#!/usr/bin/env python3
"""px78: the running root refused when the install allow-list names it, on
NVMe. The smoke install's disk (log-last.img) is booted alone as an NVMe
namespace, standing in for kasumi's CachyOS root: a list naming that disk
by its model and serial is written, then `pax-install --check` and a
`--dry-run` at it must refuse it as the running root, before the list is
read (px78-plant-root lets the list win and turns this row red).
QEMU ends by the monitor's quit; no host signals. The image is a copy.
"""
from pathlib import Path
import os
import re
import socket
import subprocess
import sys
import threading
import time

work=Path(sys.argv[1]);source=Path(sys.argv[2])
image=work/'root-nvme.img';logpath=work/'root-nvme.serial'
subprocess.run(['cp','--sparse=always',str(source),str(image)],check=True)
mon=str(work/'root-nvme.mon')
if os.path.exists(mon):os.unlink(mon)
serial='PX78-ROOT-NVME'
cmd=['qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max','-smp','4','-m','512M',
     '-display','none','-serial','stdio','-monitor','unix:'+mon+',server=on,wait=off','-nic','none',
     '-drive',f'file={image},if=none,id=n0,format=raw','-device',f'nvme,drive=n0,serial={serial},bootindex=0']
p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
buf=bytearray();lock=threading.Lock();log=logpath.open('wb')
def reader():
    for b in iter(lambda:p.stdout.read1(8192),b''):
        with lock:buf.extend(b)
        log.write(b);log.flush()
thread=threading.Thread(target=reader,daemon=True);thread.start()
def text():
    with lock:return bytes(buf)
def wait(predicate,what,seconds=180):
    end=time.monotonic()+seconds
    while not predicate(text()):
        assert p.poll() is None,'FAIL I-root-nvme: QEMU exited: '+what
        assert time.monotonic()<end,'FAIL I-root-nvme: timeout '+what+'\n'+text()[-4000:].decode(errors='replace')
        time.sleep(.1)
def prompt(n):
    wait(lambda s:s.count(b'$ ')>=n,f'prompt {n}')
def send(s):
    for b in s.encode():
        p.stdin.write(bytes([b]));p.stdin.flush();time.sleep(.01)
    p.stdin.write(b'\r');p.stdin.flush()
try:
    # QEMU's NVMe model is "QEMU NVMe Ctrl"; the line names this disk exactly.
    commands=[f"echo 'model=QEMU NVMe Ctrl serial={serial}' > /tmp/allow",
              'pax-install --check --allow-list /tmp/allow',
              'pax-install --dry-run --target nvme0n1 --seed test --user pax --games no --allow-list /tmp/allow',
              'echo ROOT-NVME-END']
    for i,line in enumerate(commands,1):prompt(i);send(line)
    wait(lambda s:b'\nROOT-NVME-END' in s.replace(b'\r',b''),'the session end')
finally:
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
assert re.search(r'^root: PARTUUID=[0-9a-fA-F-]+ \(nvme0n1p2\) on /: ext2',s,re.M),'FAIL I-root-nvme: / is not on nvme0n1\n'+s[-4000:]
assert f'model=QEMU NVMe Ctrl serial={serial}' in s,'FAIL I-root-nvme: the identity\n'+s[-4000:]
assert 'refused: the running root: /dev/nvme0n1' in s,'FAIL I-root-nvme: --check did not refuse the running root\n'+s[-4000:]
assert 'pax-install: refused: the running root: /dev/nvme0n1' in s,'FAIL I-root-nvme: --dry-run planned the running root\n'+s[-4000:]
assert 'confirmation ERASE /dev/nvme0n1' not in s,'FAIL I-root-nvme: a plan for the running root\n'+s[-4000:]
image.unlink()
print('PASS I-root-nvme: the running root on NVMe, named on the allow-list, refused before the list is read')
