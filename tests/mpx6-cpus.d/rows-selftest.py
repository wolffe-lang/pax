#!/usr/bin/env python3
"""rows.py's own proof (px161): synthetic transcripts and register dumps, each with the rows it must pass
and the rows it must fail by name. No QEMU, no kernel: the arithmetic and the parsing only.

  python3 -I tests/mpx6-cpus.d/rows-selftest.py
"""
import pathlib
import re
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
CPUS_VA, SPAN = 0xffffd08000000000, 0x40000
SYMS = {'pax_ap_halt': (0xffffffff80001000, 0x10), 'pax_ap_park': (0xffffffff80000ff0, 0x10),
        'pax_cpu0': (0xffffffff80200000, 0x200),
        'pax_gdt': (0xffffffff80201000, 0x40), 'pax_tss': (0xffffffff80201040, 0x70),
        'pax_idt': (0xffffffff80202000, 0x1000)}


def regs(k, *, rip, rsp, gs, gdt, tr, hlt=1, idt=SYMS['pax_idt'][0], cr0=0x80010033, cr3=0x1000,
         cr4=0x3006a0, efer=0xd01, rfl=0x246):
    return (f'CPU#{k}\nRAX=0000000000000000 RBX=0000000000000000\nRSI=0 RDI=0 RBP=0 RSP={rsp:016x}\n'
            f'RIP={rip:016x} RFL={rfl:08x} [---Z-P-] CPL=0 II=0 A20=1 SMM=0 HLT={hlt}\n'
            f'GS =0010 {gs:016x} 000fffff 00af9300 DPL=0 DS   [-WA]\n'
            f'TR =0028 {tr:016x} 0000006f 00008b00 DPL=0 TSS64-busy\n'
            f'GDT=     {gdt:016x} 00000037\nIDT=     {idt:016x} 00000fff\n'
            f'CR0={cr0:08x} CR2=0000000000000000 CR3={cr3:016x} CR4={cr4:08x}\nEFER={efer:016x}\n')


def ap_regs(k, i=None, **kw):
    i = k if i is None else i
    rec = CPUS_VA + i * SPAN
    base = dict(rip=SYMS['pax_ap_halt'][0] + 3, rsp=rec + 0xbf00, gs=rec, gdt=rec + 256, tr=rec + 384)
    base.update(kw)
    return regs(k, **base)


def bsp_regs(**kw):
    base = dict(rip=0xffffffff80005000, rsp=0xffffd0000000ff00, gs=SYMS['pax_cpu0'][0],
                gdt=SYMS['pax_gdt'][0], tr=SYMS['pax_tss'][0])
    base.update(kw)
    return regs(0, **base)


def proc(n, cpus, aps_state='idle', ticks=100, nmis=0, pid=1, started=None, idle=None, disabled=0):
    head = f'available {n}\nactive 1\n'
    head += 'source unavailable\n' if n == 'unknown' else f'source ACPI MADT\nonline-capable 0\ndisabled {disabled}\n'
    started = cpus if started is None else started
    idle = (cpus - 1 if aps_state == 'idle' else 0) if idle is None else idle
    body = f'started {started}\nidle {idle}\ncpu 0 apic 0 boot current pid {pid} ticks {ticks} nmis 0\n'
    for i in range(1, cpus):
        if aps_state == 'idle':
            body += f'cpu {i} apic {i} idle current idle ticks {ticks} wakes {ticks + 1} nmis {nmis}\n'
        else:
            body += f'cpu {i} apic {i} {aps_state}\n'
    return head + body


def transcript(n, cpus, boot_lines, p1, p2, gs='CPU-USER-GS ok 3 reads', pid=1):
    src = 'unavailable' if n == 'unknown' else 'ACPI MADT'
    t = f'PAX: the console\nprocessors: available {n}, active 1; source {src}\n'
    t += ''.join(b + '\n' for b in boot_lines)
    t += f'{gs}\nCPU-PID {pid}\nCPU-PROC begin\n{p1}CPU-PROC end\nCPU-PROC2 begin\n{p2}CPU-PROC2 end\nhalt\n'
    return t


