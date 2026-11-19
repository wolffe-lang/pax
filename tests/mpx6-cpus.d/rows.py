"""The processor rows: px138's census (stage 0) and px161's idle processors (stage 1).

  rows.py SERIAL N [DISABLED] [--mode default|nosmp|nmi] [--elf KERNEL.elf | --symbols NM.txt]

SERIAL is a boot's transcript; SERIAL.cmdK are the monitor's answers to tests/mpx6-cpus's commands
(`stop`, `info registers -a`, `cont`, three times: dumps in .cmd2, .cmd5 and .cmd8). N is the
processors the machine has (or `unknown`, booted with no ACPI), DISABLED the MADT's disabled entries.

Stage 0, every boot:
  CPU-CENSUS   the boot line and /proc/pax-cpus's first lines agree on the firmware's counts.
Stage 1 (px161):
  SMP-ENTER    with N > 1 the boot line says N-1 application processors idle of N-1, and the proc
               file says `started N`, `idle N-1` and one line a processor, each APIC ID once.
  SMP-ONE      with one processor (or no ACPI): no `cpus:` line, `started 1`, `idle 0`, cpu 0 alone.
  SMP-IDLE     every application processor's RIP lies in pax_ap_halt with QEMU's HLT=1, in one of
               three dumps at least; the boot processor's lies in the kernel.
  SMP-PRIVATE  per processor its own GS base (pax_cpu0, or slot 417 + 256 KiB x its index), GDT and
               TSS (in its record page), its RSP in its own idle stack; one IDT, pax_idt; every
               application processor's CR0, CR3, CR4 and EFER the boot processor's; the kernel's own
               check of the records and stacks said.
  SMP-TICKS    the probe's two reads 300 ms apart: every application processor's ticks and wakes
               advance by 10 at least, its current thread idle; the boot processor's is the probe.
  SMP-SCHED    no processor stopped (an application processor in the scheduler stops by name).
  SMP-USER-GS  ring 3's GS base is its own (0), never the kernel's record.
  SMP-NMI      (--mode nmi) every application processor took one NMI, and ticks after it.
  SMP-NOSMP    (--mode nosmp) the application processors left parked, outside the kernel
               (stage 0's CPU-PARKED), `started 1`.
"""
import argparse
import pathlib
import re
import subprocess
import sys

CPUS_VA = 0xffffd08000000000   # kernel/cpus: PML4 slot 417, a window a processor
SPAN = 0x40000                 # 256 KiB a window
GDT_OFF, TSS_OFF = 256, 384    # in the record page, the window's first
STACK_LO, STACK_HI = 0x8000, 0xc000  # the idle stack, above a guard
KERNEL = 0xffffffff80000000

ap = argparse.ArgumentParser()
ap.add_argument('serial')
ap.add_argument('n')
ap.add_argument('disabled', nargs='?', type=int, default=0)
ap.add_argument('--mode', default='default', choices=('default', 'nosmp', 'nmi'))
ap.add_argument('--elf')
ap.add_argument('--symbols', help='`nm -S` output in a file, in place of --elf (rows-selftest)')
a = ap.parse_args()

text = pathlib.Path(a.serial).read_text(errors='replace').replace('\r', '')
n = a.n
tag = f'smp={n}' + (f' disabled={a.disabled}' if a.disabled else '') + ('' if a.mode == 'default' else f' {a.mode}')
red = []


def fail(row, why):
    print(f'FAIL {row} {tag}: {why}')
    red.append(row)


def ok(row, what):
    print(f'PASS {row} {tag}: {what}')


def block(name):
    m = re.search(rf'^{name} begin\n(.*?)^{name} end$', text, re.M | re.S)
    return m[1] if m else None


# --- stage 0 ---------------------------------------------------------------------------------
source = 'unavailable' if n == 'unknown' else 'ACPI MADT'
line = f'processors: available {n}, active 1; source {source}'
extra = '' if n == 'unknown' else f'online-capable 0\ndisabled {a.disabled}\n'
head = f'available {n}\nactive 1\nsource {source}\n{extra}'
proc1, proc2 = block('CPU-PROC'), block('CPU-PROC2')
if text.count(line + '\n') != 1 or proc1 is None or not proc1.startswith(head):
    # Said, and the stage 1 rows still run: each says what it found missing (px161: a probe that died
    # before its lines once hid every row behind this one).
    fail('CPU-CENSUS', f'boot summary {text.count(line + chr(10))} times, proc record '
         f'{"missing" if proc1 is None else "differs"}; the transcript\'s last lines:')
    print('\n'.join('  ' + x for x in text.splitlines()[-12:]))
