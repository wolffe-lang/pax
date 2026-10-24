#!/usr/bin/env python3
"""Boot our VT probe twice and take timed pixel snapshots through QEMU."""
from pathlib import Path
import json
import os
import runpy
import socket
import subprocess
import sys
import time
L = Path(sys.argv[1]).resolve()
cases = runpy.run_path(str(L / 'pax/notes/px70/cases.py'))['CASES']
if len(sys.argv) > 2 and sys.argv[2] == 'header':
    def cstring(b):
        return '"' + ''.join('\\%03o' % x for x in b) + '"'
    header = 'static const struct { const char *name, *data; int pixels; } cases[] = {\n'
    header += ''.join('{%s,%s,%d},\n' % (json.dumps(n),cstring(b),p) for n,b,p in cases)
    (L / 'measure/cases70.h').write_text(header + '};\n')
    raise SystemExit(0)
kernel = os.environ['PAX_VT_KERNEL']
tag = os.environ.get('PAX_MEASURE_TAG', 'measure')
rows = []
for run in (1,2):
    base = L / f'out/{tag}-{run}'
    base.mkdir(exist_ok=False)
    log = base / 'serial.log'
    sock = base / 'qemu.sock'
    args = ['taskset','-c','0-3','qemu-system-x86_64','-machine','q35,accel=tcg',
            '-cpu','max','-smp','1','-m','512','-display','none','-no-reboot','-nic','none',
            '-kernel',kernel,'-initrd',str(L/'measure/px70.cpio'),'-append',
            'console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/vtprobe',
            '-serial',f'file:{log}','-monitor',f'unix:{sock},server=on,wait=off']
    with (base/'qemu.log').open('wb') as out:
        proc = subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT)
        (base/'pid').write_text(str(proc.pid))
        conn = None
        done = set()
        start = tick = time.monotonic()
        try:
            while proc.poll() is None:
                now = time.monotonic()
                if now - start > 600: raise RuntimeError('probe timeout')
                if now - tick > 30:
                    print(f'probe {run}: {now-start:.0f}s {len(done)} pixel cases',flush=True)
                    tick = now
                text = log.read_text(errors='replace') if log.exists() else ''
                for line in text.splitlines():
                    if not line.startswith('READY '): continue
                    name = line.split()[1]
                    if name in done: continue
                    if conn is None:
                        conn = socket.socket(socket.AF_UNIX)
                        conn.connect(str(sock)); conn.settimeout(0.2)
                    for i in range(12):
                        # 12 samples at 100ms spacing cross the blink phase.
                        target = base / f'{name}-{i}.ppm'
                        conn.sendall(f'screendump {target}\n'.encode())
                        until = time.monotonic()+5
                        while not target.exists():
                            if time.monotonic() > until: raise RuntimeError('missing dump')
                            time.sleep(.01)
                        time.sleep(.1)
                        try: conn.recv(65536)
                        except TimeoutError: pass
                    conn.sendall(b'sendkey ret\n')
                    done.add(name)
                time.sleep(.05)
            if proc.returncode != 0 or 'DONE px70' not in log.read_text():
                raise RuntimeError(f'probe failed: {proc.returncode}')
        finally:
            if conn: conn.close()
            if proc.poll() is None:
                proc.terminate(); proc.wait(timeout=10)
    rows.append('\n'.join(l for l in log.read_text().splitlines() if l.startswith(('SCREEN ','CMAP ','RGB ')))+'\n')
if rows[0] != rows[1]: raise RuntimeError('repeated rows differ')
(L/f'out/{tag}.rows').write_text(rows[0])
print(f'Two VT repeats identical: {len(rows[0].splitlines())} rows',flush=True)
