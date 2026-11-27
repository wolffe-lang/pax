#!/usr/bin/env python3
"""Public-only pxg commands/oracle for installer ext3 and explicit ext2 preview.
The signed anchor here is TEST-ONLY fixture data, never a production default.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shlex
import sys

HERE = Path(__file__).resolve().parent
TEST_ONLY_ROOT = HERE/'TEST-ONLY-pxg-root.json'
TEST_ONLY_ROOT_SHA256 = '57da38ddbc7279a4a639920256399c03152443161173a8d18462b6c087513288'
TEST_ONLY_NOW = '2026-11-26T00:00:00Z'
GUEST_TEST_ONLY_ANCHOR = '/tmp/TEST-ONLY-pxg-root.json'
EXPECTED = {
    'VERSION': (0, 'paxage 0.2.1 (pxg; format v1, file trust, pack and stage, linux transactions)'),
    'COMPARE': (0, '-1'),
    'ANCHOR': (0, None),
    'INSTALL': (1, 'paxage: live-root-unsupported'),
    'REMOVE': (1, 'paxage: live-root-unsupported'),
    'UPGRADE': (1, 'paxage: live-root-unsupported'),
    'LIVE-INIT': (1, 'paxage: live-root-unsupported'),
}
EXT2_REFUSAL = 'paxage: unqualified-filesystem ext2-family (journal not qualified on PAX)'
EMPTY_STATUS = dict(generation=0, pending='', ownership='privileged', packages=[], residuals=[],
                    proposals=[], accounts=[], pending_actions=[])


def identity(profile, instance):
    assert profile in ('ext2', 'ext3'), 'I-pxg-profile-required'
    assert instance in ('bios', 'uefi'), 'I-pxg-instance-required'
    return '/home/pax/TEST-ONLY-pxg-root-'+instance


def fixture_bytes():
    assert not TEST_ONLY_ROOT.is_symlink(), 'I-pxg-test-only-anchor-link'
    data = TEST_ONLY_ROOT.read_bytes()
    assert hashlib.sha256(data).hexdigest() == TEST_ONLY_ROOT_SHA256, 'I-pxg-test-only-anchor-digest'
    provenance = json.loads((HERE/'TEST-ONLY-pxg-root.provenance.json').read_text())
    assert provenance.get('test_only') is True and provenance.get('producer_run') == 45914664981, 'I-pxg-test-only-anchor-provenance'
    assert provenance.get('public_root_sha256') == TEST_ONLY_ROOT_SHA256, 'I-pxg-test-only-anchor-provenance'
    assert provenance.get('verification_now') == TEST_ONLY_NOW, 'I-pxg-test-only-anchor-clock'
    assert provenance.get('bundle_sha256') == 'f185488197c4ac0924b921dabbf39b60c3542f34a034ac0e26b947ccc132ee2e', 'I-pxg-test-only-anchor-provenance'
    assert b'\n' not in data and data.isascii(), 'I-pxg-test-only-anchor-encoding'
    return data


def commands(profile, instance):
    root = identity(profile, instance)
    # Bounded quoted chunks preserve the approved public signed bytes exactly.
    # Minimal test roots precreate root; the delivered full image already has mkdir.
    data = fixture_bytes().decode('ascii')
    result = []
    for offset in range(0, len(data), 256):
        redirect = '>' if offset == 0 else '>>'
        result.append("printf '%s' "+shlex.quote(data[offset:offset+256])+' '+redirect+' '+GUEST_TEST_ONLY_ANCHOR)
    result += ['test -d '+root+' || mkdir '+root,
               'test -d '+root+'; echo PXG-ROOT-DIR=$?',
               'test ! -e '+root+'/var; echo PXG-CANDIDATE-EMPTY=$?',
               'echo PXG-PROFILE='+profile, 'echo PXG-INSTANCE='+instance]
    for line in (HERE/'pxg.keys').read_text().splitlines():
        if line.startswith('@EXT3@'):
            if profile != 'ext3':
                continue
            line = line.removeprefix('@EXT3@')
        for token, value in (('@ROOT@', root), ('@ANCHOR@', GUEST_TEST_ONLY_ANCHOR), ('@NOW@', TEST_ONLY_NOW)):
            line = line.replace(token, value)
        assert '@' not in line, 'I-pxg-command-placeholder'
        result.append(line)
    assert all('\n' not in line and len(line) <= 768 for line in result), 'I-pxg-command-bound'
    return result


def expected(profile):
    rows = dict(EXPECTED)
    rows['INIT'] = (0, 'init ok') if profile == 'ext3' else (1, EXT2_REFUSAL)
    if profile == 'ext3':
        rows['VERIFY'] = (0, 'verify ok')
        rows['STATUS'] = (0, None)
    return rows


def judge(text, release, profile, instance):
    identity(profile, instance)
    text = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', text).replace('\r', '')
    # Kernel syscall observations are not the program's stdout/stderr.
    text = re.sub(r'^user: [^\n]*\n', '', text, flags=re.M)
    rows = expected(profile)
    for name, (status, body) in rows.items():
        pattern = rf'^PXG-{name}-BEGIN\n(.*?)\nPXG-{name}-END=([0-9]+)$'
        got = re.findall(pattern, text, re.M | re.S)
        label = 'I-pxg-init-'+profile if name == 'INIT' else 'I-pxg-'+name.lower()
        assert len(got) == 1 and got[0][1] == str(status), f'{label}: {got!r}'
        if name == 'ANCHOR':
            anchor = got[0][0]
            for line in ('role root', 'version 1', 'sha256 '+TEST_ONLY_ROOT_SHA256,
                         'length 2519', 'threshold 2 valid 3 met', 'repo inspect ok'):
                assert anchor.splitlines().count(line) == 1, 'I-pxg-test-only-anchor-observed'
        elif name == 'STATUS':
            assert json.loads(got[0][0]) == EMPTY_STATUS, 'I-pxg-empty-status'
        else:
            assert got[0][0] == body, f'{label}: {got!r}'
    assert Counter(re.findall(r'^PXG-([A-Z-]+)-BEGIN$', text, re.M)) == Counter(rows.keys()), 'I-pxg-receipt-set'
    for name, value in (('PROFILE', profile), ('INSTANCE', instance), ('ROOT-DIR', '0'), ('CANDIDATE-EMPTY', '0'),
                        ('STATE-PRESENT', '0' if profile == 'ext3' else '1'), ('LIVE-NO-STATE', '0')):
        assert re.findall(r'^PXG-'+name+r'=([^\n]+)$', text, re.M) == [value], 'I-pxg-'+name.lower()
    pins = [line for line in release.splitlines() if line.startswith('pxg ')]
    assert len(pins) == 1 and pins[0] in text.splitlines(), 'I-pxg-release-pin'


def control_body(name, body):
    if name == 'STATUS':
        return json.dumps(EMPTY_STATUS, separators=(',', ':'))
    if name == 'ANCHOR':
        return 'role root\nversion 1\nsha256 '+TEST_ONLY_ROOT_SHA256+'\nlength 2519\nthreshold 2 valid 3 met\nrepo inspect ok'
    return body


def selftest():
    release = 'pxg '+'a'*40+' '+'b'*64
    for profile in ('ext2', 'ext3'):
        for instance in ('bios', 'uefi'):
            rendered = commands(profile, instance)
            recovered = ''
            for line in rendered:
                if line.startswith("printf '%s' "):
                    fields = shlex.split(line)
                    assert fields[:2] == ['printf', '%s'] and fields[3] in ('>', '>>')
                    assert fields[4] == GUEST_TEST_ONLY_ANCHOR
                    recovered += fields[2]
            assert recovered.encode('ascii') == fixture_bytes(), 'I-pxg-test-only-anchor-rendered-bytes'
            init = next(line for line in rendered if line.startswith('echo PXG-INIT-BEGIN;'))
            args = shlex.split(init.split(';')[1])
            assert args[args.index('--root')+1] == identity(profile, instance)
            assert args[args.index('--repo')+1] == 'file:///home/pax'
            assert args[args.index('--pinned-root')+1] == GUEST_TEST_ONLY_ANCHOR
            assert args[args.index('--now')+1] == TEST_ONLY_NOW
            text = ''.join(f'PXG-{n}-BEGIN\n{control_body(n,b)}\nPXG-{n}-END={s}\n'
                           for n,(s,b) in expected(profile).items())
            text += f'PXG-PROFILE={profile}\nPXG-INSTANCE={instance}\nPXG-ROOT-DIR=0\nPXG-CANDIDATE-EMPTY=0\nPXG-STATE-PRESENT={0 if profile=="ext3" else 1}\nPXG-LIVE-NO-STATE=0\n'+release+'\n'
            judge(text, release, profile, instance)
            status = 0 if profile == 'ext3' else 1
            cases = [('version',text.replace('paxage 0.2.1','paxage 0.1.0')),
                     ('anchor-digest',text.replace('sha256 '+TEST_ONLY_ROOT_SHA256,'sha256 '+'0'*64)),
                     ('anchor-threshold',text.replace('threshold 2 valid 3 met','threshold 2 valid 0 not-met')),
                     ('refusal',text.replace('live-root-unsupported','wrong-refusal')),
                     ('init-status',text.replace('PXG-INIT-END='+str(status),'PXG-INIT-END='+str(1-status))),
                     ('state',text.replace('PXG-STATE-PRESENT='+str(status),'PXG-STATE-PRESENT='+str(1-status))),
                     ('live-state',text.replace('PXG-LIVE-NO-STATE=0','PXG-LIVE-NO-STATE=1')),
                     ('missing',text.replace('PXG-UPGRADE-BEGIN','LOST')),
                     ('duplicate',text+'PXG-VERSION-BEGIN\nx\nPXG-VERSION-END=0\n'),
                     ('pin',text.replace(release,'pxg wrong pin'))]
            if profile == 'ext3': cases.append(('empty-status',text.replace('"generation":0','"generation":1')))
            for label, changed in cases:
                try:
                    judge(changed, release, profile, instance)
                except (AssertionError, ValueError):
                    continue
                raise AssertionError('I-pxg-judge-accepted-'+label)
            try:
                judge(text, release, 'ext3' if profile=='ext2' else 'ext2', instance)
            except AssertionError:
                pass
            else:
                raise AssertionError('I-pxg-judge-accepted-opposite-profile')
    for profile,instance in (('', 'bios'), ('ext4','bios'), ('ext3','other')):
        try:
            commands(profile,instance)
        except AssertionError:
            pass
        else:
            raise AssertionError('I-pxg-unknown-profile-instance')
    print('PASS I-pxg-judge: both profiles/firmwares, state/exits/receipts/pin and exact test-only anchor bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('serial', nargs='?', type=Path)
    parser.add_argument('release', nargs='?', type=Path)
    parser.add_argument('--selftest', action='store_true')
    parser.add_argument('--commands', choices=('ext2','ext3'))
    parser.add_argument('--profile', choices=('ext2','ext3'))
    parser.add_argument('--instance', choices=('bios','uefi'))
    args = parser.parse_args()
    try:
        if args.selftest:
            selftest()
        elif args.commands and args.instance and not args.serial and not args.release:
            print('\n'.join(commands(args.commands,args.instance)))
        elif args.serial and args.release and args.profile and args.instance:
            judge(args.serial.read_text(errors='replace'),args.release.read_text(),args.profile,args.instance)
            print('PASS I-pxg-'+args.profile+'-'+args.instance+': shipped source identity, synthetic state contract and named live-root refusals')
        else:
            parser.error('need --selftest, --commands PROFILE --instance FIRMWARE, or SERIAL RELEASE --profile PROFILE --instance FIRMWARE')
    except (AssertionError, ValueError, OSError) as error:
        print('FAIL '+str(error),file=sys.stderr,flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