else:
    ok('CPU-CENSUS', f'available={n} active=1 boot=proc')

# --- stage 1 ---------------------------------------------------------------------------------
cpus = 1 if n == 'unknown' else int(n)   # with no ACPI the bootloader starts no processor
aps = cpus - 1
LINE = re.compile(r'^cpu (\d+) apic (\d+) (boot|idle|parked|stopped|never entered)(.*)$', re.M)


def lines(p):
    return {int(m[1]): (int(m[2]), m[3], m[4]) for m in LINE.finditer(p or '')}


def word(rest, key):
    m = re.search(rf'\b{key} (\d+)\b', rest or '')
    return int(m[1]) if m else None


def count(p, key):
    m = re.search(rf'^{key} (\d+)$', p or '', re.M)
    return int(m[1]) if m else None


def rest(rows, i):
    return rows.get(i, (0, '', ''))[2]


started, idle = count(proc1, 'started'), count(proc1, 'idle')
one, two = lines(proc1), lines(proc2)
boot = re.findall(r'^cpus: .*$', text, re.M)
pid = re.search(r'^CPU-PID (\d+)$', text, re.M)

if a.mode == 'nosmp':
    want = f'cpus: application processors left parked {aps} of {aps} (nosmp)'
    if aps and boot != [want]:
        fail('SMP-NOSMP', f'boot lines {boot}, want [{want!r}]')
    elif started != 1 or idle != 0 or sorted(one) != list(range(cpus)) \
            or one[0][1] != 'boot' or any(one[i][1] != 'parked' for i in range(1, cpus)):
        fail('SMP-NOSMP', f'proc: started {started}, idle {idle}, lines {one}')
    else:
        ok('SMP-NOSMP', f'{aps} left parked, started 1')
elif cpus == 1:
    if boot or started != 1 or idle != 0 or sorted(one) != [0] or one[0][1] != 'boot':
        fail('SMP-ONE', f'boot lines {boot}; proc started {started}, idle {idle}, lines {one}')
    else:
        ok('SMP-ONE', 'no cpus: line; started 1, idle 0, cpu 0 alone')
else:
    want = re.compile(rf'^cpus: application processors idle {aps} of {aps} in \d+ ms, \d+ KiB each '
                      r'\(\d+ KiB with their tables\); the boot processor runs every thread$')
    apics = sorted(v[0] for v in one.values())
    if not any(want.match(b) for b in boot):
        fail('SMP-ENTER', f'no boot line "idle {aps} of {aps}": {boot}')
    elif started != cpus or idle != aps:
        fail('SMP-ENTER', f'proc: started {started}, idle {idle}')
    elif sorted(one) != list(range(cpus)) or one[0][1] != 'boot' \
            or any(one[i][1] != 'idle' for i in range(1, cpus)):
        fail('SMP-ENTER', f'proc lines: {one}')
    elif len(set(apics)) != cpus or one[0][0] != 0:
        fail('SMP-ENTER', f'APIC IDs not one each, or the boot processor not APIC 0: {apics}')
    else:
        ok('SMP-ENTER', f'{aps} application processors idle, APIC IDs {apics}')

# The probe's own line: ring 3's GS.
gs = re.findall(r'^CPU-USER-GS .*$', text, re.M)
if gs != ['CPU-USER-GS ok 3 reads']:
    fail('SMP-USER-GS', f'probe said {gs or "nothing (it died: a fault on %gs:0x200000?)"}')
else:
    ok('SMP-USER-GS', "ring 3's GS base its own, 3 reads")

