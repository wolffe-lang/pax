#!/usr/bin/env python3
"""Exercise console keyboard bytes using QMP, on PS/2 and USB."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('--image', required=True)
p.add_argument('--output', required=True)
p.add_argument('--keyboard', choices=('ps2', 'usb'), required=True)
p.add_argument('--firmware', choices=('bios', 'uefi'), required=True)
p.add_argument('--accel', choices=('auto', 'tcg', 'kvm'), required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=True)
serial, qmp = out / 'serial.log', out / 'qmp.sock'
qmp.unlink(missing_ok=True)
# QEMU qcodes refer to physical US keys, not the resulting character.
printables = [('backslash', '|'), ('1', '!'), ('2', '@'), ('semicolon', ':'),
              ('apostrophe', '"'), ('comma', '<'), ('dot', '>'), ('slash', '?'),
              ('a', 'A'), ('z', 'Z'), ('0', ')')]
rows = []
for code, char in printables:
    for modifiers in (('alt', 'shift'), ('shift', 'alt')):
        rows.append((list(modifiers) + [code], b'\x1b' + char.encode()))
rows += [(['alt', 'shift', 'ctrl', 'a'], b''),
         (['shift', 'alt', 'ctrl', 'backslash'], b''),
         (['alt', 'shift', 'up'], b'\x1b[1;4A'),
         (['shift', 'alt', 'f1'], b''),
         (['shift', 'a'], b'A'),
         (['shift', 'backslash'], b'|'),
         (['alt_r', 'shift', 'a'], b''),
         (['alt_r', 'shift', '1'], b''),
         (['alt', 'backslash'], b'\x1b\\'),
         (['alt', 't'], b'\x1bt'),
         (['alt', 'w'], b'\x1bw'),
         (['alt', 'shift', 'ret'], b'')]
assert len(rows) == 34
cmd = [str(root / 'tools/qemu-run'), '--firmware', a.firmware, '--accel', a.accel,
       '--timeout', '180', '--serial', str(serial)]
if a.keyboard == 'usb': cmd += ['--usb-kbd']
cmd += [str(Path(a.image).resolve()), '--', '-qmp', f'unix:{qmp},server=on,wait=off']
env = dict(os.environ)
# The enclosing USB replay must not silently turn our PS/2 leg into USB.
env.pop('PAX_USB_KBD', None)
with (out / 'qemu.log').open('wb') as log:
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env)
    try:
        deadline = time.monotonic() + 120
        while not qmp.exists():
            if proc.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('QMP unavailable')
            time.sleep(.1)
        with socket.socket(socket.AF_UNIX) as sock:
            sock.connect(str(qmp))
            stream = sock.makefile('rb')
            json.loads(stream.readline())
            def command(name, arguments=None):
                req = {'execute': name}
                if arguments is not None: req['arguments'] = arguments
                sock.sendall(json.dumps(req).encode() + b'\n')
                while True:
                    reply = json.loads(stream.readline())
                    if 'error' in reply: raise RuntimeError(str(reply))
                    if 'return' in reply: return reply['return']
            command('qmp_capabilities')
            def wait_for(text, timeout=120):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    data = serial.read_bytes().replace(b'\r', b'') if serial.exists() else b''
                    for line in data.split(b'\n')[:-1]:
                        if line == text or line.startswith(text + b' '): return line
                    if proc.poll() is not None: raise RuntimeError('QEMU exited before ' + repr(text))
                    time.sleep(.05)
                raise RuntimeError('timed out waiting for ' + repr(text))
            failures = 0
            for i, (keys, want) in enumerate(rows):
                wait_for(f'KEYREADY {i}'.encode())
                def event(code, down):
                    return {'type': 'key', 'data': {'down': down, 'key': {'type': 'qcode', 'data': code}}}
                # Separate modifier reports so USB sees the actual order too.
                for k in keys:
                    command('input-send-event', {'events': [event(k, True)]})
                    time.sleep(.05)
                for k in reversed(keys):
                    command('input-send-event', {'events': [event(k, False)]})
                    time.sleep(.05)
                line = wait_for(f'KEYROW {i}'.encode(), 10)
                got = bytes.fromhex(line.decode().split(' ', 2)[2]) if len(line.split()) > 2 else b''
                ok = got == want
                failures += not ok
                print(f'{"PASS" if ok else "FAIL"} console-keys {a.keyboard} {"-".join(keys)} expected={want.hex()} actual={got.hex()}', flush=True)
            wait_for(b'KEYDONE', 10)
            if failures: raise SystemExit(1)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
