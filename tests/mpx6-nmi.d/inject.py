#!/usr/bin/env python3
"""px77d: one injection of tests/mpx6-nmi. Boots IMAGE under tools/qemu-run frozen (-S) with
QEMU's gdb stub and QMP, runs to a hardware breakpoint at the kernel function AT, injects an
NMI or a machine check there, resumes, and records how the machine ends.

The NMI is a message, as a device's or the chipset's is: the stub, in its physical-memory mode
(`Qqemu.PhyMemMode:1`), writes 0x00000400 at 0xFEE00000, an MSI to APIC 0 whose delivery mode
(bits 10:8 of the data) is NMI. QMP's `inject-nmi` cannot be used: QEMU delivers it through the
local APIC's LINT1, which Limine hands over masked (`info lapic`: `LVT1 0x00010400 … masked NMI`)
and PAX never unmasks. Measured on hasu's QEMU 8.2.2: the MSI reaches the guest under KVM; under
TCG the write is lost, so an NMI row needs KVM (the caller skips it, loudly, without).
The machine check is the monitor's `mce` (bank 1, VAL|UC|EN|PCC, MCG status RIPV|MCIP), under
either accelerator. The outcomes:

  survive  it halts at the end of the boot (pax_halt) with `nmi: 1 at rip …` in its transcript
  panic    it halts in pax_halt with `PANIC <name> vector <v>` (and for a machine check `mce: bank 1`)
  reset    QEMU ends by itself (a triple fault or shutdown under qemu-run's -no-reboot)

  inject.py --image ISO --elf ELF --output DIR --firmware bios|uefi --at FUNCTION
            --kind nmi|mce --expect survive|panic|reset

Prints PASS/FAIL by name. Written from QEMU's gdb remote protocol and monitor, run as black
boxes (the client is px77b's), and the Intel SDM vol. 3A ch. 15 (the status bits)."""
import argparse, json, re, socket, subprocess, sys, time
from pathlib import Path

p = argparse.ArgumentParser()
for k in ('image', 'elf', 'output', 'at', 'kind', 'expect'):
    p.add_argument('--' + k, required=True)
p.add_argument('--firmware', default='uefi')
p.add_argument('--timeout', type=int, default=240)
p.add_argument('--accel', default='auto')
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
out = Path(a.output).resolve(); out.mkdir(parents=True, exist_ok=True)
name = f'{a.kind}@{a.at}'
def fail(why):
    print(f'FAIL NMI {a.firmware} {name}: {why}', flush=True); sys.exit(1)

syms = {}
for line in subprocess.check_output(['nm', '-S', a.elf], text=True).splitlines():
    f = line.split()
    if len(f) >= 3:
        syms[f[-1]] = (int(f[0], 16), int(f[1], 16) if len(f) == 4 else 0)
hits = [v[0] for k, v in syms.items() if re.fullmatch(r'_W' + re.escape(a.at) + r'\$[0-9a-f]+', k)]
if len(hits) != 1:
    fail(f'no single symbol for {a.at}: {hits}')
target = hits[0]
lo, size = syms['pax_halt']; halt = (lo, lo + size)

qsock, gsock = out / 'qmp.sock', out / 'gdb.sock'
for s in (qsock, gsock):
    s.unlink(missing_ok=True)
cmd = [str(root / 'tools/qemu-run'), '--firmware', a.firmware, '--timeout', str(a.timeout), '--accel', a.accel,
       '--serial', str(out / 'serial.log'), a.image, '--',
       '-qmp', f'unix:{qsock},server=on,wait=off', '-gdb', f'unix:{gsock},server=on,wait=off', '-S']
(out / 'command.json').write_text(json.dumps(cmd, indent=1) + '\n')
proc = subprocess.Popen(cmd, stdout=(out / 'runner.log').open('wb'), stderr=subprocess.STDOUT)
for _ in range(300):
    if qsock.exists() and gsock.exists():
        break
    if proc.poll() is not None:
        fail('QEMU exited before its sockets')
    time.sleep(0.05)
q = socket.socket(socket.AF_UNIX); q.connect(str(qsock)); q.settimeout(30)
qr = q.makefile('rb'); json.loads(qr.readline())
def qmp(n, args=None):
    q.sendall(json.dumps({'execute': n} | ({'arguments': args} if args is not None else {})).encode() + b'\n')
    while True:
        v = json.loads(qr.readline())
        if 'error' in v:
            raise RuntimeError(v)
        if 'return' in v:
            return v['return']
def hmp(c):
    return qmp('human-monitor-command', {'command-line': c})
qmp('qmp_capabilities')
g = socket.socket(socket.AF_UNIX); g.connect(str(gsock)); g.settimeout(a.timeout)
def rsp_send(s):
    b = s.encode(); g.sendall(b'$' + b + b'#' + f'{sum(b) % 256:02x}'.encode())