def idle_line(aps):
    return (f'cpus: application processors idle {aps} of {aps} in 2 ms, 84 KiB each ({aps * 84 + 12} KiB with their '
            'tables); the boot processor runs every thread')


def private_line(cpus):
    return f'cpus: private state checked: {cpus} processors, no record, GDT, TSS or stack shared'


def green(cpus):
    lines = [idle_line(cpus - 1), private_line(cpus)]
    d = bsp_regs() + ''.join(ap_regs(k) for k in range(1, cpus))
    return dict(n=str(cpus), text=transcript(cpus, cpus, lines, proc(cpus, cpus), proc(cpus, cpus, ticks=130)),
                dumps=[d, d, d])


cases = []
for cpus in (2, 4, 16):
    g = green(cpus)
    cases.append((f'green {cpus}', g, [], {'CPU-CENSUS', 'SMP-ENTER', 'SMP-USER-GS', 'SMP-SCHED', 'SMP-TICKS',
                                         'SMP-IDLE', 'SMP-PRIVATE'}, set()))

# Trunk: no application processor enters; the dump shows them in wait-for-SIPI, GS 0.
trunk_proc = 'available 4\nactive 1\nsource ACPI MADT\nonline-capable 0\ndisabled 0\n'
trunk_dump = regs(0, rip=0xffffffff80005000, rsp=0xffffd0000000ff00, gs=0, gdt=SYMS['pax_gdt'][0], tr=SYMS['pax_tss'][0]) + \
    ''.join(regs(k, rip=0xfff0, rsp=0, gs=0, gdt=0, tr=0, cr0=0x60000010, cr3=0, cr4=0, efer=0) for k in range(1, 4))
cases.append(('trunk 4', dict(n='4', text=transcript(4, 4, [], trunk_proc, trunk_proc), dumps=[trunk_dump] * 3), [],
              {'CPU-CENSUS', 'SMP-USER-GS', 'SMP-SCHED'}, {'SMP-ENTER', 'SMP-TICKS', 'SMP-IDLE', 'SMP-PRIVATE'}))
cases.append(('trunk 1', dict(n='1', text=transcript(1, 1, [], trunk_proc.replace('4', '1'), trunk_proc.replace('4', '1')),
                              dumps=[]), [], {'CPU-CENSUS', 'SMP-USER-GS', 'SMP-SCHED'}, {'SMP-ONE', 'SMP-TICKS'}))
one = proc(1, 1)
cases.append(('one', dict(n='1', text=transcript(1, 1, [], one, one), dumps=[]), [],
              {'CPU-CENSUS', 'SMP-ONE', 'SMP-USER-GS', 'SMP-SCHED', 'SMP-TICKS'}, set()))
unk = proc('unknown', 1)
cases.append(('no acpi', dict(n='unknown', text=transcript('unknown', 1, [], unk, unk), dumps=[]), [],
              {'CPU-CENSUS', 'SMP-ONE', 'SMP-USER-GS', 'SMP-SCHED', 'SMP-TICKS'}, set()))

# The plant: every application processor's GS base the boot processor's record.
g = green(4)
shared = bsp_regs() + ''.join(ap_regs(k, gs=SYMS['pax_cpu0'][0]) for k in range(1, 4))
g['dumps'] = [shared] * 3
cases.append(('plant shared GS', g, [], {'SMP-ENTER', 'SMP-IDLE'}, {'SMP-PRIVATE'}))

# One dump catches an application processor in its tick handler: the others save the row.
g = green(4)
busy = bsp_regs() + ap_regs(1, rip=0xffffffff80009000, hlt=0) + ap_regs(2) + ap_regs(3)
g['dumps'] = [busy, g['dumps'][0], g['dumps'][0]]
cases.append(('busy in one dump', g, [], {'SMP-IDLE', 'SMP-PRIVATE'}, set()))
g = green(4)
g['dumps'] = [busy] * 3
cases.append(('busy in every dump', g, [], set(), {'SMP-IDLE'}))

