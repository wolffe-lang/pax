#!/usr/bin/env python3
"""px77d: the local APIC's LVT at a breakpoint (the monitor's `info lapic`), black box."""
import json, os, re, socket, subprocess, sys, time
from pathlib import Path
iso, elf, out, fw, at = sys.argv[1:6]
out = Path(out); out.mkdir(parents=True, exist_ok=True)
qs, gs = out/'q.sock', out/'g.sock'
for s in (qs, gs): s.unlink(missing_ok=True)
sy = {f[2]: int(f[0], 16) for f in (l.split() for l in subprocess.check_output(['nm', elf], text=True).splitlines()) if len(f) == 3}
t = [v for k, v in sy.items() if re.fullmatch(r'_W' + re.escape(at) + r'\$[0-9a-f]+', k)][0]
p = subprocess.Popen(['/home/mfwolffe/lanes/px77d/pax/tools/qemu-run', '--firmware', fw, '--accel', os.environ.get('ACCEL', 'tcg'), '--timeout', '120', '--serial', str(out/'serial.log'), iso, '--', '-qmp', f'unix:{qs},server=on,wait=off', '-gdb', f'unix:{gs},server=on,wait=off', '-S'], stdout=open(out/'run.log', 'w'), stderr=subprocess.STDOUT)
while not (qs.exists() and gs.exists()): time.sleep(0.05)
q = socket.socket(socket.AF_UNIX); q.connect(str(qs)); r = q.makefile('rb'); json.loads(r.readline())
def qm(n, a=None):
    q.sendall(json.dumps({'execute': n} | ({'arguments': a} if a else {})).encode() + b'\n')
    while True:
        v = json.loads(r.readline())
        if 'return' in v or 'error' in v: return v.get('return', v)
qm('qmp_capabilities')
g = socket.socket(socket.AF_UNIX); g.connect(str(gs))
def send(s): b = s.encode(); g.sendall(b'$' + b + b'#' + f'{sum(b) % 256:02x}'.encode())
def pkt():
    while g.recv(1) != b'$': pass
    d = b''
    while (c := g.recv(1)) != b'#': d += c
    g.recv(2); g.sendall(b'+'); return d.decode()
import os
accel = os.environ.get('ACCEL', 'tcg')
send(f'Z1,{t:x},1'); print('Z1', pkt())
send('c'); print('stop', pkt())
send(f'z1,{t:x},1'); print('z1', pkt())
send('Qqemu.PhyMemMode:1'); print('phys', pkt())
send('Mfee00360,4:00040000'); print('lint1 write', pkt())
send('mfee00360,4'); print('lint1 read', pkt())
send('Qqemu.PhyMemMode:0'); print('virt', pkt())
print(qm('human-monitor-command', {'command-line': 'info lapic'}).splitlines()[3])
print('inject', qm('inject-nmi'))
send('c')
for i in range(120):
    if p.poll() is not None: print('QEMU ended', p.returncode, 'after', i*0.5, 's: RESET'); break
    regs = qm('human-monitor-command', {'command-line': 'info registers'})
    if 'HLT=1' in regs: print('halted', re.search(r'RIP=([0-9a-f]+)', regs)[1]); break
    time.sleep(0.5)
tail = (out/'serial.log').read_bytes().decode('latin-1').replace('\r','').splitlines()
print('nmi lines', [l for l in tail if l.startswith(('nmi:','PANIC'))][:3], 'last', tail[-1:] )
try: qm('quit')
except Exception: pass
