#!/usr/bin/env python3
"""px76: no UART, no heap; inspect real QEMU pixels and halted guest RIP."""
import argparse, json, re, socket, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--image',required=True);p.add_argument('--elf',required=True)
p.add_argument('--output',required=True);p.add_argument('--mode',default='3840x2160')
a=p.parse_args();root=Path(__file__).resolve().parents[2];out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
sock=out/'qmp.sock';sock.unlink(missing_ok=True)
nm=subprocess.check_output(['nm','-S',a.elf],text=True)
m=re.search(r'^([0-9a-f]+) ([0-9a-f]+) T pax_halt$',nm,re.M)
assert m,'no sized pax_halt symbol';lo=int(m[1],16);hi=lo+int(m[2],16)
cmd=[str(root/'tools/qemu-run'),'--firmware','uefi','--no-serial','--display-mode='+a.mode,
     '--serial',str(out/'serial.log'),'--timeout','45',a.image,'--','-qmp',f'unix:{sock},server=on,wait=off']
with (out/'runner.log').open('wb') as log:
    proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
    conn=None;reader=None
    try:
        end=time.monotonic()+35
        while time.monotonic()<end:
            try:
                conn=socket.socket(socket.AF_UNIX);conn.connect(str(sock));break
            except (FileNotFoundError,ConnectionRefusedError):
                conn.close();conn=None
                if proc.poll() is not None: raise RuntimeError('QEMU exited before QMP')
                time.sleep(.05)
        assert conn,'QMP timeout';conn.settimeout(5);reader=conn.makefile('rb');json.loads(reader.readline())
        def qmp(name,args=None):
            msg={'execute':name}
            if args is not None: msg['arguments']=args
            conn.sendall(json.dumps(msg).encode()+b'\n')
            while True:
                value=json.loads(reader.readline())
                if 'error' in value: raise RuntimeError(value)
                if 'return' in value:return value['return']
        qmp('qmp_capabilities')
        while time.monotonic()<end:
            registers=qmp('human-monitor-command',{'command-line':'info registers'})
            rip=re.search(r'RIP=([0-9a-f]+)',registers)
            if rip and lo<=int(rip[1],16)<hi and 'HLT=1' in registers:break
            time.sleep(.1)
        else:raise RuntimeError('guest did not halt in pax_halt')
        (out/'registers.txt').write_text(registers)
        qmp('screendump',{'filename':str(out/'screen.ppm')})
        qmp('quit');proc.wait(timeout=5)
    finally:
        if reader:reader.close()
        if conn:conn.close()
        if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
assert (out/'serial.log').read_bytes()==b'','a UART was accidentally present'
header,shape,maxval,pixels=(out/'screen.ppm').read_bytes().split(b'\n',3)
w,h=map(int,shape.split());assert header==b'P6' and maxval==b'255'
assert f'{w}x{h}'==a.mode,(w,h,a.mode)
assert len(pixels)==w*h*3
scale=2 if w>2560 else 1
glyphs={};cp=None;rows=None
for line in (root/'font/spleen-8x16.bdf').read_text().splitlines():
    if line.startswith('ENCODING '):cp=int(line.split()[1])
    elif line=='BITMAP':rows=[]
    elif line=='ENDCHAR':glyphs[cp]=rows;rows=None
    elif rows is not None:rows.append(int(line,16))
lines=['PAX metal early','PANIC metal early witness 0x000000000000004c']
count=0
for y,text in enumerate(lines):
    for x,c in enumerate(text):
        for row,bits in enumerate(glyphs[ord(c)]):
            for col in range(8):
                colour=b'\xaa'*3 if bits&(0x80>>col) else b'\0'*3
                for dy in range(scale):
                    for dx in range(scale):
                        at=(((y*16+row)*scale+dy)*w+(x*8+col)*scale+dx)*3
                        assert pixels[at:at+3]==colour,(y,x,row,col,scale)
                        count+=1
print(f'PASS METAL no-serial early panic {w}x{h} scale{scale}: {count} exact pixels',flush=True)
