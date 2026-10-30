#!/usr/bin/env python3
"""px77d: one leg of tests/mpx6-triage. Boots IMAGE under tools/qemu-run with QMP,
waits until the guest halts (in boot/triage.S's t_halt or io.S's pax_halt) or QEMU
ends by itself (a reset: qemu-run passes -no-reboot), then reads the registers,
boot/triage.S's words by their symbols (`x` through the monitor, the halted CR3)
and the screendump, and checks what LEG expects. Prints PASS/FAIL lines by name.

  leg.py --leg NAME --image ISO --elf ELF --output DIR --firmware bios|uefi
         [--mode WxH] [--no-serial] [QEMU-RUN FLAGS...]

Written from the Intel SDM vol. 3A (CR4.MCE is bit 6) and QEMU's monitor
(`info registers`, `x`, `screendump`), run as a black box. No Linux source."""
import argparse, json, re, socket, subprocess, sys, time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--leg', required=True)
p.add_argument('--image', required=True)
p.add_argument('--elf', required=True)
p.add_argument('--output', required=True)
p.add_argument('--firmware', default='uefi')
p.add_argument('--mode', default='1280x800')
p.add_argument('--no-serial', action='store_true')
p.add_argument('--timeout', type=int, default=150)
a, rest = p.parse_known_args()  # the rest: tools/qemu-run's own flags (--no-pit, --high-bar)
root = Path(__file__).resolve().parents[2]
out = Path(a.output).resolve(); out.mkdir(parents=True, exist_ok=True)
sock = out / 'qmp.sock'; sock.unlink(missing_ok=True)
leg = a.leg

def fail(why):
    print(f'FAIL TRIAGE {leg}: {why}', flush=True)
    sys.exit(1)

# The symbols: io.S's sized pax_halt, triage.S's t_halt (local: the next symbol bounds it),
# pax_ud2, and triage.S's words.
syms = {}
order = []
for line in subprocess.check_output(['nm', '-n', '-S', a.elf], text=True).splitlines():
    f = line.split()
    if len(f) == 4:
        syms[f[3]] = (int(f[0], 16), int(f[1], 16)); order.append((int(f[0], 16), f[3]))
    elif len(f) == 3:
        syms[f[2]] = (int(f[0], 16), 0); order.append((int(f[0], 16), f[2]))
for need in ('pax_halt', 't_halt', 'pax_ud2', 'tg_on', 'tg_step', 'tg_f_vec', 'tg_f_rip', 'tg_f_src', 'tg_saved_cr3', 'tg_e_cr4'):
    if need not in syms:
        fail(f'no symbol {need} in {a.elf}')
lo, size = syms['pax_halt']; pax_halt = (lo, lo + size)
t = syms['t_halt'][0]
nxt = min(addr for addr, _ in order if addr > t)
t_halt = (t, nxt)

cmd = [str(root / 'tools/qemu-run'), '--firmware', a.firmware, '--timeout', str(a.timeout)]
if a.firmware == 'uefi':
    cmd.append('--display-mode=' + a.mode)
if a.no_serial:
    cmd.append('--no-serial')
cmd += ['--serial', str(out / 'serial.log')] + rest + [a.image, '--', '-qmp', f'unix:{sock},server=on,wait=off']
(out / 'command.json').write_text(json.dumps(cmd, indent=1) + '\n')
log = (out / 'runner.log').open('wb')
proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
conn = None
end = time.monotonic() + 60
while time.monotonic() < end:
    try:
        conn = socket.socket(socket.AF_UNIX); conn.connect(str(sock)); break
    except (FileNotFoundError, ConnectionRefusedError):
        conn.close(); conn = None
        if proc.poll() is not None:
            fail(f'QEMU exited before QMP ({proc.returncode})')
        time.sleep(0.05)
if not conn:
    fail('no QMP')
