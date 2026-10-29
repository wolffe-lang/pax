#!/usr/bin/env python3
"""Qualify only regular image files; no serial, disks writable, USB keyboard input."""
from pathlib import Path
import hashlib, json, os, re, select, shutil, socket, struct, subprocess, time, zlib
L=Path('/home/mfwolffe/lanes/px77a'); O=L/'qualify-smoke'; O.mkdir(exist_ok=False)

def log(s): print(time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),s,flush=True)
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def disk(name, tag):
    p=O/name
    # Fully materialized, nonzero known content, distinct per disk. No sparse holes.
    block=hashlib.shake_256(tag).digest(1048576)
    with p.open('wb') as f:
        for _ in range(2048): f.write(block)
        f.flush(); os.fsync(f.fileno())
    assert p.stat().st_size==2*1024**3
    return p
nv=disk('nvme.img',b'px77a NVMe known content v1')
sa=disk('sata.img',b'px77a SATA known content v1')
before={p.name:sha(p) for p in (nv,sa)}
(O/'before.json').write_text(json.dumps(before,indent=2)+'\n'); log('before '+json.dumps(before))
code=Path('/usr/share/OVMF/OVMF_CODE_4M.fd'); var=Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
assert code.is_file() and var.is_file()
shutil.copyfile(var,O/'vars.fd')
symbols={p[2]:int(p[0],16) for line in (L/'out/kernel.symbols').read_text().splitlines() if len(p:=line.split())==3}
cmd=['qemu-system-x86_64','-machine','q35','-cpu','max','-m','2048M','-accel','tcg',
     '-display','none','-serial','none','-parallel','none','-nic','none','-no-reboot',
     '-drive',f'if=pflash,format=raw,unit=0,readonly=on,file={code}',
     '-drive',f'if=pflash,format=raw,unit=1,file={O}/vars.fd',
     '-device','qemu-xhci,id=xhci',
     '-drive',f'file={L}/out/pax-stick-6ccfe3fe+f1f8137b.img,if=none,id=stick,format=raw,readonly=on',
     '-device','usb-storage,bus=xhci.0,drive=stick,bootindex=0',
     '-device','qemu-xhci,id=pax-usb','-device','usb-kbd,id=pax-usb-kbd,bus=pax-usb.0,port=1',
     '-drive',f'file={nv},if=none,id=nv,format=raw','-device','nvme,serial=px77a-nvme,drive=nv',
     '-drive',f'file={sa},if=none,id=sa,format=raw','-device','ide-hd,bus=ide.0,drive=sa',
     '-qmp',f'unix:{O}/qmp.sock,server=on,wait=off',
     '-gdb',f'unix:{O}/gdb.sock,server=on,wait=off','-S']
(O/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
(O/'versions.txt').write_text(subprocess.check_output([cmd[0],'--version'],text=True)+
    subprocess.check_output(['sha256sum',str(code),str(var)],text=True)+
    subprocess.check_output(['taskset','-pc',str(os.getpid())],text=True))
qlog=(O/'qemu.log').open('wb'); proc=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=qlog,stderr=subprocess.STDOUT)
(O/'qemu.pid').write_text(str(proc.pid)+'\n')
class QMP:
    def __init__(self):
        self.s=socket.socket(socket.AF_UNIX); self.s.connect(str(O/'qmp.sock')); self.f=self.s.makefile('rb'); self.f.readline(); self.i=0; self.call('qmp_capabilities')
    def call(self,name,args=None):
        self.i+=1; ident=self.i
        self.s.sendall((json.dumps({'execute':name,'arguments':args or {},'id':ident})+'\n').encode())
        while True:
            r=json.loads(self.f.readline())
            if r.get('id')==ident:
                if 'error' in r: raise RuntimeError(r)
                return r.get('return')
    def hmp(self,s): return self.call('human-monitor-command',{'command-line':s})
def png(ppm, dest):
    # QEMU P6 PPM to truecolor PNG, no external decoder or synthetic screen.
    data=ppm.read_bytes(); match=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',data); assert match
    w,h=map(int,match.groups()); raw=data[match.end():]; assert len(raw)==w*h*3
    def chunk(k,b): return struct.pack('>I',len(b))+k+b+struct.pack('>I',zlib.crc32(k+b))
    filtered=b''.join(b'\0'+raw[y*w*3:(y+1)*w*3] for y in range(h))
    dest.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(filtered))+chunk(b'IEND',b''))
    return hashlib.sha256(raw).hexdigest()
def shot(name):
    p=O/'screen.ppm'; q.call('screendump',{'filename':str(p)}); return png(p,O/name)
def screen(name=None):
    # Read PAX's own exported terminal state/cells, not UART output.
    q.call('stop')
    a=symbols['pax_screen_state']; b=symbols['pax_screen_cells']
    r=q.hmp(f'memsave 0x{a:x} 536 "{O}/state.bin"'); assert not r,r
    state=struct.unpack('<67Q',(O/'state.bin').read_bytes())
    cols,rows=state[5:7]
    if not (state[0] and 1<=cols<=256 and 1<=rows<=128):
        q.call('cont'); return '',state
    offset=(256*128*4 if state[60] else 0)
    r=q.hmp(f'memsave 0x{b+offset:x} {cols*rows*4} "{O}/cells.bin"'); assert not r,r
    cells=struct.unpack('<'+str(cols*rows)+'I',(O/'cells.bin').read_bytes())
    text='\n'.join(''.join(chr(v&255) if 32<=v&255<127 else ' ' for v in cells[y*cols:(y+1)*cols]).rstrip() for y in range(rows)).rstrip()+'\n'
    if name:
        (O/(name+'.txt')).write_text(text); (O/(name+'.state.json')).write_text(json.dumps(list(state))+'\n')
    q.call('cont'); return text,state
