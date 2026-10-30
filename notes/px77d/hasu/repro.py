#!/usr/bin/env python3
"""px77d: boot a stick image under OVMF shaped like kasumi and record how it ends.
   repro.py NAME IMAGE ACCEL DISPLAY SERIAL MEM SMP SECONDS [extra qemu args...]
   ACCEL kvm|tcg; DISPLAY vga|bochs|none; SERIAL file|none; MEM like 32G.
   At the end (or when QEMU pauses on a reset/shutdown) it records query-status, info registers,
   info pci, a screendump and the serial file."""
import json, os, shutil, socket, struct, subprocess, sys, time, zlib
from pathlib import Path
name, img, accel, disp, serial, mem, smp, secs = sys.argv[1:9]
extra = sys.argv[9:]
L = Path('/home/mfwolffe/lanes/px77d'); O = L/'runs'/name; O.mkdir(parents=True, exist_ok=False)
def log(s): print(time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), name, s, flush=True)
code = '/usr/share/OVMF/OVMF_CODE_4M.fd'; shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', O/'vars.fd')
cpu = 'host' if accel == 'kvm' else 'max'
pre = os.environ.get('PRE', '').split()
machine = os.environ.get('MACHINE', 'q35,pit=off')
cmd = ['qemu-system-x86_64', '-machine', machine, '-cpu', cpu, '-m', mem, '-smp', smp, '-accel', accel] + pre + [
       '-display', 'none', '-vga', 'none', '-parallel', 'none', '-nic', 'none',
       '-action', 'reboot=shutdown,shutdown=pause',
       '-drive', f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
       '-drive', f'if=pflash,format=raw,unit=1,file={O}/vars.fd',
       '-device', 'nec-usb-xhci,id=xhci,msi=on,msix=off',
       '-drive', f'file={img},if=none,id=stick,format=raw,readonly=on',
       '-device', 'usb-storage,bus=xhci.0,drive=stick,bootindex=0',
       '-device', 'nec-usb-xhci,id=pax-usb,msi=on,msix=off',
       '-device', 'usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1',
       '-fw_cfg', 'name=opt/ovmf/X-PciMmio64Mb,string=262144',
       '-qmp', f'unix:{O}/qmp.sock,server=on,wait=off']
if disp == 'vga': cmd += ['-device', 'VGA,vgamem_mb=64,xres=3840,yres=2160']
elif disp == 'bochs': cmd += ['-device', 'bochs-display,vgamem=64M,xres=3840,yres=2160']
elif disp == 'virtio': cmd += ['-device', 'virtio-vga,xres=3840,yres=2160']
cmd += ['-serial', f'file:{O}/serial.log'] if serial == 'file' else ['-serial', 'none']
cmd += extra
(O/'command.json').write_text(json.dumps(cmd, indent=1)+'\n')
log('start '+' '.join(cmd))
p = subprocess.Popen(cmd, stdout=open(O/'qemu.out', 'w'), stderr=subprocess.STDOUT)
sock = None
for _ in range(100):
    try:
        sock = socket.socket(socket.AF_UNIX); sock.connect(str(O/'qmp.sock')); break
    except OSError:
        sock = None; time.sleep(0.1)
assert sock, 'no qmp'
f = sock.makefile('rw')
def rd():
    while True:
        m = json.loads(f.readline())
        if 'event' in m:
            (O/'events.log').open('a').write(json.dumps(m)+'\n'); continue
        return m
def qmp(c, **a):
    f.write(json.dumps({'execute': c, 'arguments': a} if a else {'execute': c})+'\n'); f.flush(); return rd()
rd(); qmp('qmp_capabilities')
def hmp(c): return qmp('human-monitor-command', **{'command-line': c}).get('return', '')
def png(src, dst):
    b = open(src, 'rb').read()
    parts = b.split(b'\n', 3); w, h = map(int, parts[1].split()); px = parts[3]
    raw = b''.join(b'\x00' + px[y*w*3:(y+1)*w*3] for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(dst, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
def shot(tag):
    qmp('screendump', filename=str(O/f'{tag}.ppm'))
    try: png(O/f'{tag}.ppm', O/f'{tag}.png'); os.unlink(O/f'{tag}.ppm')
    except Exception as e: log(f'png {tag}: {e}')
entry = int(os.environ.get('ENTRY', '1'))
t0 = time.time(); status = None
picked = entry == 1
while time.time() - t0 < float(secs):
    time.sleep(2)
    if not picked and time.time() - t0 > float(os.environ.get('MENU_AT', '9')):
        shot('menu')
        for _ in range(entry - 1):
            qmp('send-key', keys=[{'type': 'qcode', 'data': 'down'}]); time.sleep(0.2)
        shot('menu-picked')
        qmp('send-key', keys=[{'type': 'qcode', 'data': 'ret'}]); picked = True
        log(f'picked entry {entry}')
    if p.poll() is not None: break
    status = qmp('query-status').get('return', {})
    if status.get('status') not in ('running', None):
        log('status '+json.dumps(status)); break
    if int(time.time()-t0) % 30 < 2: log(f'running {int(time.time()-t0)} s')
if p.poll() is None:
    status = qmp('query-status').get('return', {})
    (O/'status.json').write_text(json.dumps(status)+'\n')
    (O/'registers.txt').write_text(hmp('info registers'))
    (O/'pci.txt').write_text(hmp('info pci'))
    (O/'mtree.txt').write_text(hmp('info mtree -f'))
    shot('screen')
    qmp('quit')
p.wait(timeout=60)
log(f'end status {json.dumps(status)} qemu exit {p.returncode}')
sl = O/'serial.log'
if sl.exists():
    t = sl.read_bytes().decode('latin-1').splitlines()
    log(f'serial {len(t)} lines; last: ' + ' | '.join(t[-6:]))
