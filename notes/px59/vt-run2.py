#!/usr/bin/env python3
"""px59's second VT measurement: notes/px59/vtprobe2.c as pid 1 of kasumi's
own kernel image under QEMU (TCG, its VGA display, the PS/2 keyboard),
the keys sent through QEMU's monitor as the probe asks for each; twice,
the two runs' rows compared. Only this lane's QEMU, by its recorded pid.
    vt-run2.py LANE_DIR (the cpio at LANE_DIR/measure/vt2.cpio)"""
import os, pathlib, re, socket, subprocess, sys, time
base = pathlib.Path(sys.argv[1])
src = (pathlib.Path(__file__).resolve().parent / 'vtprobe2.c').read_text()
keys = re.search(r'static const char \*keys\[\] = \{(.*?)\};', src, re.S).group(1)
keys = re.findall(r'"([^"]+)"', keys)
kernel = f'/usr/lib/modules/{os.uname().release}/vmlinuz'
for run in (1, 2):
    log = base / f'out/vt2-{run}.log'
    sock = base / f'out/vt2-{run}.sock'
    sock.unlink(missing_ok=True)
    log.unlink(missing_ok=True)
    cmd = ['taskset', '-c', '0-3', 'qemu-system-x86_64', '-machine', 'q35,accel=tcg', '-cpu', 'max', '-smp', '1',
           '-m', '512', '-display', 'none', '-no-reboot', '-nic', 'none', '-kernel', kernel,
           '-initrd', str(base / 'measure/vt2.cpio'),
           '-append', 'console=ttyS0 quiet loglevel=0 panic=-1 rdinit=/vtprobe2',
           '-serial', f'file:{log}', '-monitor', f'unix:{sock},server=on,wait=off']
    with (base / f'out/vt2-{run}.qemu.log').open('wb') as output:
        p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
        (base / f'out/vt2-{run}.qemu.pid').write_text(str(p.pid))
        try:
            start = tick = time.monotonic()
            sent = 0
            s = None
            while p.poll() is None:
                now = time.monotonic()
                if now - tick >= 60:
                    print(f'VT2 {run}: {now - start:.0f}s, {sent}/{len(keys)} keys', flush=True)
                    tick = now
                if now - start > 1500:
                    raise RuntimeError('VT2 timeout')
                text = log.read_bytes() if log.exists() else b''
                if sent < len(keys) and f'KEYREADY {sent} '.encode() in text:
                    if s is None:
                        s = socket.socket(socket.AF_UNIX)
                        s.connect(str(sock))
                        s.settimeout(0.2)
                    time.sleep(0.2)
                    s.sendall(f'sendkey {keys[sent]}\n'.encode())
                    sent += 1
                    try:
                        s.recv(65536)
                    except (TimeoutError, socket.timeout):
                        pass
                time.sleep(0.1)
            if p.returncode != 0:
                raise RuntimeError(f'QEMU exit {p.returncode}')
            if b'DONE px59 vt2' not in log.read_bytes():
                raise RuntimeError('missing completion')
            print(f'VT2 {run}: done in {time.monotonic() - start:.0f}s, {sent} keys', flush=True)
        finally:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=10)
rows = []
for run in (1, 2):
    raw = (base / f'out/vt2-{run}.log').read_text(errors='replace').replace('\r', '')
    rows.append('\n'.join(l for l in raw.splitlines() if l.startswith(('STATE ', 'SCREEN ', 'QUERY ', 'ECHO ', 'KEY '))))
if rows[0] != rows[1]:
    a, b = rows[0].splitlines(), rows[1].splitlines()
    for x, y in zip(a, b):
        if x != y:
            print('first difference:\n  ' + x + '\n  ' + y)
            break
    raise RuntimeError('VT2 runs differ')
(base / 'out/vt2.rows').write_text(rows[0] + '\n')
print(f'VT2 twice: identical rows ({len(rows[0].splitlines())}); kernel {kernel} {os.uname().release}', flush=True)
