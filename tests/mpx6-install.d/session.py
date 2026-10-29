#!/usr/bin/env python3
"""Target alone, two boots and real shell edits; QEMU ends by monitor quit.
No host signals/process-table operations. Each image is a lane-owned copy.
"""
from pathlib import Path
import os
import re
import socket
import subprocess
import sys
import threading
import time

work=Path(sys.argv[1]);firmware=sys.argv[2]
image=work/('session-'+firmware+'.img');logpath=work/('session-'+firmware+'.serial')
subprocess.run(['cp','--sparse=always',str(Path(sys.argv[3]) if len(sys.argv)>3 else work/'target.img'),str(image)],check=True)
mon=str(work/('session-'+firmware+'.mon'))
if os.path.exists(mon):os.unlink(mon)
cmd=['qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max','-smp','4','-m','512M',
     '-display','none','-serial','stdio','-monitor','unix:'+mon+',server=on,wait=off','-nic','none',
     '-drive',f'file={image},if=none,id=d0,format=raw','-device','virtio-blk-pci,drive=d0,bootindex=0,serial=PX71-ROOT']
if firmware=='uefi':cmd+=['-drive','if=pflash,format=raw,unit=0,readonly=on,file='+os.environ.get('PAX_OVMF_CODE','/usr/share/OVMF/OVMF_CODE_4M.fd')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
buf=bytearray();lock=threading.Lock();log=logpath.open('wb')
def reader():
    for b in iter(lambda:p.stdout.read1(8192),b''):
        with lock:buf.extend(b)
        log.write(b);log.flush()
thread=threading.Thread(target=reader,daemon=True);thread.start()
def text():
    with lock:return bytes(buf)
def wait(predicate,what,seconds=120):
    end=time.monotonic()+seconds
    while not predicate(text()):
        assert p.poll() is None,'QEMU exited: '+what
        assert time.monotonic()<end,'timeout '+what+'\n'+text()[-4000:].decode(errors='replace')
        time.sleep(.1)
def prompt(boot,n):
    wait(lambda s:len(s.split(b'PAX: the console'))>boot and s.split(b'PAX: the console')[boot].count(b'$ ')>=n,f'boot {boot} prompt {n}')
def send(s,enter=True):
    for b in s.encode():
        p.stdin.write(bytes([b]));p.stdin.flush();time.sleep(.01)
    if enter:p.stdin.write(b'\r');p.stdin.flush()
try:
    # px78: the running root is refused before the allow-list is read,
    # even when the list names it (px78-plant-root lets the list win).
    commands=["echo 'model= serial=PX71-ROOT' > /tmp/allow",
              'pax-install --dry-run --target vda --seed test --user pax --games no --allow-list /tmp/allow','echo hello > /etc/motd','lope add /usr/share/tunes','lope list','cd',
              'echo written on PAX, before the reboot > notes.txt','echo root wrote this in /root > /root/note','reboot']
    for i,line in enumerate(commands,1):prompt(1,i);send(line)
    wait(lambda s:b'marked clean; restarting' in s,'reboot completed')
    for i,line in enumerate(['cat /etc/motd','lope list','cat notes.txt','cat /root/note','cat /proc/self/mounts','exit'],1):
        prompt(2,i);send(line)
    wait(lambda s:re.search(rb'\r?\nhalt\r?\n',s.split(b'PAX: the console')[-1]) is not None,'clean halt')
finally:
    # The monitor is a control protocol of this child, not a host signal.
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as monitor:
        monitor.settimeout(10)
        monitor.connect(mon)
        greeting=bytearray()
        while b'(qemu)' not in greeting:greeting.extend(monitor.recv(4096))
        monitor.sendall(b'quit\n')
        while monitor.recv(4096):pass
    p.wait(timeout=10);thread.join(timeout=5);log.close()
s=logpath.read_text(errors='replace').replace('\r','')
s=re.sub(r'\x1b\[[0-9;?=<>]*[A-Za-z]','',s)
boots=s.split('PAX: the console')[1:];assert len(boots)==2,s[-4000:]
for i,b in enumerate(boots,1):
    assert re.search(r'^root: PARTUUID=[0-9a-fA-F-]+ \(vda2\) on /: ext2, read-write, write-back$',b,re.M),b
    assert f'clean, mount {i};' in b,b
    assert re.search(r'fstab: PARTUUID=[0-9a-fA-F-]+ \(vda2\) is /: ext2, read-write, write-back',b),b
assert 'pax-install: refused: the running root: /dev/vda' in boots[0],boots[0]
second=boots[1]
for command,answer in [('cat /etc/motd','\nhello\n'),('lope list','/usr/share/tunes'),('cat notes.txt','written on PAX, before the reboot'),('cat /root/note','root wrote this in /root'),('cat /proc/self/mounts','/dev/root / ext2 rw,relatime 0 0')]:
    assert command in second and answer in second.split(command,1)[1].split('$ ',1)[0],(command,second)
check=work/('session-'+firmware+'-root.img')
with image.open('rb') as f,check.open('wb') as o:
    f.seek(69206016);left=467644416
    while left:
        b=f.read(min(left,1048576));assert b;o.write(b);left-=len(b)
r=subprocess.run(['e2fsck','-fn',check],capture_output=True);(work/('session-'+firmware+'.fsck')).write_bytes(r.stdout+r.stderr)
assert r.returncode==0 and b'WARNING' not in r.stdout+r.stderr,(r.stdout,r.stderr)
r=subprocess.run(['dumpe2fs','-h',check],capture_output=True,check=True)
assert re.search(rb'^Filesystem state:\s+clean$',r.stdout,re.M) and re.search(rb'^Mount count:\s+2$',r.stdout,re.M),r.stdout
image.unlink();check.unlink()
print(f'PASS I-session-{firmware}: target alone, motd/home/root/lope persisted across reboot, ext2 clean and mount count 2')
