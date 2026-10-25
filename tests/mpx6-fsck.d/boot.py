#!/usr/bin/env python3
"""Bounded QEMU witness through tools/qemu-run; stop via monitor, no signals."""
from pathlib import Path
import os
import socket
import subprocess
import sys
import time

repo, disk, serial, firmware, kind = sys.argv[1:6]
extra_drive = sys.argv[6] if len(sys.argv) > 6 else None
serial = Path(serial)
monitor = str(serial) + '.sock'
try:
    os.unlink(monitor)
except FileNotFoundError:
    pass
cmd = [repo + '/tools/qemu-run', '--boot-disk', '--accel', 'tcg', '--firmware', firmware,
       '--serial', str(serial), '--timeout', '210', disk, '--',
       '-m', '512M', '-monitor', 'unix:' + monitor + ',server=on,wait=off']
if extra_drive:
    at = cmd.index(disk)
    cmd[at:at] = ['--drive', extra_drive]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def quit_monitor():
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(3)
        s.connect(monitor)
        s.sendall(b'quit\n')


try:
    until = time.monotonic() + 180
    marker = {'cut': b'PX72_CRASH_READY', 'halt': b'\nhalt\n',
              'restart': b'marked clean; restarting'}[kind]
    while time.monotonic() < until:
        text = serial.read_bytes().replace(b'\r', b'') if serial.exists() else b''
        if marker in text:
            if kind == 'cut':
                # Cross the five-second flusher turn. Monitor quit is the
                # power cut; no guest shutdown/unmount is requested.
                time.sleep(6)
            if kind != 'restart':
                quit_monitor()
            break
        if p.poll() is not None:
            raise RuntimeError('QEMU ended before ' + repr(marker))
        time.sleep(0.1)
    else:
        raise RuntimeError('missing marker ' + repr(marker))
    output, _ = p.communicate(timeout=20)
    (Path(str(serial) + '.runner.log')).write_bytes(output)
    assert p.returncode == 0, (p.returncode, output)
    print('PASS boot-' + kind + '-' + firmware, flush=True)
finally:
    if p.poll() is None:
        quit_monitor()
        p.wait(timeout=20)