if a.mode != 'nosmp':
    stopped = [b for b in boot if ' stopped' in b or 'never reached' in b]
    bad = sorted({i for rows in (one, two) for i, v in rows.items() if v[1] in ('stopped', 'never entered')})
    if stopped or bad:
        fail('SMP-SCHED', f'stopped or never entered: boot {stopped}, proc cpus {bad}')
    else:
        ok('SMP-SCHED', 'no processor stopped')

    # Two reads: the application processors tick while the boot processor runs the probe.
    cur = rest(one, 0)
    if pid is None or 'current pid' not in cur or word(cur, 'pid') != int(pid[1]):
        fail('SMP-TICKS', f'cpu 0 current {cur.strip()!r}, the probe is pid {pid[1] if pid else "?"}')
    else:
        slow = []
        for i in range(1, cpus):
            r1, r2 = rest(one, i), rest(two, i)
            t1, t2, w1, w2 = word(r1, 'ticks'), word(r2, 'ticks'), word(r1, 'wakes'), word(r2, 'wakes')
            if None in (t1, t2, w1, w2) or t2 - t1 < 10 or w2 - w1 < 10 or 'current idle' not in r1:
                slow.append((i, r1.strip(), r2.strip()))
        if slow:
            fail('SMP-TICKS', f'not ticking, or not idle: {slow}')
        else:
            ok('SMP-TICKS', f'{aps} application processors ticked in 300 ms; cpu 0 runs the probe')

    if a.mode == 'nmi':
        want = f'cpus: application processors took an NMI each {aps} of {aps}, each on its own stack'
        nmis = [word(rest(one, i), 'nmis') for i in range(1, cpus)]
        first = [word(rest(one, i), 'ticks') or 0 for i in range(1, cpus)]
        later = [word(rest(two, i), 'ticks') or 0 for i in range(1, cpus)]
        if want not in boot or nmis != [1] * aps or any(b - f < 10 for f, b in zip(first, later)):
            fail('SMP-NMI', f'boot {boot}; nmis {nmis}; ticks {first} then {later}')
        else:
            ok('SMP-NMI', f'{aps} NMIs, one each, ticking after')


# --- the register dumps ------------------------------------------------------------------------
def dumps():
    out = []
    for k in (2, 5, 8):
        p = pathlib.Path(f'{a.serial}.cmd{k}')
        if p.exists():
            out.append(p.read_text(errors='replace'))
    return out


def parse(d):
    found = {}
    for part in re.split(r'^(?=CPU#\d+)', d, flags=re.M):
        m = re.match(r'CPU#(\d+)', part)
        if not m:
            continue
        r = {}
        for key, pat in (('rip', r'\b[RE]IP=([0-9a-f]+)'), ('rsp', r'\b[RE]SP=([0-9a-f]+)'),
                         ('hlt', r'\bHLT=([01])'), ('gs', r'^GS =[0-9a-f]{4} ([0-9a-f]+)'),
                         ('tr', r'^TR =[0-9a-f]{4} ([0-9a-f]+)'), ('gdt', r'^GDT=\s*([0-9a-f]+)'),
                         ('idt', r'^IDT=\s*([0-9a-f]+)'), ('cr0', r'\bCR0=([0-9a-f]+)'),
                         ('cr3', r'\bCR3=([0-9a-f]+)'), ('cr4', r'\bCR4=([0-9a-f]+)'),
                         ('efer', r'\bEFER=([0-9a-f]+)')):
            mm = re.search(pat, part, re.M)
            r[key] = int(mm[1], 16) if mm else None
        found[int(m[1])] = r
    return found


def symbols(elf):
    for tool in ('nm', 'llvm-nm'):
        if a.symbols:
            out = pathlib.Path(a.symbols).read_text()
        else:
            try:
                out = subprocess.run([tool, '-S', '--defined-only', elf], capture_output=True, text=True, check=True).stdout
            except (OSError, subprocess.CalledProcessError):
                continue
        syms = {}
        for ln in out.splitlines():
            f = ln.split()
            if len(f) == 4:
                syms[f[3]] = (int(f[0], 16), int(f[1], 16))
            elif len(f) == 3:
                syms[f[2]] = (int(f[0], 16), 0)
        return syms
    print('FAIL SMP-SYMBOLS: neither nm nor llvm-nm read the kernel')
    sys.exit(1)


