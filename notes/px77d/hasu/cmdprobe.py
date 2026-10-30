#!/usr/bin/env python3
"""px77d: boot ISO, wait for the halt, read Limine's executable-cmdline response and the
pointer it holds (through the halted CR3), and the memory map entry that pointer lies in."""
import json, re, socket, subprocess, sys, time
from pathlib import Path
iso, elf, out, fw = sys.argv[1:5]
out = Path(out); out.mkdir(parents=True, exist_ok=True); sock = out/'qmp.sock'; sock.unlink(missing_ok=True)
nm = {f[2]: int(f[0], 16) for f in (l.split() for l in subprocess.check_output(['nm', elf], text=True).splitlines()) if len(f) == 3}
root = Path('/home/mfwolffe/lanes/px77d/pax')
p = subprocess.Popen([str(root/'tools/qemu-run'), '--firmware', fw, '--timeout', '90', '--serial', str(out/'serial.log'), iso, '--', '-qmp', f'unix:{sock},server=on,wait=off'], stdout=open(out/'runner.log', 'w'), stderr=subprocess.STDOUT)
for _ in range(200):
    try: c = socket.socket(socket.AF_UNIX); c.connect(str(sock)); break
    except OSError: time.sleep(0.1)
r = c.makefile('rb'); json.loads(r.readline())
def q(n, a=None):
    c.sendall(json.dumps({'execute': n} | ({'arguments': a} if a else {})).encode() + b'\n')
    while True:
        v = json.loads(r.readline())
        if 'return' in v or 'error' in v: return v.get('return', v)
def h(cmd): return q('human-monitor-command', {'command-line': cmd})
q('qmp_capabilities')
for _ in range(300):
    regs = h('info registers')
    if 'HLT=1' in regs: break
    time.sleep(0.3)
def word(a):
    m = re.search(r':\s*0x([0-9a-f]+)', h('x /1gx 0x%x' % a)); return int(m[1], 16) if m else None
req = nm['limine_executable_cmdline_request']
resp = word(req + 40)
ptr = word(resp + 8) if resp else None
hhdm = word(word(nm['limine_hhdm_request'] + 40) + 8)
print('cr3', re.search(r'CR3=([0-9a-f]+)', regs)[1], 'response', hex(resp or 0), 'cmdline ptr', hex(ptr or 0), 'hhdm', hex(hhdm or 0))
if ptr:
    print(h('x /16bx 0x%x' % ptr).strip())
    pa = ptr - hhdm if ptr >= hhdm else ptr
    print('physical', hex(pa), 'phys bytes:', h('xp /8bx 0x%x' % pa).strip())
mm = word(nm['limine_memmap_request'] + 40); n = word(mm + 8); arr = word(mm + 16)
for i in range(n):
    e = word(arr + 8*i); b, l, t = word(e), word(e+8), word(e+16)
    if ptr and b <= (ptr - hhdm if ptr >= hhdm else ptr) < b + l:
        print('entry', i, 'base', hex(b), 'len', hex(l), 'type', t)
for line in open(out/'serial.log', errors='replace'):
    if line.startswith('memory:'): print(line.strip())
q('quit'); p.wait(timeout=20)