def rsp_packet():
    while g.recv(1) != b'$':
        pass
    data = b''
    while (c := g.recv(1)) != b'#':
        data += c
    g.recv(2); g.sendall(b'+'); return data.decode()
def rsp_call(s):
    rsp_send(s)
    while True:
        r = rsp_packet()
        if not re.match(r'^[TS][0-9a-f]{2}', r):
            return r
if rsp_call(f'Z1,{target:x},1') != 'OK':
    fail('the stub refused the hardware breakpoint')
rsp_send('c')
try:
    stop = rsp_packet()
except socket.timeout:
    fail(f'{a.at} was never reached')
if not re.match(r'^[TS]05', stop):
    fail(f'unexpected stop {stop!r}')
regs = hmp('info registers')
rip = int(re.search(r'RIP=([0-9a-f]+)', regs)[1], 16)
if rip != target:
    fail(f'stopped at {rip:#x}, not {a.at} {target:#x}')
(out / 'at-breakpoint.txt').write_text(regs)
if rsp_call(f'z1,{target:x},1') != 'OK':
    fail('the stub refused to clear the breakpoint')
try:
    if a.kind == 'nmi':
        for packet in ('Qqemu.PhyMemMode:1', 'Mfee00000,4:00040000', 'Qqemu.PhyMemMode:0'):
            if rsp_call(packet) != 'OK':
                fail(f'the stub refused {packet}')
    else:
        hmp('mce 0 1 0xb200000000000000 0x5 0x0 0x0')
    rsp_send('c')
except (OSError, RuntimeError, json.JSONDecodeError):
    pass  # QEMU ended at the injection itself (a machine check with CR4.MCE clear: a shutdown)

# Now: the halt, or QEMU's own end.
outcome = None
end = time.monotonic() + a.timeout
while time.monotonic() < end:
    if proc.poll() is not None:
        outcome = 'reset'; break
    try:
        r = hmp('info registers')
    except (OSError, RuntimeError, json.JSONDecodeError):
        time.sleep(0.2)
        if proc.poll() is not None:
            outcome = 'reset'; break
        continue
    m = re.search(r'RIP=([0-9a-f]+)', r)
    if m and 'HLT=1' in r and halt[0] <= int(m[1], 16) < halt[1]:
        outcome = 'halted'; (out / 'registers.txt').write_text(r); break
    time.sleep(0.25)
early = b''
if outcome == 'halted':
    # An NMI before serial.init's UART logs into kernel/screen's early buffer (replayed on the screen
    # at its attach), not to the port: read the buffer too.
    if 'pax_screen_early' in syms:
        try:
            va = syms['pax_screen_early'][0]  # QMP's `val` is a signed 64-bit integer
            qmp('memsave', {'val': va - (1 << 64) if va >= 1 << 63 else va, 'size': 16384, 'filename': str(out / 'screen-early.bin')})
            early = (out / 'screen-early.bin').read_bytes()
        except Exception as e:
            (out / 'screen-early.error').write_text(repr(e) + '\n')
    try:
        qmp('quit')
    except Exception:
        pass
try:
    proc.wait(timeout=20)
except subprocess.TimeoutExpired:
    proc.terminate(); proc.wait(timeout=10)
if outcome is None:
    fail('neither halted nor reset in time')
t = (out / 'serial.log').read_bytes().decode('latin-1').replace('\r', '') if (out / 'serial.log').exists() else ''
if outcome == 'halted':
    if re.search(r'^PANIC ', t, re.M):
        outcome = 'panic'
    elif re.search(r'^halt$', t, re.M):
        outcome = 'survive'
nmi_line = r'nmi: 1 at rip 0x[0-9a-f]+ reason 0x[0-9a-f]+, continuing'
seen = {'survive': bool(re.search('^' + nmi_line, t, re.M) or re.search(nmi_line.encode(), early)),
        'mce': bool(re.search(r'^mce: bank 1 status 0x', t, re.M)),
        'panic': (re.search(r'^PANIC .*$', t, re.M) or [''])[0]}
(out / 'outcome.json').write_text(json.dumps({'outcome': outcome, 'at': a.at, 'rip': hex(rip)} | seen, indent=1) + '\n')
if outcome != a.expect:
    fail(f'expected {a.expect}, got {outcome} {json.dumps(seen)}')
if outcome == 'survive' and a.kind == 'nmi' and not seen['survive']:
    fail('survived without its `nmi: 1 …` line')
if outcome == 'panic' and a.kind == 'mce' and not (seen['mce'] and 'machine check vector 18' in seen['panic']):
    fail(f'the machine check panic lacks its bank or its name: {json.dumps(seen)}')
print(f'PASS NMI {a.firmware} {name}: {outcome}' + (f' ({seen["panic"]})' if outcome == 'panic' else ''), flush=True)