ds = [parse(d) for d in dumps()]
if a.mode == 'nosmp' or cpus > 1:
    row = 'CPU-PARKED' if a.mode == 'nosmp' else 'SMP-IDLE'
    if not ds or len(ds[0]) != cpus:
        fail(row, f'register dumps: {len(ds)}, processors in the first: {len(ds[0]) if ds else 0}')
    elif a.mode == 'nosmp':
        ips = [ds[0][i]['rip'] for i in sorted(ds[0])]
        if ips[0] is None or ips[0] < KERNEL or any(ip is None or ip >= KERNEL for ip in ips[1:]):
            fail('CPU-PARKED', f'unexpected processor instruction pointers: {[hex(x or 0) for x in ips]}')
        else:
            ok('CPU-PARKED', f'{len(ips) - 1} secondary processors outside the kernel')
    else:
        syms = symbols(a.elf)
        lo, size = syms.get('pax_ap_halt', (0, 0))
        hi = lo + size

        def inloop(c):
            return lo <= (c.get('rip') or 0) < hi and c.get('hlt') == 1
        halted = {i: any(inloop(d.get(i, {})) for d in ds) for i in range(1, cpus)}
        b0 = ds[0][0]['rip'] or 0
        if not size or not all(halted.values()) or b0 < KERNEL:
            where = [(i, [hex(d.get(i, {}).get('rip') or 0) for d in ds]) for i, v in halted.items() if not v]
            fail('SMP-IDLE', f'pax_ap_halt [{lo:#x}, {hi:#x}); cpu 0 RIP {b0:#x}; not halted there: {where}')
        else:
            ok('SMP-IDLE', f'{aps} application processors halted in pax_ap_halt')

        # Private state, from the first dump in which every application processor sat in its loop.
        d = next((d for d in ds if all(inloop(d.get(i, {})) for i in range(1, cpus))), ds[0])
        index = {v[0]: i for i, v in one.items()}   # APIC ID -> record index (QEMU's CPU#k is APIC k)
        idt = syms.get('pax_idt', (None, 0))[0]
        why = []
        if d[0]['gs'] != syms.get('pax_cpu0', (None, 0))[0]:
            why.append(f'cpu 0 GS {d[0]["gs"] or 0:#x} is not pax_cpu0')
        if d[0]['gdt'] != syms.get('pax_gdt', (None, 0))[0] or d[0]['tr'] != syms.get('pax_tss', (None, 0))[0]:
            why.append('cpu 0 GDT or TR is not pax_gdt / pax_tss')
        for k in range(1, cpus):
            c, i = d.get(k, {}), index.get(k)
            if not i:
                why.append(f'CPU#{k} (APIC {k}) has no record line')
                continue
            rec = CPUS_VA + i * SPAN
            if c.get('gs') != rec:
                why.append(f'CPU#{k} GS {c.get("gs") or 0:#x}, its record {rec:#x}')
            if c.get('gdt') != rec + GDT_OFF or c.get('tr') != rec + TSS_OFF:
                why.append(f'CPU#{k} GDT {c.get("gdt") or 0:#x} TR {c.get("tr") or 0:#x}, its record {rec:#x}')
            if not rec + STACK_LO <= (c.get('rsp') or 0) < rec + STACK_HI:
                why.append(f'CPU#{k} RSP {c.get("rsp") or 0:#x} outside its idle stack')
            for reg in ('cr0', 'cr3', 'cr4', 'efer'):
                if c.get(reg) != d[0][reg]:
                    why.append(f'CPU#{k} {reg} {c.get(reg) or 0:#x}, the boot processor\'s {d[0][reg] or 0:#x}')
        for key in ('gs', 'gdt', 'tr', 'rsp'):
            vals = [d[k].get(key) for k in sorted(d)]
            if len(set(vals)) != len(vals):
                why.append(f'{key} shared: {[hex(v or 0) for v in vals]}')
        if any(d[k].get('idt') != idt for k in d):
            why.append(f'IDT bases {[hex(d[k].get("idt") or 0) for k in sorted(d)]}, pax_idt {idt or 0:#x}')
        check = f'cpus: private state checked: {cpus} processors, no record, GDT, TSS or stack shared'
        if check not in boot:
            why.append(f'the kernel\'s own check: no {check!r}')
        if why:
            fail('SMP-PRIVATE', '; '.join(why[:8]))
        else:
            ok('SMP-PRIVATE', f'{cpus} processors: GS, GDT, TSS and stack each their own; one IDT; CR0/3/4, EFER alike')

sys.exit(1 if red else 0)