conn.settimeout(10)
reader = conn.makefile('rb'); json.loads(reader.readline())
def qmp(name, args=None):
    msg = {'execute': name}
    if args is not None:
        msg['arguments'] = args
    conn.sendall(json.dumps(msg).encode() + b'\n')
    while True:
        v = json.loads(reader.readline())
        if 'error' in v:
            raise RuntimeError(v)
        if 'return' in v:
            return v['return']
def hmp(c):
    return qmp('human-monitor-command', {'command-line': c})
qmp('qmp_capabilities')

# Wait for the halt, or for QEMU to end by itself (a reset under -no-reboot).
halted = None
regs = ''
end = time.monotonic() + a.timeout
try:
    while time.monotonic() < end:
        regs = hmp('info registers')
        m = re.search(r'RIP=([0-9a-f]+)', regs)
        if m and 'HLT=1' in regs:
            rip = int(m[1], 16)
            if t_halt[0] <= rip < t_halt[1]:
                halted = 't_halt'; break
            if pax_halt[0] <= rip < pax_halt[1]:
                halted = 'pax_halt'; break
        time.sleep(0.25)
except (OSError, json.JSONDecodeError, RuntimeError):
    pass
if halted is None:
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    ended = proc.poll()
    if leg.endswith('-reset'):
        if ended is None:
            proc.terminate(); proc.wait(timeout=10)
            fail('expected QEMU to end by a reset; it did not')
        print(f'PASS TRIAGE {leg}: no triage IDT, the fault became a reset (QEMU ended {ended} under -no-reboot)')
        sys.exit(0)
    proc.terminate(); proc.wait(timeout=10)
    fail(f'the guest never halted (QEMU {"running" if ended is None else "ended " + str(ended)})')
(out / 'registers.txt').write_text(regs)
def word(name):
    r = hmp('x /1gx 0x%x' % syms[name][0])
    m = re.search(r':\s*0x([0-9a-f]+)', r)
    if not m:
        fail(f'cannot read {name}: {r!r}')
    return int(m[1], 16)
w = {n: word(n) for n in ('tg_on', 'tg_step', 'tg_f_vec', 'tg_f_rip', 'tg_f_src', 'tg_saved_cr3', 'tg_e_cr4')}
cr4 = int(re.search(r'CR4=([0-9a-f]+)', regs)[1], 16)
(out / 'words.json').write_text(json.dumps({k: hex(v) for k, v in w.items()} | {'cr4': hex(cr4), 'halted': halted}, indent=1) + '\n')
qmp('screendump', {'filename': str(out / 'screen.ppm')})
qmp('quit')
try:
    proc.wait(timeout=10)
except subprocess.TimeoutExpired:
    proc.terminate(); proc.wait(timeout=10)
if leg.endswith('-reset'):
    fail(f'expected a reset, but the guest halted in {halted}')

# The screen and triage.S's geometry (t_fb_setup, t_steps).
hdr, shape, maxv, px = (out / 'screen.ppm').read_bytes().split(b'\n', 3)
W, H = map(int, shape.split())
def rgb(x, y):
    i = (y * W + x) * 3
    return (px[i] << 16) | (px[i + 1] << 8) | px[i + 2]
ss = 2
while (ss + 1) * 640 < W and ss < 16:
    ss += 1
band = 104 * ss
if band >= H // 2:
    band = H // 2
band_y = H - band
colours = [0xffffff, 0xff5555, 0x55ff55, 0xffff55, 0x55ffff, 0xff55ff, 0xffaa00, 0x8888ff]
def box(k):
    bw, bh = 14 * ss, 10 * ss
    x, y = 0, band_y + ss
    for j in range(1, k):
        x += bw
        if x + bw >= W:
            x = 0; y += bh
    return x, y
def has_box(k):
    x, y = box(k)
    return rgb(x, y) == colours[k & 7]
serial = (out / 'serial.log').read_bytes().decode('latin-1') if (out / 'serial.log').exists() else ''
ud2 = syms['pax_ud2'][0]
MCE = 0x40