# An AP whose CR4 differs, or that shares the IDT wrongly, or whose stack is another's.
g = green(4)
g['dumps'] = [bsp_regs() + ap_regs(1, cr4=0x6a0) + ap_regs(2) + ap_regs(3)] * 3
cases.append(('cr4 differs', g, [], {'SMP-IDLE'}, {'SMP-PRIVATE'}))
g = green(4)
g['dumps'] = [bsp_regs() + ap_regs(1) + ap_regs(2, rsp=CPUS_VA + SPAN + 0xbf00) + ap_regs(3)] * 3
cases.append(('stack shared', g, [], {'SMP-IDLE'}, {'SMP-PRIVATE'}))
g = green(4)
g['text'] = g['text'].replace(private_line(4) + '\n', '')
cases.append(('no kernel check', g, [], {'SMP-ENTER'}, {'SMP-PRIVATE'}))

# The scheduler check: an application processor stopped by name.
g = green(4)
g['text'] = g['text'].replace(private_line(4), private_line(4) + '\ncpus: cpu 2 stopped: entered the scheduler')
g['text'] = g['text'].replace('cpu 2 apic 2 idle current idle ticks 130 wakes 131 nmis 0', 'cpu 2 apic 2 stopped entered the scheduler')
cases.append(('ap in the scheduler', g, [], {'SMP-ENTER'}, {'SMP-SCHED', 'SMP-TICKS'}))

# Ticks that do not advance; the boot processor's current not the probe.
g = green(4)
g['text'] = re.sub(r'CPU-PROC2 begin\n.*?CPU-PROC2 end', lambda m: 'CPU-PROC2 begin\n' + proc(4, 4, ticks=104) + 'CPU-PROC2 end',
                   g['text'], flags=re.S)
cases.append(('stalled ticks', g, [], {'SMP-ENTER'}, {'SMP-TICKS'}))
g = green(4)
g['text'] = g['text'].replace('CPU-PID 1', 'CPU-PID 9')
cases.append(('wrong current', g, [], {'SMP-ENTER'}, {'SMP-TICKS'}))

# Ring 3's GS: the probe died before its line.
g = green(4)
g['text'] = g['text'].replace('CPU-USER-GS ok 3 reads\n', '')
cases.append(('user gs', g, [], {'SMP-ENTER'}, {'SMP-USER-GS'}))

# The probe dies before its lines: the census is red, and so is every row that needs the probe; the
# register dumps' rows still say what they see.
g = green(4)
g['text'] = re.sub(r'CPU-USER-GS.*?CPU-PROC2 end\n', 'user: cpuprobe pid 1 killed: general protection vector 13\n',
                   g['text'], flags=re.S)
cases.append(('probe died', g, [], {'SMP-IDLE', 'SMP-SCHED'},
              {'CPU-CENSUS', 'SMP-ENTER', 'SMP-USER-GS', 'SMP-TICKS', 'SMP-PRIVATE'}))

# nosmp: the application processors stay in the bootloader.
park = proc(4, 4, aps_state='parked', started=1, idle=0)
parked_dump = bsp_regs() + ''.join(regs(k, rip=0xffff80000009f000, rsp=0, gs=0, gdt=0, tr=0) for k in range(1, 4))
nos = dict(n='4', text=transcript(4, 4, ['cpus: application processors left parked 3 of 3 (nosmp)'], park, park),
           dumps=[parked_dump] * 3)
cases.append(('nosmp', nos, ['--mode', 'nosmp'], {'CPU-CENSUS', 'SMP-NOSMP', 'CPU-PARKED', 'SMP-USER-GS'}, set()))
nos2 = dict(nos)
nos2['dumps'] = [green(4)['dumps'][0]] * 3
cases.append(('nosmp but released', nos2, ['--mode', 'nosmp'], {'SMP-NOSMP'}, {'CPU-PARKED'}))

# nosmp under QEMU's TCG, which acts on a halted processor's INIT only when something next wakes it: the
# processors still sit where the kernel halted them for good (pax_ap_park, HLT=1, interrupts off). Held
# there under TCG alone; with interrupts on, not halted, or under KVM (which acts on INIT at once), red.
def held(meta, **kw):
    base = dict(rip=SYMS['pax_ap_park'][0] + 3, rsp=0xffff80000f54fff8, gs=0, gdt=0, tr=0, rfl=0x2)
    base.update(kw)
    c = dict(nos)
    c['dumps'] = [bsp_regs() + ''.join(regs(k, **base) for k in range(1, 4))] * 3
    c['meta'] = meta
    return c


