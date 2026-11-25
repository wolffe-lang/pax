#!/usr/bin/env python3
"""tests/distribution-warren's own self-test: its two readers against made-up inputs, no QEMU and no network.

    python3 -I -B tests/distribution-warren.d/judge-selftest.py

identity.py's `archive` reads a made-up image directory (a newc archive written here, its release file, its
resolution, the ISO's copy of the archive). `tree` reads a git tree made here and a stand-in for warren.
`rows` reads the rows a console_rows.py asks by default. judge.py reads made-up leg transcripts. Each case says
whether it wanted the reader green or red, and which rows it wanted named. A case passes only when the reader's
verdict and its named rows are what the case wants. It prints one PASS or FAIL line a case, and exits 0 only when
every case passed.
"""
import hashlib
import importlib.util
import io
import os
import struct
import subprocess
import sys
import tempfile
import contextlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT = 'a' * 40
OTHER = 'b' * 40
YEW = 'c' * 40
REPO = 'https://github.com/wolffe-lang/warren'
ROWS11 = ['C%d' % i for i in range(11)]
failed = []


def load(name):
    path = HERE / (name + '.py')
    spec = importlib.util.spec_from_file_location('dw_' + name, path)
    if spec is None or not path.exists():
        raise ImportError(f'{path.name} is missing')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case(name, want_ok, want_named, run):
    """run() returns (ok, lines); want_named are row names that must have a FAIL line, and nothing else may."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ok, lines = run()
    except Exception as exc:  # a reader that cannot run fails every case it is in
        print(f'FAIL JUDGE-SELFTEST {name}: the reader did not run: {type(exc).__name__}: {exc}', flush=True)
        failed.append(name)
        return
    named = sorted({l.split()[1] for l in lines if l.startswith('FAIL ')})
    held = ok == want_ok and named == sorted(want_named)
    print('%s JUDGE-SELFTEST %s: %s, named %s (want %s, named %s)' % (
        'PASS' if held else 'FAIL', name, 'green' if ok else 'red', named or 'none', 'green' if want_ok else 'red',
        sorted(want_named) or 'none'), flush=True)
    if not held:
        failed.append(name)
        for l in lines:
            print('    ' + l, flush=True)


# --- made-up images -------------------------------------------------------------------------------------------

def elf(interp=False, dynamic=False, etype=2, machine=0x3e):
    """A 64-bit little-endian ELF header and its program headers: PT_LOAD, and PT_INTERP or PT_DYNAMIC if asked."""
    kinds = [1] + ([3] if interp else []) + ([2] if dynamic else [])
    head = (b'\x7fELF' + bytes([2, 1, 1, 0]) + bytes(8)
            + struct.pack('<HHIQQQIHHHHHH', etype, machine, 1, 0x401000, 64, 0, 0, 64, 56, len(kinds), 0, 0, 0))
    phdrs = b''.join(struct.pack('<IIQQQQQQ', k, 5, 0, 0x400000, 0x400000, 4096, 4096, 4096) for k in kinds)
    return head + phdrs + b'warren-made-up-body' * 8


def newc(entries):
    """A newc archive of (name, mode, data) entries and its trailer."""
    out = b''
    for i, (name, mode, data) in enumerate(entries + [('TRAILER!!!', 0, b'')]):
        n = name.encode() + b'\0'
        fields = [i + 1, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(n), 0]
        rec = b'070701' + b''.join(b'%08x' % f for f in fields) + n
        rec += b'\0' * (-len(rec) % 4) + data
        rec += b'\0' * (-len(rec) % 4)
        out += rec
    return out


def image(tmp, warren=None, mode=0o100755, files_digest=None, release_commit=COMMIT, out_release=None,
          resolution=COMMIT, iso_differs=False, no_warren_row=False):
    """A made-up OUT directory: dev.cpio, pax-release, latest/resolution.txt, and the ISO's copy of the archive."""
    out = Path(tmp) / 'out'
    (out / 'latest').mkdir(parents=True)
    war = elf() if warren is None else warren
    rows = ['kernel %s %s' % ('d' * 40, 'e' * 64), 'pelt %s %s' % ('f' * 40, '1' * 64), 'yew %s merged' % YEW]
    if not no_warren_row:
        rows.append('warren %s merged' % release_commit)
    release = ''.join(r + '\n' for r in sorted(rows)).encode()
    digest = files_digest or hashlib.sha256(war).hexdigest()
    files = ('%s  etc/pax-release\n%s  usr/bin/warren\n' % (hashlib.sha256(release).hexdigest(), digest)).encode()
    archive = newc([('etc', 0o40755, b''), ('etc/pax-release', 0o100644, release),
                    ('etc/pax-files.sha256', 0o100644, files), ('usr', 0o40755, b''), ('usr/bin', 0o40755, b''),
                    ('usr/bin/warren', mode, war)])
    (out / 'dev.cpio').write_bytes(archive)
    (out / 'pax-release').write_bytes(out_release if out_release is not None else release)
    if resolution is not None:
        (out / 'latest/resolution.txt').write_text(
            'pax %s unmerged https://github.com/wolffe-lang/pax checkout\n' % ('9' * 40)
            + 'warren %s merged %s trunk\n' % (resolution, REPO)
            + 'yew %s merged https://github.com/wolffe-lang/yew trunk\n' % YEW)
    iso = Path(tmp) / 'iso-initramfs.cpio'
    iso.write_bytes(archive + (b'\0' * 512 if iso_differs else b''))
    work = Path(tmp) / 'work'
    work.mkdir()
    return out, iso, work


