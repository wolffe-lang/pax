#!/usr/bin/env python3
"""rows.py's own proof: synthetic transcripts in the probe's and the kernel's shapes, each with
the rows it must pass and the rows it must fail by name: stage 2 green; stage 1 as it is (every row of
the default kind red at the gate, the guards green); and each plant's shape (one break in a green
kernel). No QEMU, no kernel: the parsing and the arithmetic only.

  python3 -I tests/mpx6-smp.d/rows-selftest.py
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
KTEXT = 0xffffffff80005000
SYMS = {'pax_ap_halt': (0xffffffff80001000, 0x10), 'pax_ap_park': (0xffffffff80000ff0, 0x10)}


# --- /proc/pax-cpus ------------------------------------------------------------------------------
def proc(n, active=None, started=None, stage=2, cur=None, user=100, tlb=5, cap=None, unlocked=0):
    """n processors. Stage 2: `runs` lines (cap: those past it on stage 1's idle line); stage 1: idle lines."""
    active = n if active is None else active
    started = n if started is None else started
    head = f'available {n}\nactive {active}\nsource ACPI MADT\nonline-capable 0\ndisabled 0\n'
    idle = 0 if stage == 2 and not cap else (started - 1 if stage == 1 else n - cap)
    body = f'started {started}\nidle {idle}\n'
    if stage == 2:
        body += f'unlocked-allocations {unlocked}\n'
    cur = cur or {}
    for i in range(n):
        c = cur.get(i, 'pid 1' if i == 0 else ('idle' if stage == 1 or (cap and i >= cap) else f'pid {100 + i}'))
        if i >= started:
            body += f'cpu {i} apic {i} parked\n'
        elif stage == 1 or (cap and i >= cap):
            body += (f'cpu {i} apic {i} boot current {c} ticks 300 nmis 0\n' if i == 0 else
                     f'cpu {i} apic {i} idle current idle ticks 300 wakes 301 nmis 0\n')
        else:
            body += (f'cpu {i} apic {i} {"boot" if i == 0 else "runs"} current {c} ticks 300 user {user} resched 4 '
                     f'tlb {tlb}{"" if i == 0 else " wakes 302"} nmis 0\n')
    return head + body


def block(tagname, p):
    return f'SMP-PROC {tagname} begin\n{p}SMP-PROC {tagname} end\n'


def online(n):
    return '0' if n == 1 else f'0-{n - 1}'


def active_line(n, stage=2, cap=None):
    k = cap or n
    if stage == 1:
        return 'SMP-ACTIVE online 0 affinity-ret 8 mask 0x1 setaffinity-ret -38 cpus-allowed 1 cpus-allowed-list 0\n'
    return (f'SMP-ACTIVE online {online(k)} affinity-ret 8 mask {hex((1 << k) - 1)} setaffinity-ret 0 '
            f'cpus-allowed {format((1 << k) - 1, "x")} cpus-allowed-list {online(k)}\n')


def run_lines(n, stage=2, rounds=3, ratio=1.05, cap=None, user=None):
    out = f'SMP-RUN jobs {n} loops 300000000\n'
    for r in range(rounds):
        pids = [200 + 10 * r + i for i in range(n)]
        out += f'SMP-RUN round {r} lone wall-us 1000000 cpu-us 1000000 status 0x0\n'
        runners = cap or n
        for k in range(4):
            cells = []
            for i in range(n):
                if stage == 1:
                    cells.append(f'{i}:{pids[k % n]}' if i == 0 else f'{i}:i')
                elif i >= runners:
                    cells.append(f'{i}:i')
                elif i == k % runners:
                    cells.append(f'{i}:99')  # the sampler, where it ran this time
                else:
                    cells.append(f'{i}:{pids[(i + k) % n]}')
            out += f'SMP-RUN round {r} sample {k} ' + ' '.join(cells) + '\n'
        out += f'SMP-RUN round {r} workers ' + ' '.join(map(str, pids)) + '\n'
        wall = int(1000000 * (n if stage == 1 else ratio * (n / runners)))
        out += f'SMP-RUN round {r} jobs {n} wall-us {wall} cpu-us ' + ','.join(['990000'] * n) + ' bad-status 0\n'
        phase = wall // 10000
        if user is not None:
            gains = user
        elif stage == 1:
            gains = ['-'] * n
        else:
            gains = [f'+{phase - 2}' if i < runners else '-' for i in range(n)]
        out += f'SMP-RUN round {r} phase-ticks {phase} user-ticks ' + ' '.join(f'{i}:{g}' for i, g in enumerate(gains)) + '\n'
    return out + 'SMP-RUN done\n'


def tlb_lines(stage=2, faulted='yes', lat=40, stale=0, tlb='+1'):
    b = '-' if stage == 1 else '1'
    t = '-' if stage == 1 else tlb
    out = ''
    for r in range(5):
        out += (f'SMP-TLB protect {r} faulted {faulted} latency-us {lat if faulted == "yes" else "-"} call-us 30 mprotect 0 '
                f'a-cpu 0 b-cpu {b} tlb {t} reads 1000\n')
    for r in range(5):
        out += f'SMP-TLB replace {r} stale {stale} reads 200000 fixed yes a-cpu 0 b-cpu {b} tlb {t}\n'
    return out + 'SMP-TLB done\n'


def signal_lines(stage=2, usr1=None, kill=None, tgk=None, tid='yes', kill_status='0x9'):
    w = '-' if stage == 1 else '1'
    usr1 = usr1 or [30] * 9
    kill = kill or [50] * 5
    tgk = tgk or [30] * 9
    out = ''.join(f'SMP-SIGNAL usr1 {k} latency-us {v} w-cpu {w} p-cpu 0\n' for k, v in enumerate(usr1))
    out += 'SMP-SIGNAL stop status 0x137f cont status 0xffff held yes resumed yes\n'
    out += ''.join(f'SMP-SIGNAL kill {k} latency-us {v} status {kill_status} w-cpu {w} p-cpu 0\n' for k, v in enumerate(kill))
    out += ''.join(f'SMP-SIGNAL tgkill {k} latency-us {v} tid-ok {tid} t-cpu {w} m-cpu 0\n' for k, v in enumerate(tgk))
    return out + 'SMP-SIGNAL tgkill-status 0x0\nSMP-SIGNAL done\n'


def exit_lines(n, stage=2, statuses=('0x700', '0x700', '0x800', '0x800'), after=200000, stopped='none'):
    run = 1 if stage == 1 else min(4, n)
    out = ''.join(f'SMP-EXIT group {r} exiter {"main" if r < 2 else "sibling"} status {s} running {run} of 4\n'
                  for r, s in enumerate(statuses))
    for r in range(5):
        out += f'SMP-EXIT exec-child pid {40 + r}\n'
        out += f'SMP-EXIT exec {r} {"measured" if r else "warm"} status 0x900 running {run} of 4\n'
    return out + f'SMP-EXIT frames-kb before 200000 after {after}\nSMP-EXIT stopped {stopped}\nSMP-EXIT done\n'


def wait_lines(n, stage=2, right=16, cpus=None):
    cpus = cpus or ('0' if stage == 1 else ','.join(str(i) for i in range(min(n, 16))))
    return f'SMP-WAIT statuses right {right} of 16 cpu-us 2800000 expected-us 2720000 cpus {cpus}\nSMP-WAIT done\n'


def tail():
    return 'SMP-PROBE done\nuser: smpprobe pid 1 exit_group 0 after 9000 runs\nrun: 1 commands\nPAX: init /bin/smpprobe ended with status 0; nothing left to run\nhalt\n'


def head(mode='rows'):
    return f'PAX: the console\nSMP-PROBE start mode {mode} pid 1\nSMP-PROBE tsc-hz 3000000000 loops-per-ms 300000\n'


def rows_text(n, stage=2, **kw):
    p = proc(n, active=1 if stage == 1 else n, stage=stage)
    t = head() + block('start', p) + active_line(n, stage)
    t += kw.get('run', run_lines(n, stage))
    t += kw.get('tlb', tlb_lines(stage))
    t += kw.get('signal', signal_lines(stage))
    t += kw.get('exit', exit_lines(n, stage))
    t += kw.get('wait', wait_lines(n, stage))
    return t + kw.get('extra', '') + block('end', p) + tail()


ALL6 = {'SMP-ACTIVE', 'SMP-RUN', 'SMP-TLB', 'SMP-SIGNAL', 'SMP-EXIT', 'SMP-WAIT'}
cases = []  # (name, text, args, meta, dumps, files, passes, fails)
KVM, TCG = 'accel: kvm\n', 'accel: tcg\n'


def case(name, text, args, passes, fails, meta=KVM, dumps=(), files=None):
    cases.append((name, text, args, meta, list(dumps), files or {}, set(passes), set(fails)))


# --- the default kind ----------------------------------------------------------------------------
for n in (2, 4, 16):
    case(f'stage 2 green at {n}', rows_text(n), ['--kind', 'rows', '--smp', str(n)], ALL6, set())
    case(f'stage 1 at {n}: every row red at the gate', rows_text(n, stage=1), ['--kind', 'rows', '--smp', str(n)],
         set(), ALL6)
case('stage 2 green under TCG', rows_text(4), ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
case('the plant tlb: B reads on past PROT_NONE', rows_text(4, tlb=tlb_lines(faulted='no')),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('a stale read after the new page', rows_text(4, tlb=tlb_lines(stale=1734)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('no shootdown counted', rows_text(4, tlb=tlb_lines(tlb='+0')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('slow faults under KVM', rows_text(4, tlb=tlb_lines(lat=4000)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('slow faults under TCG: printed, not gated', rows_text(4, tlb=tlb_lines(lat=4000)), ['--kind', 'rows', '--smp', '4'],
     ALL6, set(), meta=TCG)
tick = [3000, 7000, 500, 9000, 4000, 6000, 8000, 2500, 1000]
case('the plant resched: signals wait for the tick', rows_text(4, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})
case('the plant resched under TCG: printed, not gated', rows_text(4, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
case('one slow signal of nine is allowed', rows_text(4, signal=signal_lines(usr1=[30] * 8 + [5000])),
     ['--kind', 'rows', '--smp', '4'], ALL6, set())
case('tgkill on the wrong thread', rows_text(4, signal=signal_lines(tid='no')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})
case('a wrong SIGKILL status', rows_text(4, signal=signal_lines(kill_status='0xf')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})
case('N workers at 1.8 times one under KVM', rows_text(4, run=run_lines(4, ratio=1.8)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-RUN'}, {'SMP-RUN'})
case('N workers at 1.8 times one under TCG: printed', rows_text(4, run=run_lines(4, ratio=1.8)),
     ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
case('a processor gains no ring-3 tick', rows_text(4, run=run_lines(4, user=['+100', '+100', '+3', '+100'])),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-RUN'}, {'SMP-RUN'})
case('a wrong exit_group status', rows_text(4, exit=exit_lines(4, statuses=('0x700', '0x700', '0x800', '0x9'))),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'})
case('the exec rounds lose frames', rows_text(4, exit=exit_lines(4, after=199000)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'})
case('a processor stopped', rows_text(4, exit=exit_lines(4, stopped='3')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'})
case('a wrong wait status', rows_text(4, wait=wait_lines(4, right=15)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'})
case('children on one processor', rows_text(4, wait=wait_lines(4, cpus='0')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'})
case('a kernel panic mid-run', rows_text(4, extra='PANIC sched: slot 9 running on two processors 0x0000000000000009\n'),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-RUN', 'SMP-EXIT'}, {'SMP-RUN', 'SMP-EXIT'})
t = rows_text(4)
case('the probe died after SMP-RUN', t[:t.index('SMP-TLB protect 0')] + 'user: smpprobe pid 1 killed: page fault vector 14\nhalt\n',
     ['--kind', 'rows', '--smp', '4'], {'SMP-ACTIVE'}, ALL6 - {'SMP-ACTIVE'})
case('a wrong online list', rows_text(4).replace('online 0-3', 'online 0-2'), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-ACTIVE'}, {'SMP-ACTIVE'})
case('sched_setaffinity refused', rows_text(4).replace('setaffinity-ret 0', 'setaffinity-ret -38'),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-ACTIVE'}, {'SMP-ACTIVE'})
case('status still says one processor', rows_text(4).replace('cpus-allowed f cpus-allowed-list 0-3', 'cpus-allowed 1 cpus-allowed-list 0'),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-ACTIVE'}, {'SMP-ACTIVE'})

# Timed bounds hold only where the boot's processors fit the take's host CPUs: 16 virtual processors on four host
# threads run the 16 workers four at a time whatever the kernel does, and a target's virtual processor may wait for one.
case('16 workers at 4x on 4 host CPUs under KVM: printed, not gated', rows_text(16, run=run_lines(16, ratio=4.0)),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '4'], ALL6, set())
case('16 workers at 4x on 20 host CPUs under KVM: red', rows_text(16, run=run_lines(16, ratio=4.0)),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '20'], ALL6 - {'SMP-RUN'}, {'SMP-RUN'})
case('signals over a tick at 16 on 4 host CPUs: printed, not gated', rows_text(16, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '4'], ALL6, set())
case('signals over a tick at 4 on 4 host CPUs: red', rows_text(4, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '4', '--host-cpus', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})

# --- the stress ----------------------------------------------------------------------------------
def stress_text(stage=2, extra='', lost=0, unlocked=0, done=True, gains=None):
    n = 4
    p = proc(n, active=1 if stage == 1 else n, stage=stage)
    t = head('stress') + block('start', p)
    t += f'SMP-LOCK unlocked-allocations-before {-1 if stage == 1 else 0}\n'
    names = []
    for i in range(4):
        t += f'SMP-LOCK forkwait {i} rounds 5000 wrong 0\n'
        names.append('forkwait')
    for i in range(2):
        t += f'SMP-LOCK pipe {i} rounds 90000 wrong 0\n'
        names.append('pipe')
    for i in range(2):
        t += f'SMP-LOCK futex {i} rounds 80000 thread-rounds 80000 wrong 0\n'
        names.append('futex')
    t += 'SMP-LOCK churn ops 20000 reader-reads 900000 wrong 0\n'
    t += f'SMP-LOCK kill sent 30000 got {30000 - lost} lost {lost}\n'
    names += ['churn', 'kill']
    t += extra
    t += ''.join(f'SMP-LOCK component {nm} pid {10 + i} status {"0x100" if nm == "kill" and lost else "0x0"}\n'
                 for i, nm in enumerate(names))
    g = gains or (['-'] * 4 if stage == 1 else ['+1900'] * 4)
    t += 'SMP-LOCK user-ticks ' + ' '.join(f'{i}:{x}' for i, x in enumerate(g)) + '\n'
    t += f'SMP-LOCK unlocked-allocations-after {-1 if stage == 1 else unlocked}\n'
    t += block('stress', p)
    if done:
        t += 'SMP-LOCK done\n' + tail()
    return t


sa = ['--kind', 'stress', '--smp', '4', '--boot', '3']
case('stress green', stress_text(), sa, {'SMP-LOCK'}, set())
case('stress at stage 1: red at the gate', stress_text(stage=1), sa, set(), {'SMP-LOCK'})
case('the plant lock: a slot on two processors, the boot dies',
     stress_text(extra='PANIC sched: slot 12 running on two processors 0x000000000000000c\n', done=False), sa, set(), {'SMP-LOCK'})
case('a lost signal in the storm', stress_text(lost=1), sa, set(), {'SMP-LOCK'})
# the kernel lock's door (kernel/interrupts): a processor carrying the lock into ring 3 panics by name, and
# SMP-KLOCK carries that line; another panic (the slot on two processors, above) is not the lock's door
KLOCK = 'PANIC klock: entered from ring 3 holding it, cpu  0x0000000000000000\n'
case('the lock plant in a stress boot: red by the door\'s line', stress_text(extra=KLOCK, done=False), sa, set(),
     {'SMP-LOCK', 'SMP-KLOCK'})
case('the lock plant in a rows boot: the probe stops at its first entry', head('rows') + KLOCK,
     ['--kind', 'rows', '--smp', '4'], set(), ALL6 | {'SMP-KLOCK'})
case('the lock plant at one processor', head('one') + KLOCK, ['--kind', 'one', '--smp', '1'], set(),
     {'SMP-ONE', 'SMP-KLOCK'})
case('allocations outside the lock', stress_text(unlocked=3), sa, set(), {'SMP-LOCK'})
case('a processor out of the stress', stress_text(gains=['+1900', '+1900', '+0', '+1900']), sa, set(), {'SMP-LOCK'})
case('a program killed by a fault', stress_text(extra='user: smpprobe pid 17 killed: page fault vector 14 error 0x4 rip 0x401000 after 3 runs\n'),
     sa, set(), {'SMP-LOCK'})
case('a component hung past the deadline, ended by the probe',
     stress_text(extra='SMP-LOCK component futex pid 16 hung 30 s past the deadline: SIGKILL\n'), sa, set(), {'SMP-LOCK'})
case('SIGKILL and SIGTERM deaths are expected', stress_text(extra='user: smpprobe pid 17 killed: SIGKILL after 3 runs\n'),
     sa, {'SMP-LOCK'}, set())


# --- the ends ------------------------------------------------------------------------------------
def regs(k, rip, hlt=1, rfl=0x2):
    return f'CPU#{k}\nRAX=0000000000000000\nRIP={rip:016x} RFL={rfl:08x} [-------] CPL=0 II=0 A20=1 SMM=0 HLT={hlt}\n'


def end_text(how, stage=2, order='right'):
    n = 4
    p = proc(n, active=1 if stage == 1 else n, stage=stage)
    t = head('end') + block('start', p)
    t += f'SMP-END spinners 4 on cpus {"0" if stage == 1 else "0,1,2,3"}\nSMP-END asking reboot(2) {how}\n'
    stop = 'cpus: 3 application processors stopped for the end\n' if stage == 2 else ''
    the_end = 'PAX: the end: SIGTERM to 5 processes, 5 ended within 0 ms\n'
    line = f'user: smpprobe pid 1 reboot(2): the volumes written and marked clean; {"restarting" if how == "restart" else "halting"}\n'
    t += (stop + the_end if order == 'early' else the_end + stop) + line
    return t + ('halt\n' if how == 'halt' else '')


halted = regs(0, KTEXT, rfl=0x2) + ''.join(regs(k, KTEXT + 0x40, rfl=0x2) for k in range(1, 4))
idle_dump = regs(0, KTEXT, rfl=0x2) + ''.join(regs(k, SYMS['pax_ap_halt'][0] + 3, rfl=0x246) for k in range(1, 4))
case('end halt green', end_text('halt'), ['--kind', 'end-halt', '--smp', '4'], {'SMP-END'}, set(), dumps=[halted] * 3)
case('end halt at stage 1: no stop line, APs idle with IF set', end_text('halt', stage=1), ['--kind', 'end-halt', '--smp', '4'],
     set(), {'SMP-END'}, dumps=[idle_dump] * 3)
case('the plant end: the line gone, APs idle', end_text('halt').replace('cpus: 3 application processors stopped for the end\n', ''),
     ['--kind', 'end-halt', '--smp', '4'], set(), {'SMP-END'}, dumps=[idle_dump] * 3)
case('the stop line before the processes end', end_text('halt', order='early'), ['--kind', 'end-halt', '--smp', '4'],
     set(), {'SMP-END'}, dumps=[halted] * 3)
case('end power-off green', end_text('poweroff'), ['--kind', 'end-poweroff', '--smp', '4', '--qemu-status', '0'], {'SMP-END'}, set())
case('end power-off hung', end_text('poweroff'), ['--kind', 'end-poweroff', '--smp', '4', '--qemu-status', '124'], set(), {'SMP-END'})
case('end restart green', end_text('restart'), ['--kind', 'end-reboot', '--smp', '4', '--qemu-status', '0'], {'SMP-END'}, set())


# --- one processor, the cap ----------------------------------------------------------------------
def one_text(n, cmdline_parked=False, stage=1, boot_line=None, mode='one'):
    p = proc(n, active=1, started=1 if cmdline_parked or n == 1 else n, stage=1)
    t = 'PAX: the console\n' + (boot_line + '\n' if boot_line else '') + head(mode)[len('PAX: the console\n'):]
    return t + block('start', p) + active_line(1, 1) + block('end', p) + tail()


parked = regs(0, KTEXT) + ''.join(regs(k, 0xffff80000009f000) for k in range(1, 4))
nosmp_line = 'cpus: application processors left parked 3 of 3 (nosmp)'
case('nosmp green (stage 1)', one_text(4, True, boot_line=nosmp_line), ['--kind', 'nosmp', '--smp', '4'],
     {'SMP-NOSMP'}, set(), dumps=[parked] * 3)
case('nosmp with processors in the kernel', one_text(4, True, boot_line=nosmp_line), ['--kind', 'nosmp', '--smp', '4'],
     set(), {'SMP-NOSMP'}, dumps=[idle_dump] * 3)
held = regs(0, KTEXT) + ''.join(regs(k, SYMS['pax_ap_park'][0] + 3, rfl=0x2) for k in range(1, 4))
case('nosmp under TCG: halted in the park', one_text(4, True, boot_line=nosmp_line), ['--kind', 'nosmp', '--smp', '4'],
     {'SMP-NOSMP'}, set(), meta=TCG, dumps=[held] * 3)
case('nosmp under KVM: halted in the park is in the kernel', one_text(4, True, boot_line=nosmp_line),
     ['--kind', 'nosmp', '--smp', '4'], set(), {'SMP-NOSMP'}, dumps=[held] * 3)
case('one green (stage 1)', one_text(1), ['--kind', 'one', '--smp', '1'], {'SMP-ONE'}, set())
case('one with a cpus: line', one_text(1, boot_line='cpus: application processors idle 0 of 0'),
     ['--kind', 'one', '--smp', '1'], set(), {'SMP-ONE'})
case('cap1 green (stage 1 ignores the word)', one_text(4), ['--kind', 'cap1', '--smp', '4', '--cap', '1'], {'SMP-CAP'}, set())


def cap2_text(stage=2):
    p = proc(4, active=1 if stage == 1 else 2, stage=stage, cap=None if stage == 1 else 2)
    t = head('cap') + block('start', p) + active_line(4, stage, cap=2)
    t += run_lines(4, stage, rounds=1, cap=None if stage == 1 else 2)
    return t + block('end', p) + tail()


case('cap2 green', cap2_text(), ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, set())
case('cap2 at stage 1: red', cap2_text(stage=1), ['--kind', 'cap2', '--smp', '4', '--cap', '2'], set(), {'SMP-CAP'})
t = re.sub(r'^(SMP-RUN round 0 sample 1 .*) 3:i$', r'\1 3:201', cap2_text(), flags=re.M)
case('cap2 with a worker past the cap', t, ['--kind', 'cap2', '--smp', '4', '--cap', '2'], set(), {'SMP-CAP'})


# --- SMP-BUILD -------------------------------------------------------------------------------------
EXPECTED = {'pack-8ae042682afb5156b4b5a80bc241260795144d29.pack': '8ae042682afb5156b4b5a80bc241260795144d29',
            'pack-8ae042682afb5156b4b5a80bc241260795144d29.idx': 'c219e2f6ef55933c2050bc2356210dff1d746e4b'}


def build_text(active, wrong=False):
    t = f'BENCH TSC-HZ 3000000000\nBENCH ACTIVE {active}\n'
    for r in range(3):
        for j in (1, 4):
            t += f'BENCH BEGIN round={r} jobs={j}\nBENCH END round={r} jobs={j} user_us=1 sys_us=1 maxrss_kib=44136 guest_wall_us=203000\n'
            for k in range(j):
                for name, d in EXPECTED.items():
                    t += f'OUTPUT /bench/r{r}-j{j}-{k} {name} trailer-sha1={"0" * 40 if wrong and r == 2 else d}\n'
    return t + f'BENCH ACTIVE {active}\nBENCH DONE\nhalt\n'


def times(one, four):
    return json.dumps([[r, 1, one + r * 0.01] for r in range(3)] + [[r, 4, four + r * 0.01] for r in range(3)])


ba = ['--kind', 'build', '--smp', '4', '--expected', 'expected.json']
case('build at 4, gated, 1.3x under KVM', build_text(4), ba + ['--scaling', 'gate'], {'SMP-BUILD'}, set(),
     files={'times': times(0.203, 0.264)})
case('build at 4, gated, 1.9x under KVM', build_text(4), ba + ['--scaling', 'gate'], set(), {'SMP-BUILD'},
     files={'times': times(0.203, 0.386)})
case('build at 4, reported, 1.9x', build_text(4), ba + ['--scaling', 'report'], {'SMP-BUILD'}, set(),
     files={'times': times(0.203, 0.386)})
case('build at 4, gated under TCG', build_text(4), ba + ['--scaling', 'gate'], set(), {'SMP-BUILD'}, meta=TCG,
     files={'times': times(0.203, 0.264)})
case('build at stage 1: one processor runs the jobs', build_text(1), ba + ['--scaling', 'report'], set(), {'SMP-BUILD'},
     files={'times': times(0.203, 0.876)})
case('build at 4, gated, on 2 host CPUs', build_text(4), ba + ['--scaling', 'gate', '--host-cpus', '2'], set(), {'SMP-BUILD'},
     files={'times': times(0.203, 0.264)})
case('build at 1: the figures alone', build_text(1), ['--kind', 'build', '--smp', '1', '--expected', 'expected.json'],
     {'SMP-BUILD'}, set(), files={'times': times(0.203, 0.876)})
case('build with an output not the oracle\'s', build_text(4, wrong=True), ba + ['--scaling', 'report'], set(), {'SMP-BUILD'},
     files={'times': times(0.203, 0.264)})

bad = 0
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    (td / 'nm.txt').write_text(''.join(f'{v[0]:016x} {v[1]:016x} T {k}\n' for k, v in SYMS.items()))
    (td / 'expected.json').write_text(json.dumps(EXPECTED))
    for name, text, args, meta, dumps, files, passes, fails in cases:
        s = td / 'serial.log'
        s.write_text(text)
        for suffix in ('.cmd2', '.cmd5', '.cmd8', '.meta', '.times'):
            (td / f'serial.log{suffix}').unlink(missing_ok=True)
        for k, d in zip((2, 5, 8), dumps):
            (td / f'serial.log.cmd{k}').write_text(d)
        if meta:
            (td / 'serial.log.meta').write_text(meta)
        if 'times' in files:
            (td / 'serial.log.times').write_text(files['times'])
        argv = [x if x != 'expected.json' else str(td / 'expected.json') for x in args]
        r = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'rows.py'), str(s), *argv, '--symbols', str(td / 'nm.txt')],
                           capture_output=True, text=True)
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
print(f'rows-selftest: {len(cases) - bad} of {len(cases)} cases as expected')
sys.exit(1 if bad else 0)
