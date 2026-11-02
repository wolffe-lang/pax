#!/usr/bin/env python3
"""px87: what a user is told, and the power-off by name (pax#243, #265, #266).

    asuser.py REPO WORK PROGRAMS FULL SU KERNEL

One QEMU boot (native BIOS, a UART, one 64 MiB virtio disk) of a small
initramfs whose run list is, in order:
  1. `/bin/su pax /check-user.sh`: root dropping to the account pax, uid
     1000 (su(1), px46), whose shell runs the script:
       - `pax-install --check` (PROGRAMS' pax-install): the user may not
         open the disk's node (root's alone, `brw-------`), so I-user-check
         wants `pax-install: inventory: /dev/vda: Permission denied; …, so
         run it as root` and the status 1 (pax#266: it printed only
         `pax-install: inventory: io`);
       - `reboot`, then `poweroff` (FULL's probe/reboot under both names):
         I-user-reboot wants each refusal as Linux's tools say it, measured
         black-box as uid 1000 (notes/px87/linux/reboot-as-user.log:
         `reboot: Operation not permitted`, `poweroff: Operation not
         permitted`), each status 1, and the machine still up after both
         (pax#265: reboot said nothing);
  2. `/bin/poweroff`, as root: I-poweroff wants QEMU to end with status 0
     and the kernel's last line `poweroff: ACPI S5 types a/b` (kernel/power,
     px76): power-off by the program's name, no argument and no debugger
     (pax#243: the image had no poweroff, and `reboot` with no argument
     restarts).
The disk's bytes are unchanged. SU is a directory holding tools/mksu's su.
"""
import hashlib
from pathlib import Path
import re
import subprocess
import sys

repo, work, programs, full, su, kernel = map(Path, sys.argv[1:])
work.mkdir(parents=True, exist_ok=True)


def run(*args, ok=True):
    p = subprocess.run([str(x) for x in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if ok:
        assert p.returncode == 0, (args, p.returncode, p.stdout[-4000:])
    return p


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


disk = work / 'a.img'
with disk.open('wb') as f:
    f.truncate(64 * 1024 * 1024)
before = digest(disk)
(work / 'check-user.sh').write_text(
    'echo PX87-USER-START\n'
    '/bin/pax-install --check\n'
    'echo PX87-CHECK-EXIT=$?\n'
    '/bin/reboot\n'
    'echo PX87-REBOOT-EXIT=$?\n'
    '/bin/poweroff\n'
    'echo PX87-POWEROFF-EXIT=$?\n'
    'echo PX87-USER-END\n')
(work / 'run').write_text('/bin/su pax /check-user.sh\n/bin/poweroff\n')
(work / 'passwd').write_text('root:x:0:0:root:/root:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\n')
(work / 'group').write_text('root:x:0:\npax:x:1000:\n')
reboot = full / 'probe/reboot'
run(repo / 'tools/mkinitramfs', work / 'init.cpio',
    '/bin/pax-install=' + str(programs / 'pax-install') + ':755',
    '/bin/su=' + str(su / 'su') + ':755',
    '/bin/pelt=' + str(full / 'pelt/pelt') + ':755',
    '/bin/reboot=' + str(reboot) + ':755',
    '/bin/poweroff=' + str(reboot) + ':755',
    '/etc/passwd=' + str(work / 'passwd') + ':644',
    '/etc/group=' + str(work / 'group') + ':644',
    '/etc/pax-run=' + str(work / 'run') + ':644',
    '/check-user.sh=' + str(work / 'check-user.sh') + ':644',
    '/root/:700', '/home/pax/:755:1000:1000', '/tmp/:1777')
run(repo / 'tools/mkimage', '--conf', repo / 'boot/limine-initramfs.conf', '--add', work / 'init.cpio',
    'initramfs.cpio', kernel, work / 'boot.iso')
serial = work / 'serial.log'
p = run(repo / 'tools/qemu-run', '--firmware', 'bios', '--timeout', '240', '--serial', serial,
        '--drive', str(disk) + ';serial=PX87-USER', work / 'boot.iso', ok=False)
(work / 'boot.log').write_bytes(p.stdout)
text = serial.read_bytes().decode('latin-1').replace('\r', '')
lines = text.splitlines()


def need(row, line):
    assert line in lines, '%s: no line %r in %s' % (row, line, serial)


def idx(line):
    return lines.index(line) if line in lines else -1


row = 'I-user-check'
need(row, 'PX87-USER-START')
need(row, 'pax-install: inventory: /dev/vda: Permission denied; pax-install opens every disk to measure it, so run it as root')
assert 'pax-install: inventory: io' not in lines, '%s: the bare io refusal' % row
need(row, 'PX87-CHECK-EXIT=1')
print('PASS I-user-check: pax-install --check as uid 1000 names /dev/vda, the errno and that root is needed; status 1', flush=True)
row = 'I-user-reboot'
need(row, 'reboot: Operation not permitted')
need(row, 'PX87-REBOOT-EXIT=1')
need(row, 'poweroff: Operation not permitted')
need(row, 'PX87-POWEROFF-EXIT=1')
need(row, 'PX87-USER-END')
assert idx('reboot: Operation not permitted') < idx('PX87-REBOOT-EXIT=1') < idx('poweroff: Operation not permitted') < idx('PX87-USER-END'), row + ': out of order'
print("PASS I-user-reboot: reboot and poweroff as uid 1000 say Linux's 'Operation not permitted', status 1; the machine still up", flush=True)
row = 'I-poweroff'
kernel_lines = [l for l in lines if re.match(r'^(reboot|poweroff): ', l) and not l.endswith(': Operation not permitted')]
last = kernel_lines[-1] if kernel_lines else ''
assert p.returncode == 0, '%s: QEMU exit %d (last power line %r)' % (row, p.returncode, last)
assert re.fullmatch(r'poweroff: ACPI S5 types [0-7]/[0-7]', last), '%s: the last power line is %r, not poweroff: ACPI S5' % (row, last)
assert 'did not power down' not in text and 'PANIC' not in text, row + ': a panic or S5 failure'
print(f'PASS I-poweroff: /bin/poweroff as root ended the machine by ACPI S5 ({last}), QEMU status 0', flush=True)
assert digest(disk) == before, 'the disk changed'
print('PASS I-user-disk: the disk byte-identical', flush=True)