def archive_case(name, want_ok, want_named=(), check=None, **kw):
    def run():
        identity = load('identity')
        with tempfile.TemporaryDirectory() as tmp:
            out, iso, work = image(tmp, **kw)
            ok, lines = identity.archive(out, iso, work)
            if ok and check is not None:
                why = check(work)
                if why:
                    return False, lines + ['FAIL W0-written: ' + why]
            return ok, lines
    case(name, want_ok, list(want_named), run)


def written(work):
    war = work / 'warren'
    if not war.exists() or war.read_bytes() != elf():
        return 'the image\'s warren was not written as its bytes'
    if os.stat(war).st_mode & 0o777 != 0o755:
        return 'the written warren is not 0755'
    if (work / 'warren-commit').read_text().strip() != COMMIT:
        return 'warren-commit is not the release row\'s commit'
    if (work / 'warren-repo').read_text().strip() != REPO:
        return 'warren-repo is not the resolution\'s repository'
    return None


# --- made-up trees --------------------------------------------------------------------------------------------

def git(tree, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@t', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    return subprocess.run(['git', '-C', str(tree), '-c', 'commit.gpgsign=false', *args], check=True,
                          capture_output=True, text=True, env=env).stdout.strip()


ROWS_SOURCE = "ap.add_argument('rows', nargs='?', default='%s')\n"


def tree(tmp, version='0.3.1', rows=True, says=None, status=0):
    t = Path(tmp) / 'tree'
    (t / 'src').mkdir(parents=True)
    (t / 'src/wolf.pkg').write_text('// the package\npackage { name: "warren", version: "%s", }\n' % version)
    if rows:
        (t / 'tests/pax').mkdir(parents=True)
        (t / 'tests/pax/console_rows.py').write_text(ROWS_SOURCE % ','.join(ROWS11))
    git(t, 'init', '-q')
    git(t, 'add', '-A')
    git(t, 'commit', '-q', '-m', 'made up')
    war = Path(tmp) / 'warren'
    line = says if says is not None else 'warren 0.3.1: modules'
    war.write_text('#!/bin/sh\n[ "$1" = modules ] || exit 9\necho "%s"\nexit %d\n' % (line, status))
    war.chmod(0o755)
    return t, git(t, 'rev-parse', 'HEAD'), war


def tree_case(name, want_ok, want_named=(), commit=None, **kw):
    def run():
        identity = load('identity')
        with tempfile.TemporaryDirectory() as tmp:
            t, head, war = tree(tmp, **kw)
            return identity.tree(t, commit or head, war)
    case(name, want_ok, list(want_named), run)


def rows_case(name, source, want):
    def run():
        identity = load('identity')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'console_rows.py'
            p.write_text(source)
            try:
                got = identity.default_rows(p)
            except ValueError as exc:
                got = None
                why = str(exc)
            if want is None:
                return got is None, ([] if got is None else ['FAIL ROWS read %s from a file with none' % got])
            if got == want:
                return True, ['PASS ROWS ' + ','.join(got)]
            return False, ['FAIL ROWS read %s' % (got if got is not None else why)]
    case(name, True, [], run)


# --- made-up legs ---------------------------------------------------------------------------------------------