cases.append(('nosmp, halted in the park under TCG', held('accel: tcg\n'), ['--mode', 'nosmp'],
              {'SMP-NOSMP', 'CPU-PARKED'}, set()))
cases.append(('nosmp, halted in the park under KVM', held('accel: kvm\n'), ['--mode', 'nosmp'],
              {'SMP-NOSMP'}, {'CPU-PARKED'}))
cases.append(('nosmp, halted in the park, no accelerator said', held(None), ['--mode', 'nosmp'],
              {'SMP-NOSMP'}, {'CPU-PARKED'}))
cases.append(('nosmp, in the park with interrupts on under TCG', held('accel: tcg\n', rfl=0x202), ['--mode', 'nosmp'],
              {'SMP-NOSMP'}, {'CPU-PARKED'}))
cases.append(('nosmp, in the park but running under TCG', held('accel: tcg\n', hlt=0), ['--mode', 'nosmp'],
              {'SMP-NOSMP'}, {'CPU-PARKED'}))
cases.append(('nosmp, idle in the kernel under TCG', held('accel: tcg\n', rip=SYMS['pax_ap_halt'][0] + 3),
              ['--mode', 'nosmp'], {'SMP-NOSMP'}, {'CPU-PARKED'}))

# pax.cpunmi: one NMI each, ticking after it.
nmi_lines = [idle_line(3), private_line(4), 'cpus: application processors took an NMI each 3 of 3, each on its own stack']
d = green(4)['dumps'][0]
nm = dict(n='4', text=transcript(4, 4, nmi_lines, proc(4, 4, nmis=1), proc(4, 4, ticks=130, nmis=1)), dumps=[d] * 3)
cases.append(('nmi', nm, ['--mode', 'nmi'], {'SMP-NMI', 'SMP-ENTER', 'SMP-PRIVATE'}, set()))
nm2 = dict(nm)
nm2['text'] = nm['text'].replace('nmis 1', 'nmis 0', 1).replace('cpu 1 apic 1 idle current idle ticks 100 wakes 101 nmis 1',
                                                                'cpu 1 apic 1 idle current idle ticks 100 wakes 101 nmis 2')
cases.append(('nmi counted twice', nm2, ['--mode', 'nmi'], {'SMP-ENTER'}, {'SMP-NMI'}))

bad = 0
with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t)
    (t / 'nm.txt').write_text(''.join(f'{v[0]:016x} {v[1]:016x} T {k}\n' for k, v in SYMS.items()))
    for name, c, extra, passes, fails in cases:
        s = t / 'serial.log'
        s.write_text(c['text'])
        for k in (2, 5, 8):
            (t / f'serial.log.cmd{k}').unlink(missing_ok=True)
        for k, dump in zip((2, 5, 8), c['dumps']):
            (t / f'serial.log.cmd{k}').write_text(dump)
        (t / 'serial.log.meta').unlink(missing_ok=True)
        if c.get('meta'):
            (t / 'serial.log.meta').write_text(c['meta'])
        r = subprocess.run([sys.executable, '-I', str(HERE / 'rows.py'), str(s), c['n'], *extra,
                            '--symbols', str(t / 'nm.txt')], capture_output=True, text=True)
        got_pass = set(re.findall(r'^PASS (\S+)', r.stdout, re.M))
        got_fail = set(re.findall(r'^FAIL (\S+)', r.stdout, re.M))
        wrong = (passes - got_pass) | (fails - got_fail) | (got_fail - fails) | (passes & got_fail)
        code_ok = (r.returncode != 0) == bool(fails)
        if wrong or not code_ok or r.stderr:
            bad += 1
            print(f'FAIL ROWS-SELFTEST {name}: want pass {sorted(passes)} fail {sorted(fails)}; '
                  f'got pass {sorted(got_pass)} fail {sorted(got_fail)} exit {r.returncode}')
            print(r.stdout + r.stderr)
        else:
            print(f'PASS ROWS-SELFTEST {name}: fails {sorted(got_fail) or "none"}')
sys.exit(1 if bad else 0)
