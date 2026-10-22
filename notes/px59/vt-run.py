#!/usr/bin/env python3
"""Drive only px59's QEMU instance, by its monitor and recorded pid."""
import os, pathlib, socket, subprocess, time
base = pathlib.Path.home() / 'lanes/px59'
keys = ['f1','f2','f3','f4','f5','f6','f7','f8','f9','f10','f11','f12','up','shift-up','ctrl-up','alt-up','shift-ctrl-up','alt-a','alt_r-a','dot']
for run in (1, 2):
    log = base / f'out/vt{run}.log'
    sock = base / f'out/vt{run}.sock'
    sock.unlink(missing_ok=True)
    cmd = ['taskset','-c','0-3','qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max','-smp','1','-m','512','-display','none','-no-reboot','-nic','none','-kernel',f'/usr/lib/modules/{os.uname().release}/vmlinuz','-initrd',str(base/'measure/vt.cpio'),'-append','console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/vtprobe','-serial',f'file:{log}','-monitor',f'unix:{sock},server=on,wait=off']
    with (base/f'out/vt{run}.qemu.log').open('wb') as output:
        p = subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
        (base/f'out/vt{run}.pid').write_text(str(p.pid))
        try:
            start = tick = time.monotonic(); sent = 0; s = None
            while p.poll() is None:
                now = time.monotonic()
                if now - tick >= 60:
                    print(f'VT {run}: {now-start:.0f}s, {sent}/{len(keys)} keys',flush=True); tick=now
                if now-start > 420: raise RuntimeError('VT timeout')
                text=log.read_bytes() if log.exists() else b''
                if sent<len(keys) and f'KEYREADY {sent} '.encode() in text:
                    if s is None:
                        s=socket.socket(socket.AF_UNIX); s.connect(str(sock)); s.settimeout(0.1)
                    s.sendall(f'sendkey {keys[sent]}\n'.encode()); sent+=1
                    try: s.recv(65536)
                    except TimeoutError: pass
                time.sleep(.1)
            if p.returncode != 0: raise RuntimeError(f'QEMU exit {p.returncode}')
            print(log.read_text(),flush=True)
            if b'DONE px59' not in log.read_bytes(): raise RuntimeError('missing completion')
        finally:
            if p.poll() is None: p.terminate(); p.wait(timeout=10)
rows=[]
for run in (1,2):
    raw=(base/f'out/vt{run}.log').read_text()
    rows.append('\n'.join(line for line in raw.splitlines() if line.startswith(('SCREEN ','QUERY ','KEY '))))
if rows[0]!=rows[1]: raise RuntimeError('VT runs differ')
(base/'out/vt.rows').write_text(rows[0]+'\n')
print('VT twice: identical rows',flush=True)
