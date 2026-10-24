#!/usr/bin/env python3
from pathlib import Path
import json,os,runpy,socket,subprocess,sys,time
L=Path(sys.argv[1]).resolve()
keys=runpy.run_path(str(L/'pax/notes/px70/keys.py'))['KEYS']
if len(sys.argv)>2:
    (L/'measure/keys70.h').write_text('static const char *labels[]={'+','.join(json.dumps(n) for n,_ in keys)+'};\n')
    raise SystemExit(0)
tag=os.environ.get('PAX_KEYS_TAG','keys')
rows=[]
for run in (1,2):
    base=L/f'out/{tag}-{run}'; base.mkdir(exist_ok=False)
    log=base/'serial.log'; sock=base/'monitor.sock'
    args=['taskset','-c','12-15','qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max',
          '-smp','1','-m','512','-display','none','-no-reboot','-nic','none',
          '-kernel','/usr/lib/modules/7.3.0-4-cachyos/vmlinuz','-initrd',str(L/'measure/keys.cpio'),
          '-append','console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/keyprobe',
          '-serial',f'file:{log}','-monitor',f'unix:{sock},server=on,wait=off']
    with (base/'qemu.log').open('wb') as out:
        proc=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT)
        (base/'pid').write_text(str(proc.pid)); conn=None; sent=0; start=tick=time.monotonic()
        try:
            while proc.poll() is None:
                now=time.monotonic()
                if now-start>600: raise RuntimeError('key probe timeout')
                if now-tick>30:
                    print(f'keys {run}: {sent}/{len(keys)}',flush=True); tick=now
                text=log.read_bytes() if log.exists() else b''
                if sent<len(keys) and f'KEYREADY {sent} '.encode() in text:
                    if conn is None:
                        conn=socket.socket(socket.AF_UNIX); conn.connect(str(sock)); conn.settimeout(.2)
                    conn.sendall(f'sendkey {keys[sent][1]}\n'.encode()); sent+=1
                    try:
                        reply=conn.recv(65536)
                        if b'unknown' in reply.lower() or b'invalid' in reply.lower(): raise RuntimeError(reply)
                    except TimeoutError: pass
                time.sleep(.05)
            if proc.returncode!=0 or b'DONE px70 keys' not in log.read_bytes(): raise RuntimeError('key probe failed')
        finally:
            if conn: conn.close()
            if proc.poll() is None: proc.terminate(); proc.wait(timeout=10)
    rows.append('\n'.join(l for l in log.read_text().splitlines() if l.startswith('KEY '))+'\n')
if rows[0]!=rows[1]: raise RuntimeError('key repeats differ')
(L/f'out/{tag}.rows').write_text(rows[0]); print(f'keys twice identical: {len(rows[0].splitlines())}',flush=True)