def leg(rows=ROWS11, fail=(), absent=(), twice=(), other=(), summary=True, claim=None, fw='bios', kbd='usb'):
    lines = ['qemu-run: tools/qemu-run --firmware %s ...' % fw, "the console's prompt: True after 9 s"]
    for r in rows:
        if r in absent:
            continue
        f, k = ('uefi', 'ps2') if r in other else (fw, kbd)
        n = 2 if r in twice else 1
        lines += ['%s %s %s %s: made up' % ('FAIL' if r in fail else 'PASS', r, f, k)] * n
        if r in fail:
            lines.append('NOTE the screen: made up')
    bad = [r for r in rows if r in fail or r in absent or r in other]
    if summary:
        verdict = claim if claim is not None else ('FAIL ' + ','.join(bad) if bad else 'PASS')
        printed = [r for r in rows if r not in absent]
        lines.append('CONSOLE-ROWS %s %s: %s (%d rows: %s)' % (fw, kbd, verdict, len(printed), ','.join(printed)))
    return '\n'.join(lines) + '\n'


def judge_case(name, want_ok, want_named, text, rc, asked=ROWS11, index=1, fw='bios', kbd='usb'):
    def run():
        judge = load('judge')
        return judge.judge(index, fw, kbd, list(asked), rc, text)
    case(name, want_ok, list(want_named), run)


def main():
    # identity.py archive: W0 against a made-up image directory
    archive_case('A1-good', True, check=written)
    archive_case('A2-resolution-names-another-warren', False, ['W0'], resolution=OTHER)
    archive_case('A3-release-file-differs', False, ['W0'], out_release=b'warren %s merged\n' % COMMIT.encode())
    archive_case('A4-bytes-not-the-archive-digest', False, ['W0'], files_digest='0' * 64)
    archive_case('A5-iso-boots-other-bytes', False, ['W0'], iso_differs=True)
    archive_case('A6-dynamic-warren', False, ['W0'], warren=elf(interp=True))
    archive_case('A7-dynamic-section', False, ['W0'], warren=elf(dynamic=True))
    archive_case('A8-not-exec', False, ['W0'], warren=elf(etype=3))
    archive_case('A9-not-x86-64', False, ['W0'], warren=elf(machine=0xb7))
    archive_case('A10-mode-0644', False, ['W0'], mode=0o100644)
    archive_case('A11-no-warren-row', False, ['W0'], no_warren_row=True)
    archive_case('A12-pinned-build-no-resolution', True, resolution=None)
    # identity.py tree: the tree at the commit and the image's warren on the host
    tree_case('T1-good', True)
    tree_case('T2-version-differs', False, ['W0'], says='warren 0.3.2: modules')
    tree_case('T3-head-not-the-commit', False, ['W0'], commit=OTHER)
    tree_case('T4-no-console-rows', False, ['W0'], rows=False)
    tree_case('T5-warren-exits-nonzero', False, ['W0'], status=3)
    # identity.py rows: the rows a console_rows.py asks by default
    rows_case('R1-default-rows', ROWS_SOURCE % ','.join(ROWS11), ROWS11)
    rows_case('R2-eight-rows', ROWS_SOURCE % 'C0,C1,C2,C3,C4,C5,C6,C7', ROWS11[:8])
    rows_case('R3-no-default', "ap.add_argument('rows', nargs='?')\n", None)
    rows_case('R4-not-a-row-name', ROWS_SOURCE % 'C0,rm -rf', None)
    # judge.py: a leg's transcript and exit
    judge_case('J1-every-row-passed', True, [], leg(), 0)
    judge_case('J2-a-row-missing', False, ['W1-C3'], leg(absent=['C3']), 1)
    judge_case('J3-a-row-failed', False, ['W1-C2'], leg(fail=['C2']), 1)
    judge_case('J4-exit-0-with-a-row-absent', False, ['W1', 'W1-C5'], leg(absent=['C5'], claim='PASS'), 0)
    judge_case('J5-exit-1-every-row-passed', False, ['W1'], leg(), 1)
    judge_case('J6-the-leg-did-not-finish', False, ['W1', 'W1-C9', 'W1-C10'],
               leg(absent=['C9', 'C10'], summary=False), 137)
    judge_case('J7-a-row-twice', False, ['W1-C4'], leg(twice=['C4']), 0)
    judge_case('J8-another-legs-row', False, ['W1', 'W1-C1'], leg(other=['C1'], claim='PASS'), 0)
    judge_case('J9-second-leg-uefi-ps2', True, [], leg(fw='uefi', kbd='ps2'), 0, index=2, fw='uefi', kbd='ps2')
    judge_case('J10-asked-fewer', True, [], leg(rows=ROWS11[:8]), 0, asked=ROWS11[:8])
    judge_case('J11-summary-says-pass-row-failed', False, ['W1', 'W1-C6'], leg(fail=['C6'], claim='PASS'), 1)
    if failed:
        print('FAIL judge-selftest: %d case(s): %s' % (len(failed), ' '.join(failed)), flush=True)
        return 1
    print('PASS judge-selftest: every case', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
