#!/usr/bin/env python3
"""scan-rows.py — tools/secret-scan's own rows, on a throwaway key (px104,
R-px104-15).

    scan-rows.py WORKDIR

A throwaway OpenSSH ed25519 key, made by ssh-keygen (a black box) in a
0700 directory under WORKDIR and removed at the end: never a secret. Given
it as --key-file, the scanner must say:
  T1 for a file holding only the key's first base64 line (the line every
     unencrypted OpenSSH ed25519 key shares: the format's header), no hit
     (`key=0`), and `SCAN-GENERIC key=1`: one line excluded, since a key it
     made itself just then holds the same line;
  T2 for a file holding the key's second base64 line (its own bytes: the
     public key begins there), a hit (`key=1`);
  T3 that key it made itself is a key: `fresh_key('ssh-ed25519')`, written
     once into the same 0700 directory for this row alone, is read by
     ssh-keygen -y as the public key the scanner derived, and a signature
     ssh-keygen makes with it (-Y sign) checks against that public key
     (-Y check-novalidate), so the public half is the seed's.
PASS or FAIL per row. Exit 0, 1 when a row failed, 3 without ssh-keygen.
"""
import base64
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / 'tools/secret-scan'
FAILS = []


def ok(row, why):
    print('PASS %s %s' % (row, why), flush=True)


def bad(row, why):
    FAILS.append(row)
    print('FAIL %s %s' % (row, why), flush=True)


def scan(key, path):
    r = subprocess.run([sys.executable, '-I', str(SCAN), '--key-file', str(key), str(path)],
                       capture_output=True, timeout=120)
    out = r.stdout.decode(errors='replace').splitlines()
    head = next((l for l in out if l.startswith('SCAN files=')), '')
    generic = next((l for l in out if l.startswith('SCAN-GENERIC ')), '')
    return r.returncode, head, generic


def main():
    keygen = shutil.which('ssh-keygen')
    if not keygen:
        print('SKIP T1-T3: no ssh-keygen', flush=True)
        return 3
    work = Path(sys.argv[1])
    work.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='scan-rows.', dir=work))
    try:
        os.chmod(d, 0o700)
        (d / 'k').mkdir(mode=0o700)
        (d / 'f').mkdir(mode=0o700)
        key = d / 'k/id_ed25519'
        subprocess.run([keygen, '-q', '-t', 'ed25519', '-N', '', '-C', 'px104-scan-rows', '-f', str(key)], check=True)
        lines = [l for l in key.read_bytes().splitlines() if l and not l.startswith(b'-----')]
        one = d / 'f/header-line'
        one.write_bytes(b'transcript before\n' + lines[0] + b'\ntranscript after\n')
        rc, head, generic = scan(key, one)
        if rc == 0 and head.endswith(' key=0 paths=0') and generic.startswith('SCAN-GENERIC key=1 '):
            ok('T1', 'a file holding only the key\'s first line, its format header: %s; %s' % (head, generic))
        else:
            bad('T1', 'a file holding only the key\'s first line: exit %d, %r, %r' % (rc, head, generic))
        one.unlink()
        two = d / 'f/second-line'
        two.write_bytes(b'transcript before\n' + lines[1] + b'\ntranscript after\n')
        rc, head, generic = scan(key, two)
        if rc == 1 and ' key=1 ' in head:
            ok('T2', 'a file holding the key\'s second line: %s' % head)
        else:
            bad('T2', 'a file holding the key\'s second line: exit %d, %r' % (rc, head))
        two.unlink()
        spec = importlib.util.spec_from_loader('secret_scan', loader=None)
        scanner = importlib.util.module_from_spec(spec)
        exec(compile(SCAN.read_text(), str(SCAN), 'exec'), scanner.__dict__)
        fresh = getattr(scanner, 'fresh_key', None)
        if fresh is None:
            bad('T3', 'the scanner makes no key of its own (no fresh_key)')
        else:
            pem, public = fresh('ssh-ed25519')
            mine = d / 'k/fresh'
            mine.write_bytes(pem)
            os.chmod(mine, 0o600)
            r = subprocess.run([keygen, '-y', '-f', str(mine)], capture_output=True, timeout=60)
            blob = b''.join(len(x).to_bytes(4, 'big') + x for x in (b'ssh-ed25519', public))
            want = b'ssh-ed25519 ' + base64.b64encode(blob)
            got = b' '.join(r.stdout.strip().split(b' ')[:2])
            msg = d / 'f/message'
            msg.write_bytes(b'px104 scan-rows\n')
            sig = subprocess.run([keygen, '-Y', 'sign', '-f', str(mine), '-n', 'px104', str(msg)], capture_output=True, timeout=60)
            chk = subprocess.run([keygen, '-Y', 'check-novalidate', '-n', 'px104', '-s', str(msg) + '.sig'],
                                 stdin=open(msg, 'rb'), capture_output=True, timeout=60) if sig.returncode == 0 else sig
            mine.unlink()
            if r.returncode == 0 and got == want and chk.returncode == 0:
                ok('T3', 'the scanner\'s own fresh ed25519 key: ssh-keygen -y reads back the public key it derived, '
                   'and a signature made with it checks against that key')
            else:
                bad('T3', 'the scanner\'s fresh key: -y exit %d (the derived key %s), sign/check exit %d %r'
                    % (r.returncode, 'read back' if got == want else 'not read back', chk.returncode, chk.stderr[:120]))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('SCAN-ROWS: %d of 3 failed%s' % (len(FAILS), (': ' + ' '.join(FAILS)) if FAILS else ''), flush=True)
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
