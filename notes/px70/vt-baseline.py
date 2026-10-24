#!/usr/bin/env python3
"""Rerun px59's unmodified probes twice on the Linux VT; never edit goldens."""
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

base = Path(sys.argv[1]).resolve()
pax = base / 'pax'
kernel = f'/usr/lib/modules/{os.uname().release}/vmlinuz'
for suffix, prefixes in [('', ('SCREEN ', 'QUERY ', 'KEY ', 'PALETTE ')),
                         ('2', ('STATE ', 'SCREEN ', 'QUERY ', 'ECHO ', 'KEY '))]:
    source = (pax / f'notes/px59/vtprobe{suffix}.c').read_text()
    keyblock = re.search(r'static const char \*keys\[\] = \{(.*?)\};', source, re.S)
    if keyblock:
        keys = re.findall(r'"([^"]+)"', keyblock.group(1))
    else:
        keys = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10',
                'f11', 'f12', 'up', 'shift-up', 'ctrl-up', 'alt-up',
                'shift-ctrl-up', 'alt-a', 'alt_r-a', 'dot']
    measured = []
    for run in (1, 2):
        stem = base / f'out/baseline-vt{suffix}-{run}'
        log, sock = Path(f'{stem}.log'), Path(f'{stem}.sock')
        if log.exists() or sock.exists():
            raise SystemExit(f'refusing to overwrite {stem}')
        command = ['taskset', '-c', '4-7', 'qemu-system-x86_64', '-machine',
                   'q35,accel=tcg', '-cpu', 'max', '-smp', '1', '-m', '512',
                   '-display', 'none', '-no-reboot', '-nic', 'none', '-kernel', kernel,
                   '-initrd', str(base / f'measure/vt{suffix}.cpio'), '-append',
                   f'console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/vtprobe{suffix}',
                   '-serial', f'file:{log}', '-monitor', f'unix:{sock},server=on,wait=off']
        with Path(f'{stem}.qemu.log').open('wb') as output:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT)
            Path(f'{stem}.pid').write_text(f'{process.pid}\n')
            connection = None
            try:
                start = tick = time.monotonic()
                sent = 0
                while process.poll() is None:
                    now = time.monotonic()
                    if now - tick >= 60:
                        print(f'VT{suffix} run {run}: {now-start:.0f}s {sent}/{len(keys)} keys', flush=True)
                        tick = now
                    if now - start > 1500:
                        raise RuntimeError('VT timeout')
                    text = log.read_bytes() if log.exists() else b''
                    if sent < len(keys) and f'KEYREADY {sent} '.encode() in text:
                        if connection is None:
                            connection = socket.socket(socket.AF_UNIX)
                            connection.connect(str(sock))
                            connection.settimeout(0.2)
                        time.sleep(0.2)
                        connection.sendall(f'sendkey {keys[sent]}\n'.encode())
                        sent += 1
                        try:
                            connection.recv(65536)
                        except TimeoutError:
                            pass
                    time.sleep(0.1)
                if process.returncode != 0 or b'DONE px59' not in log.read_bytes():
                    raise RuntimeError(f'VT failed: exit {process.returncode}, log {log}')
            finally:
                if connection is not None:
                    connection.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
        rows = '\n'.join(line for line in log.read_text().splitlines() if line.startswith(prefixes)) + '\n'
        measured.append(rows)
        print(f'VT{suffix} run {run}: {len(rows.splitlines())} rows', flush=True)
    if measured[0] != measured[1]:
        raise SystemExit(f'VT{suffix} repeats disagree')
    Path(base / f'out/baseline-vt{suffix}.rows').write_text(measured[0])
    previous = (pax / f'notes/px59/vt{suffix}.rows').read_text()
    if measured[0] != previous:
        raise SystemExit(f'VT{suffix} differs from px59; inspect before changing the oracle')
    print(f'VT{suffix}: two repeats identical to px59, kernel {kernel}', flush=True)
