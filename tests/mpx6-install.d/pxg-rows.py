#!/usr/bin/env python3
"""Judge pxg's selected readers and named refusals on installer-created ext2."""
from pathlib import Path
import re
import sys

EXPECTED = {
    'VERSION': (0, 'paxage 0.1.0 (pxg; format v1, file trust, pack and stage, linux transactions)'),
    'COMPARE': (0, '-1'),
    'INSTALL': (1, 'paxage: live-root-is-pm05'),
    'REMOVE': (1, 'paxage: live-root-is-pm05'),
    'UPGRADE': (1, 'paxage: live-root-is-pm05'),
    'INIT': (1, 'paxage: unqualified-filesystem ext2-family (journal not qualified on PAX)'),
}


def judge(text, release):
    text = re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]', '', text).replace('\r', '')
    # Kernel syscall observations are not the program's stdout/stderr.
    text = re.sub(r'^user: [^\n]*\n', '', text, flags=re.M)
    for name, (status, body) in EXPECTED.items():
        pattern = rf'^PXG-{name}-BEGIN\n(.*?)\nPXG-{name}-END=([0-9]+)$'
        got = re.findall(pattern, text, re.M | re.S)
        assert got == [(body, str(status))], f'I-pxg-{name.lower()}: {got!r}'
    assert re.findall(r'^PXG-NO-STATE=([0-9]+)$', text, re.M) == ['0'], 'I-pxg-state-created'
    pins = [line for line in release.splitlines() if line.startswith('pxg ')]
    assert len(pins) == 1 and pins[0] in text.splitlines(), 'I-pxg-release-pin'


def selftest():
    release = 'pxg ' + 'a' * 40 + ' ' + 'b' * 64
    text = ''.join(f'PXG-{n}-BEGIN\n{b}\nPXG-{n}-END={s}\n' for n, (s, b) in EXPECTED.items())
    text += 'PXG-NO-STATE=0\n' + release + '\n'
    judge(text, release)
    cases = [('refusal-name', text.replace('ext2-family', 'overlay')),
             ('status', text.replace('PXG-INIT-END=1', 'PXG-INIT-END=0')),
             ('state', text.replace('PXG-NO-STATE=0', 'PXG-NO-STATE=1')),
             ('pin', text.replace(release, 'pxg wrong pin')),
             ('missing', text.replace('PXG-UPGRADE-BEGIN', 'LOST'))]
    for label, changed in cases:
        try:
            judge(changed, release)
        except AssertionError:
            continue
        raise AssertionError('I-pxg-judge-accepted-' + label)
    print('PASS I-pxg-judge: changed refusal, status, state, pin and missing receipt rejected')


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    elif len(sys.argv) == 3:
        judge(Path(sys.argv[1]).read_text(errors='replace'), Path(sys.argv[2]).read_text())
        print('PASS I-pxg: installed source pin, readers, named ext2/live-root refusals, no state writes')
    else:
        sys.exit('usage: pxg-rows.py SERIAL_LOG PAX_RELEASE | --selftest')
