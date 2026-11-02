#!/usr/bin/env python3
"""px87: the staged stick's qualification under QEMU (TCG), before the maintainer's metal session.

    qual.py REPO STICK.img KERNEL.elf COMMIT WORK LEG

The stick is booted from a COPY (its bytes are checked equal to STICK's first), read-only on the USB
topology (tools/qemu-run --usb-stick: qemu-xhci + usb-storage, no CD-ROM, no virtio disk), under OVMF.

LEG serial: COM1 present (the transcript is the serial file), keys typed into COM1: the live login as
  root, then each command followed by `echo PX87-MARK-$?`; the rows:
  Q1-banner  `PAX: the console`, then `kernel: COMMIT sha256 <sha256 of KERNEL.elf>, <size> bytes`
  Q1-boot    `boot: <n> ms ...; the console drew for <m> ms of it (...)` before `run 1:`
  Q1-quiet   no line of a program's ordinary life (`user: exec pid`, `user: ... exit_group N after`)
  Q1-user    `su pax -c reboot` -> `reboot: Operation not permitted`, status 1;
             `su pax -c 'pax-install --check'` -> `pax-install: inventory: /dev/sda: Permission denied; ...`
  Q1-check   `pax-install --check` as root: the stick refused as the live medium, no target, status 1
  Q1-power   `poweroff`: QEMU ends with status 0, the kernel's last power line `poweroff: ACPI S5 types a/b`
LEG kasumi: kasumi's shape: no COM1 (the transcript is PAX's own memory, boot/io.S's pax_serial_log, read
  by QMP memsave at KERNEL.elf's symbols), the USB keyboard (QMP send-key), the xHCI on MSI only behind
  OVMF's 64 GiB window (--usb-irq=msi --high-bar, px76's F8): the login screen saved (screen-login.ppm),
  root typed, `poweroff` typed, QEMU's status 0.
Prints PASS/FAIL lines; exit 0 when every row of the leg holds.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

repo, stick, kernel, commit, work, leg = sys.argv[1:7]
repo, stick, kernel, work = Path(repo), Path(stick), Path(kernel), Path(work)
work.mkdir(parents=True, exist_ok=True)
fail = 0


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def row(name, ok, what):
    global fail
    print(('PASS ' if ok else 'FAIL ') + name + ': ' + what, flush=True)
    if not ok:
        fail = 1


copy = work / 'stick-copy.img'
shutil.copyfile(stick, copy)
assert sha(copy) == sha(stick), 'the copy differs from the stick'
print('stick %s sha256 %s (the copy equal)' % (stick, sha(stick)), flush=True)
want_kernel = 'kernel: %s sha256 %s, %d bytes' % (commit, sha(kernel), kernel.stat().st_size)
quiet_re = re.compile(r'^user: (exec pid |[^ ]+ pid [0-9]+ (exit_group|exit) [0-9]+ after )')
boot_re = re.compile(r"^boot: ([0-9]+) ms from the kernel's entry to its first program; the console drew for ([0-9]+) ms of it \(([0-9]+) scrolls, ([0-9]+) bytes\)$")


def common_rows(prefix, lines):
    i = lines.index('PAX: the console') if 'PAX: the console' in lines else -1
    got = lines[i + 1] if 0 <= i < len(lines) - 1 else ''
    row(prefix + '-banner', got == want_kernel, repr(got) + ('' if got == want_kernel else ' not ' + repr(want_kernel)))
    b = [l for l in lines if l.startswith('boot: ')]
    r1 = [k for k, l in enumerate(lines) if l.startswith('run 1: ')]
    ok = bool(b) and bool(boot_re.match(b[0])) and r1 and lines.index(b[0]) < r1[0]
    row(prefix + '-boot', ok, b[0] if b else 'no boot line')
    bad = [l for l in lines if quiet_re.match(l)]
    row(prefix + '-quiet', not bad, 'no per-program line' if not bad else bad[0])


if leg == 'serial':
    serial = work / 'serial.log'
    fifo = work / 'serial.in'
    if fifo.exists():
        fifo.unlink()
    os.mkfifo(fifo)
    fd = os.open(fifo, os.O_RDWR)
    q = subprocess.Popen([repo / 'tools/qemu-run', '--firmware', 'uefi', '--accel', 'tcg', '--usb-stick', '--timeout', '1500',
                          '--serial', serial, '--serial-input', fifo, copy], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def text():
        try:
            return serial.read_bytes().decode('latin-1').replace('\r', '')
        except OSError:
            return ''

    def wait(pattern, after=0, timeout=600):
        t0 = time.time()
        while time.time() - t0 < timeout:
            t = text()
            m = re.search(pattern, t[after:], re.M)
            if m:
                return after + m.end()
            if q.poll() is not None:
                return -1
            time.sleep(0.5)
        return -1

    def typ(s):
        for ch in s:
            os.write(fd, ch.encode())
            time.sleep(0.02)

    at = wait(r'^login: ', 0, 900)
    row('Q1-login', at > 0, 'the live login reached')
    typ('root\r')
    at = wait(r'[#$] $', at, 300)
    marks = {}
    for k, cmd in enumerate(["su pax -c reboot", "su pax -c 'pax-install --check'", "pax-install --check"]):
        typ(cmd + '; echo PX87-MARK-%d-$?\r' % k)
        end = wait(r'^PX87-MARK-%d-[0-9]+$' % k, at, 600)
        marks[k] = (at, end)
        at = end if end > 0 else at
    typ('poweroff\r')
    try:
        rc = q.wait(timeout=600)
    except subprocess.TimeoutExpired:
        q.kill(); rc = q.wait()
    os.close(fd)
    t = text()
    lines = t.splitlines()
    (work / 'serial.norm').write_text(t)
    common_rows('Q1', lines)
    seg = lambda k: t[marks[k][0]:marks[k][1]] if marks[k][1] > 0 else ''
    s0, s1, s2 = seg(0), seg(1), seg(2)
    row('Q1-user-reboot', 'reboot: Operation not permitted' in s0 and 'PX87-MARK-0-1' in s0, ' | '.join(s0.strip().splitlines()[-2:]))
    ok1 = re.search(r'^pax-install: inventory: /dev/sd[a-z]: Permission denied; pax-install opens every disk to measure it, so run it as root$', s1, re.M) and 'PX87-MARK-1-1' in s1
    row('Q1-user-check', bool(ok1), ' | '.join(s1.strip().splitlines()[-2:]))
    ok2 = 'refused: a PAX live medium' in s2 and 'PX87-MARK-2-1' in s2
    row('Q1-check', ok2, ' | '.join(l for l in s2.strip().splitlines() if 'refused' in l or 'MARK' in l or 'Disks' in l))
    power = [l for l in lines if re.match(r'^(reboot|poweroff): ', l) and not l.endswith('Operation not permitted')]
    last = power[-1] if power else ''
    row('Q1-power', rc == 0 and bool(re.fullmatch(r'poweroff: ACPI S5 types [0-7]/[0-7]', last)), 'QEMU status %d, the last power line %r' % (rc, last))
elif leg == 'kasumi':
    sym = {}
    for line in subprocess.run(['nm', kernel], capture_output=True, text=True).stdout.splitlines():
        f = line.split()
        if len(f) == 3:
            sym[f[2]] = int(f[0], 16)
    qmp = work / 'qmp.sock'
    if qmp.exists():
        qmp.unlink()
    q = subprocess.Popen([repo / 'tools/qemu-run', '--firmware', 'uefi', '--accel', 'tcg', '--usb-stick', '--usb-kbd', '--no-serial',
                          '--usb-irq=msi', '--high-bar', '--timeout', '1500', '--serial', work / 'none.log', copy, '--',
                          '-qmp', 'unix:%s,server=on,wait=off' % qmp], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(200):
        if qmp.exists():
            break
        time.sleep(0.1)
    s = socket.socket(socket.AF_UNIX)
    s.connect(str(qmp))
    fh = s.makefile('rwb')

    def call(cmd, **args):
        fh.write(json.dumps({'execute': cmd, 'arguments': args} if args else {'execute': cmd}).encode() + b'\n')
        fh.flush()
        while True:
            m = json.loads(fh.readline())
            if 'return' in m or 'error' in m:
                return m

    json.loads(fh.readline())
    call('qmp_capabilities')

    def transcript():
        p = work / 'mem.bin'
        if 'error' in call('memsave', val=sym['pax_serial_log_count'], size=8, filename=str(p)):
            return ''
        n = min(int.from_bytes(p.read_bytes()[:8], 'little'), 65536)
        if n == 0 or 'error' in call('memsave', val=sym['pax_serial_log'], size=n, filename=str(p)):
            return ''
        return p.read_bytes()[:n].decode('latin-1').replace('\r', '')

    def wait(pattern, timeout=900):
        t0 = time.time()
        while time.time() - t0 < timeout:
            t = transcript()
            if re.search(pattern, t, re.M):
                return t
            if q.poll() is not None:
                return ''
            time.sleep(1)
        return ''

    QC = {' ': 'spc', '\r': 'ret', '-': 'minus', '.': 'dot', '/': 'slash'}

    def typ(s):
        for ch in s:
            call('send-key', keys=[{'type': 'qcode', 'data': QC.get(ch, ch)}])
            time.sleep(0.05)

    t = wait(r'^login: ', 1200)
    row('Q2-login', bool(t), 'the live login reached with no COM1, the keyboard on USB (xHCI on MSI)')
    call('screendump', filename=str(work / 'screen-login.ppm'))
    lines = t.splitlines()
    common_rows('Q2', lines)
    clk = [l for l in lines if l.startswith('clock: ')]
    print('  ' + (clk[0] if clk else 'no clock line'), flush=True)
    print('  ' + next((l for l in lines if l.startswith('screen: ')), 'no screen line'), flush=True)
    typ('root\r')
    t = wait(r'[#$] $', 300)
    row('Q2-root', bool(t), 'root reached the shell through the USB keyboard')
    call('screendump', filename=str(work / 'screen-root.ppm'))
    typ('poweroff\r')
    try:
        rc = q.wait(timeout=600)
    except subprocess.TimeoutExpired:
        q.kill(); rc = q.wait()
    row('Q2-power', rc == 0, 'QEMU status %d after poweroff typed on the USB keyboard' % rc)
    (work / 'transcript.txt').write_text(t)
else:
    sys.exit('qual.py: LEG is serial or kasumi')
print('qual %s: %s' % (leg, 'PASS' if fail == 0 else 'FAIL'), flush=True)
sys.exit(fail)