def expect(cond, why):
    if not cond:
        fail(why + ' ' + json.dumps({k: hex(v) for k, v in w.items()} | {'cr4': hex(cr4), 'halted': halted}))

kind = leg.split('-')[0]
if kind == 'plain':
    expect(halted == 'pax_halt', 'without triage the kernel halts in pax_halt')
    expect(w['tg_on'] == 0, 'without triage tg_on stays 0')
    expect(cr4 & MCE == 0, 'without triage CR4.MCE stays clear')
    expect(not has_box(1), 'without triage no box is drawn')
elif kind in ('triage', 'kasumi'):
    expect(halted == 't_halt', 'triage halts in t_halt (kernel/panic -> triage.halted)')
    expect(w['tg_on'] == 1, 'tg_on')
    expect(w['tg_step'] == 26, 'the last box is 26')
    expect(cr4 & MCE != 0, 'triage sets CR4.MCE')
    expect(w['tg_e_cr4'] & MCE == 0, 'the handover CR4 had MCE clear')
    expect(all(has_box(k) for k in (1, 2, 6, 9, 26)), 'boxes 1, 2, 6, 9 and 26 drawn')
    expect(not has_box(27), 'no box 27')
    expect(w['tg_saved_cr3'] != 0, 'the boxes were drawn on Limine\'s CR3 (a saved CR3)')
elif kind == 'stop6':
    expect(halted == 't_halt', 'stop=6 halts in t_halt')
    expect(w['tg_step'] == 6 and w['tg_f_vec'] == 6, 'stopped at step 6')
    expect(rgb(0, 0) == 0x004000, 'the green banner')
    expect(has_box(6) and not has_box(7), 'boxes to 6, not 7')
elif kind in ('fault3', 'fault12'):
    n = 3 if kind == 'fault3' else 12
    expect(halted == 't_halt', 'the fault screen halts in t_halt')
    expect(w['tg_f_vec'] == 6 and w['tg_step'] == n, f'vector 6 at step {n}')
    expect(w['tg_f_rip'] == ud2, 'RIP is pax_ud2')
    expect(w['tg_f_src'] == (0 if n < 9 else 1), 'the triage IDT before box 9, PAX\'s fatal from box 9')
    expect(rgb(0, 0) == 0x600000, 'the dark red fault screen')
    if n == 12 and not a.no_serial:
        expect(re.search(r'^PANIC invalid opcode vector 6 ', serial, re.M) is not None, 'PAX\'s own PANIC line too')
elif kind == 'nomce':
    expect(halted == 't_halt' and w['tg_step'] == 26, 'triage nomce boots to the end')
    expect(cr4 & MCE == 0, 'nomce leaves CR4.MCE clear')
elif kind == 'nodraw':
    expect(halted == 't_halt' and w['tg_step'] == 26, 'triage nodraw boots to the end')
    expect(w['tg_saved_cr3'] == 0, 'nodraw never switched CR3 to draw a box')
elif kind == 'fullh':
    expect(halted == 't_halt' and w['tg_step'] == 26, 'triage fullh boots to the end')
else:
    fail('unknown leg')
cells = re.search(r'^screen: .* (\d+)x(\d+) cells;', serial, re.M)
if cells and kind in ('triage', 'fullh', 'plain'):
    rows = int(cells[2])
    full = H // (16 * (2 if W > 2560 else 1))
    if kind == 'triage':
        expect(rows == band_y // (16 * (2 if W > 2560 else 1)), f'the console stops above the band ({rows} rows)')
    else:
        expect(rows == min(full, 128), f'the console takes the whole height ({rows} rows)')
print(f'PASS TRIAGE {leg}: halted in {halted}, step {w["tg_step"]}, vector {w["tg_f_vec"]}, CR4 {cr4:#x}, {W}x{H}')
