#!/usr/bin/env python3
"""Read-only QEMU inventory and dry-run; every target byte held unchanged."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

repo, work, programs, kernel = map(Path, sys.argv[1:])
work.mkdir(parents=True, exist_ok=True)

def run(*args):
    return subprocess.run([str(x) for x in args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()

for n in ['a', 'b']:
    p = work / (n + '.img')
    with p.open('wb') as f: f.truncate(128 * 1024 * 1024)
before = [digest(work / (n + '.img')) for n in ['a', 'b']]
(work / 'run').write_text('/bin/pax-install --inventory\n'
    '/bin/pax-install --dry-run --target vda --seed test --user pax --games no\n'
    '/bin/pax-install --dry-run --target vdb --seed test --user pax --games yes\n'
    '/bin/pax-install --dry-run --target vdc --seed test --user pax --games no\n')
run(repo/'tools/mkinitramfs', work/'init.cpio', '/bin/pax-install='+str(programs/'pax-install')+':755',
    '/etc/pax-run='+str(work/'run')+':644')
run(repo/'tools/mkimage', '--conf', repo/'boot/limine-initramfs.conf', '--add', work/'init.cpio',
    'initramfs.cpio', kernel, work/'boot.iso')
(work/'boot.log').write_bytes(run(repo/'tools/qemu-halt', '--firmware', 'bios', '--elf', kernel,
    '--serial', work/'serial.log', '--marker', 'halt', '--drive', work/'a.img',
    '--drive', str(work/'b.img')+',ro', work/'boot.iso'))
s=(work/'serial.log').read_text(errors='replace')
assert '/dev/vda bytes=134217728 sector=512 readonly=false mounted=false root=false' in s, s
assert '/dev/vdb bytes=134217728 sector=512 readonly=true mounted=false root=false' in s, s
assert 'capacity_bytes 134217728' in s and 'games no' in s, s
assert 'pax-install: refused: readonly' in s, s
assert 'pax-install: target unavailable: io' in s, s
assert [digest(work/(n+'.img')) for n in ['a','b']] == before
print('PASS I-inventory: QEMU nodes, ioctl sizes, readonly and vanished target; dry-run bytes unchanged')