def wait_text(needle,name,timeout=90):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        if proc.poll() is not None: raise RuntimeError('QEMU exited before '+name)
        text,state=screen()
        if re.search(needle,text):
            (O/(name+'.txt')).write_text(text); (O/(name+'.state.json')).write_text(json.dumps(list(state))+'\n'); return text,state
        time.sleep(.25)
    shot('failure.png'); raise RuntimeError('timeout waiting for '+name+'; '+text)
def key(k,down): q.call('input-send-event',{'events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':k}}}]})
def type_text(s):
    codes={' ':'spc','-':'minus','/':'slash','.':'dot','=':'equal','\n':'ret',';':'semicolon',':':'semicolon','$':'4','\'':'apostrophe'}
    for c in s:
        shift=c in ':$' or c.isupper()
        k=codes.get(c,c.lower())
        if shift:key('shift',True)
        key(k,True); time.sleep(.025); key(k,False)
        if shift:key('shift',False)
        time.sleep(.025)
def rsp_send(s):
    b=s.encode(); g.sendall(b'$'+b+b'#'+f'{sum(b)%256:02x}'.encode())
def rsp_recv():
    while g.recv(1)!=b'$': pass
    data=b''
    while (c:=g.recv(1))!=b'#': data+=c
    g.recv(2); g.sendall(b'+'); return data.decode()
rc=1
try:
    for _ in range(100):
        if (O/'qmp.sock').exists() and (O/'gdb.sock').exists(): break
        if proc.poll() is not None:raise RuntimeError('QEMU launch failed')
        time.sleep(.1)
    q=QMP(); g=socket.socket(socket.AF_UNIX); g.connect(str(O/'gdb.sock')); g.settimeout(300)
    addr=symbols['pax_user_thread']
    rsp_send(f'Z1,{addr:x},1'); assert rsp_recv()=='OK'
    rsp_send('c'); log('UEFI starts; sample actual menu until first user entry')
    last=''; candidates=[]; start=time.monotonic()
    while time.monotonic()-start<240:
        if select.select([g],[],[],0)[0]:
            # Initial RSP acknowledgement is not a stop reply.
            peek=g.recv(1,socket.MSG_PEEK)
            if peek==b'+':g.recv(1)
            elif peek==b'$':break
        name=f'menu-{len(candidates):03}.png'
        h=shot(name)
        if h!=last:candidates.append(name); last=h
        else:(O/name).unlink()
        time.sleep(.2)
    else: raise RuntimeError('first user entry not reached')
    stop=rsp_recv(); assert stop.startswith('T05') or stop.startswith('S05'),stop
    log('first user entry stopped '+stop)
    (O/'menu-candidates.json').write_text(json.dumps(candidates)+'\n')
    shot('02-last-boot-line.png')
    # At a stopped breakpoint snapshot before continuing; screen() continues via QMP.
    rsp_send(f'z1,{addr:x},1'); assert rsp_recv()=='OK'
    text,state=screen('02-last-boot-line')
    text,state=wait_text(r'(?m)^login: *$', '03-login')
    shot('03-login.png')
    lines=text.splitlines(); login=next(i for i,l in enumerate(lines) if l.startswith('login:'))
    (O/'boot-line-count.txt').write_text(f'{state[30]+login} rendered boot lines before login (scroll count {state[30]} + visible rows {login}); includes wrapped rows, not a UART transcript\n')
    log((O/'boot-line-count.txt').read_text().strip())
    type_text('root\n'); wait_text(r'(?m)^.*[$#] *$', 'root-shell')
    commands=['uname -a','cat /etc/pax-release','ls /dev','pax-install --inventory']
    transcript=[]
    for i,c in enumerate(commands,1):
        log('USB keyboard '+c); type_text(c+'\n'); time.sleep(1)
        text,state=wait_text(r'(?m)^.*[$#] *$',f'command-{i}')
        transcript.append('COMMAND '+c+'\n'+text)
    (O/'transcript.txt').write_text('\n'.join(transcript))
    assert 'nvme0n1' in transcript[-1], 'inventory must see NVMe'
    shot('04-after-commands.png')
    log('USB keyboard reboot'); type_text('reboot\n')
    proc.wait(timeout=60); assert proc.returncode==0,proc.returncode
    log('QEMU ended through reboot, exit 0'); rc=0
finally:
    if proc.poll() is None:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
    qlog.close()
    after={p.name:sha(p) for p in (nv,sa)}
    (O/'after.json').write_text(json.dumps(after,indent=2)+'\n'); log('after '+json.dumps(after))
    if before!=after:
        (O/'STOP-DISK-CHANGED').write_text('DO NOT STAGE\n'); raise RuntimeError('STOP disk image changed')
    log('PASS both writable 2 GiB disks unchanged')
    (O/'result.json').write_text(json.dumps({'exit':rc,'no_write':True,'before':before,'after':after},indent=2)+'\n')
if rc:raise SystemExit(rc)
