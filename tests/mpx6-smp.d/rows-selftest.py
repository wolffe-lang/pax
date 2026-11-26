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
def proc(n, active=None, started=None, stage=2, cur=None, user=100, tlb=5, cap=None, kthreads=None, heap=0):
    """n processors. Stage 2: `runs` lines (cap: those past it on stage 1's idle line), `kthreads` 0 unless
    the dict says otherwise for a processor; stage 1: idle lines."""
    active = n if active is None else active
    started = n if started is None else started
    head = f'available {n}\nactive {active}\nsource ACPI MADT\nonline-capable 0\ndisabled 0\n'
    idle = 0 if stage == 2 and not cap else (started - 1 if stage == 1 else n - cap)
    body = f'started {started}\nidle {idle}\n'
    if heap is not None:  # the kernel's word: whether its heap was started (0: the runtime can allocate nothing)
        body += f'heap-started {heap}\n'
    cur = cur or {}
    for i in range(n):
        c = cur.get(i, 'pid 1' if i == 0 else ('idle' if stage == 1 or (cap and i >= cap) else f'pid {100 + i}'))
        if i >= started:
            body += f'cpu {i} apic {i} parked\n'
        elif stage == 1 or (cap and i >= cap):
            body += (f'cpu {i} apic {i} boot current {c} ticks 300 nmis 0\n' if i == 0 else
                     f'cpu {i} apic {i} idle current idle ticks 300 wakes 301 nmis 0\n')
        else:
            k = (kthreads or {}).get(i, 0)
            body += (f'cpu {i} apic {i} {"boot" if i == 0 else "runs"} current {c} ticks 300 user {user} resched 4 '
                     f'kthreads {k} tlb {tlb}{"" if i == 0 else " wakes 302"} nmis 0\n')
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


def run_lines(n, stage=2, rounds=3, ratio=1.05, cap=None, user=None, seen=None, wcpu=990000):
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
                elif i >= runners or (seen is not None and i not in seen):
                    cells.append(f'{i}:i')
                elif i == k % runners:
                    cells.append(f'{i}:99')  # the sampler, where it ran this time
                else:
                    cells.append(f'{i}:{pids[(i + k) % n]}')
            out += f'SMP-RUN round {r} sample {k} ' + ' '.join(cells) + '\n'
        out += f'SMP-RUN round {r} workers ' + ' '.join(map(str, pids)) + '\n'
        wall = int(1000000 * (n if stage == 1 else ratio * (n / runners)))
        out += f'SMP-RUN round {r} jobs {n} wall-us {wall} cpu-us ' + ','.join([str(wcpu)] * n) + ' bad-status 0\n'
        phase = wall // 10000
        if user is not None:
            gains = user
        elif stage == 1:
            gains = ['-'] * n
        else:
            gains = [f'+{phase - 2}' if i < runners else '-' for i in range(n)]
        out += f'SMP-RUN round {r} phase-ticks {phase} user-ticks ' + ' '.join(f'{i}:{g}' for i, g in enumerate(gains)) + '\n'
    return out + 'SMP-RUN done\n'


def tlb_lines(stage=2, faulted='yes', lat=40, stale=0, tlb='+1', bfault='no'):
    b = '-' if stage == 1 else '1'
    t = '-' if stage == 1 else tlb
    out = ''
    for r in range(5):
        out += (f'SMP-TLB protect {r} faulted {faulted} latency-us {lat if faulted == "yes" else "-"} call-us 30 mprotect 0 '
                f'a-cpu 0 b-cpu {b} tlb {t} reads 1000\n')
    for r in range(5):
        if bfault == 'yes':  # tlb1b's own lines (B dead in h_segv: no count, no reads), with the fault named
            out += f'SMP-TLB replace {r} stale - reads 0 fixed yes b-fault yes a-cpu 0 b-cpu {b} tlb {t}\n'
        else:
            out += f'SMP-TLB replace {r} stale {stale} reads 200000 fixed yes b-fault no a-cpu 0 b-cpu {b} tlb {t}\n'
    return out + 'SMP-TLB done\n'


def signal_lines(stage=2, usr1=None, kill=None, tgk=None, tid='yes', kill_status='0x9', resched='0:1 1:23 2:0 3:0',
                 held='yes', sleeper=None, ten=None, sleeper_status='0x0'):
    w = '-' if stage == 1 else '1'
    usr1 = usr1 or [30] * 9
    kill = kill or [50] * 5
    tgk = tgk or [30] * 9
    out = ''.join(f'SMP-SIGNAL usr1 {k} latency-us {v} w-cpu {w} p-cpu 0\n' for k, v in enumerate(usr1))
    out += f'SMP-SIGNAL stop status 0x137f cont status 0xffff held {held} resumed yes\n'
    out += ''.join(f'SMP-SIGNAL kill {k} latency-us {v} status {kill_status} w-cpu {w} p-cpu 0\n' for k, v in enumerate(kill))
    out += ''.join(f'SMP-SIGNAL tgkill {k} latency-us {v} tid-ok {tid} t-cpu {w} m-cpu 0\n' for k, v in enumerate(tgk))
    out += 'SMP-SIGNAL tgkill-status 0x0\n'
    # the sleeper: a SIGUSR1 to a process whose main thread blocks it, its second thread asleep (`-` the sleeper's cpu)
    if sleeper != 'none':
        out += ''.join(f'SMP-SIGNAL sleeper {k} latency-us {v} s-cpu - p-cpu 0\n' for k, v in enumerate(sleeper or [40] * 30))
        for r, t in enumerate(ten or [10] * 20):
            # a round: taken, the worst send-to-handler time, and the kernel's counts across it (set, merged, took,
            # sleeps entered with one pending); a round of ten taken is ten set, none merged
            n, worst, merged, slept = (t, 40, 0, 0) if isinstance(t, int) else t
            out += (f'SMP-SIGNAL sleeper-ten round {r} taken {n} worst-us {worst} set {10 - merged} merged {merged} '
                    f'took {n} slept-pending {slept}\n')
        out += f'SMP-SIGNAL sleeper-status {sleeper_status}\n'
    out += f'SMP-SIGNAL resched {resched}\n' if resched is not None else ''
    return out + 'SMP-SIGNAL done\n'


def exit_lines(n, stage=2, statuses=('0x700', '0x700', '0x800', '0x800'), after=200000, stopped='none', back=None,
               left=None, settled=True):
    # each exec round: the group's VmRSS before its exec (`rss-kb`), MemFree when its wait4 returned (`waited-kb`) and
    # once its threads were off every processor and a reap had run (`settled-kb`), the settling's wait (`settle-ms`)
    # and the round's threads still current when it ended (`left`); back: the kB each round's settle gave back, five
    # values; left: five values; settled False prints the rounds without them (a probe from before the settled reading)
    run = 1 if stage == 1 else min(4, n)
    back, left = back or (0,) * 5, left or (0,) * 5
    out = ''.join(f'SMP-EXIT group {r} exiter {"main" if r < 2 else "sibling"} status {s} running {run} of 4\n'
                  for r, s in enumerate(statuses))
    for r in range(5):
        out += f'SMP-EXIT exec-child pid {40 + r}\n'
        out += f'SMP-EXIT exec {r} {"measured" if r else "warm"} status 0x900 running {run} of 4'
        kb = after if r == 4 else 200000
        if settled:
            out += (f' rss-kb 1316 waited-kb {kb - back[r]} settled-kb {kb} settle-ms {2000 if left[r] else 3}'
                    f' left {left[r]}')
        out += '\n'
    return out + f'SMP-EXIT frames-kb before 200000 after {after}\nSMP-EXIT stopped {stopped}\nSMP-EXIT done\n'


def wait_lines(n, stage=2, right=16, cpus=None, ticks='seen', resched=None, sampler=None, cpu=2800000):
    # ticks: each processor's ring-3 ticks gained while the children ran (the kernel's counters): 'seen' gives +30 to
    # each processor the sampler saw and +0 to the rest; a list gives them one by one; None prints no line (a probe
    # from before the counters)
    cpus = cpus or ('0' if stage == 1 else ','.join(str(i) for i in range(min(n, 16))))
    out = f'SMP-WAIT statuses right {right} of 16 cpu-us {cpu} expected-us 2720000 cpus {cpus}\n'
    if ticks == 'seen':
        seen = {int(x) for x in cpus.split(',')}
        ticks = ['+30' if i in seen else '+0' for i in range(n)]
    if ticks is not None:
        out += 'SMP-WAIT user-ticks' + ''.join(f' {i}:{d}' for i, d in enumerate(ticks)) + '\n'
    # resched: each processor's RESCHEDs taken while the children ran (a list); sampler: (samples, the processors it
    # sat on, each processor's idle samples): printed as INFO, never judged
    if resched is not None:
        out += 'SMP-WAIT resched' + ''.join(f' {i}:{d}' for i, d in enumerate(resched)) + '\n'
    if sampler is not None:
        k, on, idle = sampler
        out += f'SMP-WAIT samples {k} sampler-on {",".join(str(i) for i in on) or "-"} idle' + ''.join(f' {i}:{c}' for i, c in enumerate(idle)) + '\n'
    return out + 'SMP-WAIT done\n'


def tail():
    return 'SMP-PROBE done\nuser: smpprobe pid 1 exit_group 0 after 9000 runs\nrun: 1 commands\nPAX: init /bin/smpprobe ended with status 0; nothing left to run\nhalt\n'


def head(mode='rows'):
    return f'PAX: the console\nSMP-PROBE start mode {mode} pid 1\nSMP-PROBE tsc-hz 3000000000 loops-per-ms 300000\n'


def rows_text(n, stage=2, **kw):
    p = proc(n, active=1 if stage == 1 else n, stage=stage, kthreads=kw.get('kthreads'), heap=kw.get('heap', 0))
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


def case(name, text, args, passes, fails, meta=KVM, dumps=(), files=None, why=None, says=None):
    # why: a regular expression some `FAIL ROW …` line must match (the red for the reason named, not only the row);
    # says: one some line of the row's output must match (what a green row prints, such as the processors it missed)
    cases.append((name, text, args, meta, list(dumps), files or {}, set(passes), set(fails), why, says))


# --- the default kind ----------------------------------------------------------------------------
for n in (2, 4, 16):
    case(f'stage 2 green at {n}', rows_text(n), ['--kind', 'rows', '--smp', str(n)], ALL6, set())
    case(f'stage 1 at {n}: every row red at the gate', rows_text(n, stage=1), ['--kind', 'rows', '--smp', str(n)],
         set(), ALL6)
case('stage 2 green under TCG', rows_text(4), ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
# the CPU shares (each worker 0.8 of the lone, the children 0.8 of their work): the work is a loop count calibrated at
# boot, so its CPU time is the processor's speed at the time; under TCG the guest's TSC follows the host's clock, and on
# a shared host that speed moves within a boot (the hosted job at one head: the lone read 361, 889 and 475 ms for one
# second of work). Gated where the timed bounds are, printed elsewhere with the reason; every run says its accelerator
# and the host's processors.
low = dict(run=run_lines(2, wcpu=350000), wait=wait_lines(2, cpu=1100000))
case('low CPU shares under TCG: printed, not gated', rows_text(2, **low), ['--kind', 'rows', '--smp', '2', '--host-cpus', '4'],
     ALL6, set(), meta=TCG, says=r"^PASS SMP-RUN smp=2: .*tcg: not gated: CPU time of fixed work follows the host's speed under TCG")
case("low CPU shares under TCG: the children's said so", rows_text(2, **low), ['--kind', 'rows', '--smp', '2', '--host-cpus', '4'],
     ALL6, set(), meta=TCG, says=r"^PASS SMP-WAIT smp=2: the children's CPU 1100000 us .*tcg: not gated: CPU time of fixed work follows the host's speed under TCG")
case('low CPU shares under KVM: red', rows_text(2, **low), ['--kind', 'rows', '--smp', '2', '--host-cpus', '4'],
     ALL6 - {'SMP-RUN', 'SMP-WAIT'}, {'SMP-RUN', 'SMP-WAIT'}, why=r"the children's CPU 1100000 us against 2720000 us")
case('every run says its accelerator and the host\'s processors', rows_text(2), ['--kind', 'rows', '--smp', '2', '--host-cpus', '4'],
     ALL6, set(), says=r'^INFO SMP-HOST smp=2: accel kvm, 4 host CPUs for 2 processors')
case('the plant tlb: B reads on past PROT_NONE', rows_text(4, tlb=tlb_lines(faulted='no')),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('a stale read after the new page', rows_text(4, tlb=tlb_lines(stale=1734)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-TLB'}, {'SMP-TLB'})
case('B took SIGSEGV on the page A replaced, present when the fault was routed', rows_text(4, tlb=tlb_lines(bfault='yes')),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-TLB'}, {'SMP-TLB'}, why=r'B took SIGSEGV on a page present at routing')
case('a stale read after the new page, named so', rows_text(4, tlb=tlb_lines(stale=1734)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-TLB'}, {'SMP-TLB'}, why=r'B read the old page after the new one was written')
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
case('no RESCHED taken where the targets ran', rows_text(4, signal=signal_lines(resched='0:1 1:0 2:0 3:0')),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})
case('no resched line', rows_text(4, signal=signal_lines(resched=None)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})
# the sleeper (tests/mpx3-threads' takers at four processors): a process-directed SIGUSR1 that only a sleeping second
# thread may take, woken where it can run; and ten 5 ms apart, each taken before the next comes (not queued: one
# still pending is taken once)
case('the sleeper woken within a tick: green', rows_text(4, signal=signal_lines()), ['--kind', 'rows', '--smp', '4'],
     ALL6, set())
case('the sleeper waits for a tick: red', rows_text(4, signal=signal_lines(sleeper=[40] * 27 + [9000, 40, 40])),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'sleeper: the worst 9000 us')
case('the sleeper waits for a tick under TCG: printed, not gated', rows_text(4, signal=signal_lines(sleeper=[40] * 27 + [9000, 40, 40])),
     ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
case('the sleeper: one of 30 at 3 ms, within the bound', rows_text(4, signal=signal_lines(sleeper=[40] * 29 + [3000])),
     ['--kind', 'rows', '--smp', '4'], ALL6, set())
case('the sleeper: four of 30 over 2 ms: red', rows_text(4, signal=signal_lines(sleeper=[40] * 26 + [3000] * 4)),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'sleeper: 26 of 30 within 2 ms')
# ten 5 ms apart, twenty rounds: each SIGUSR1 handled before the next is sent (a pending signal ends the sleeper's
# interruptible sleep at once, so its delivery is bounded far below the 5 ms between sends); a round that loses one to
# a merge, its predecessor handled late, is red under the timed bounds and printed otherwise
LOST = [10] * 19 + [(9, 9800, 1, 1)]
case('a round loses one: merged into a pending one after a sleep entered with it pending: red', rows_text(4, signal=signal_lines(ten=LOST)),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'round 19: taken 9 of ten, the worst 9800 us')
case('a round loses one under TCG: printed, not gated', rows_text(4, signal=signal_lines(ten=LOST)),
     ['--kind', 'rows', '--smp', '4'], ALL6, set(), meta=TCG)
case('a round of ten, one late: red', rows_text(4, signal=signal_lines(ten=[10] * 19 + [(10, 6000, 0, 1)])),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'round 19: taken 10 of ten, the worst 6000 us')
case('the sleeper never woken', rows_text(4, signal=signal_lines(sleeper=[40] * 29 + ['-'])), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'never ran')
case('no sleeper lines', rows_text(4, signal=signal_lines(sleeper='none')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'sleeper')
case('the sleeper\'s process ended badly', rows_text(4, signal=signal_lines(sleeper_status='0x8b')),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'}, why=r'sleeper process ended')
case('SIGSTOP not held: the target spun on after its stop status (its processor had nothing else to take)',
     rows_text(4, signal=signal_lines(held='no')), ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'},
     why=r'SIGSTOP not held')
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
# dev-final4's boot at 16 read MemFree 1368 kB short 50 ms after the last exec round. The exec parks the space it left
# while an ended sibling's processor still holds it in CR3 (kernel/sched's leave_space), and the kernel frees a parked
# space at its next reap (a fork, a clone, a wait), which the last round's wait4 may run before that processor has
# switched. So each round is read twice: when its wait4 returns, and once its threads are off every processor and a
# wait4 with no child to wait for has run the reap. The settled readings are judged; what each settle gave back is
# printed.
case('frames out at a round\'s wait4, given back once its threads were off every processor and a reap ran',
     rows_text(16, exit=exit_lines(16, back=(0, 0, 0, 0, 1368))), ['--kind', 'rows', '--smp', '16'], ALL6, set(),
     says=r'^PASS SMP-EXIT smp=16: MemFree before 200000 kB, after 200000 kB, each read once the round\'s threads were '
          r'off every processor and a reap had run \(settled in at most 3 ms\); given back by each round\'s settle '
          r'\[0, 0, 0, 0, 1368\] kB; the group\'s VmRSS before each exec \[1316, 1316, 1316, 1316, 1316\] kB')
case('frames short even once settled', rows_text(16, exit=exit_lines(16, after=198632)), ['--kind', 'rows', '--smp', '16'],
     ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'},
     why=r'MemFree around the four exec rounds: frames-kb before 200000 after 198632 \(within 64 kB, each read once settled\)')
case('a round\'s thread still current on a processor 2 s after its wait4',
     rows_text(16, exit=exit_lines(16, left=(0, 0, 1, 0, 0))), ['--kind', 'rows', '--smp', '16'],
     ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'}, why=r'exec round 2: 1 of its threads still current on a processor 2000 ms after its wait4')
case('no settled reading (a probe from before it)', rows_text(4, exit=exit_lines(4, settled=False)),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-EXIT'}, {'SMP-EXIT'},
     why=r'exec round 0: no settled MemFree reading \(`settled-kb`, `left`\)')
case('a wrong wait status', rows_text(4, wait=wait_lines(4, right=15)), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'})
case('children on one processor', rows_text(4, wait=wait_lines(4, cpus='0')), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'})
# SMP-WAIT counts the processors the children ran on from the kernel's ring-3 ticks, not from the sampler, which never
# sees a child on the processor it runs on itself (dev-final3's boot at 16: the sampler missed 0, its own, and 8, idle)
all16 = ','.join(str(i) for i in range(16))
case("the sampler misses its own processor and an idle one; the kernel's ticks count fifteen",
     rows_text(16, wait=wait_lines(16, cpus=','.join(str(i) for i in range(16) if i not in (0, 8)),
                                   ticks=['+0' if i == 8 else '+30' for i in range(16)])),
     ['--kind', 'rows', '--smp', '16'], ALL6, set(), says=r'^PASS SMP-WAIT .*missed \[8\]')
case("the kernel's ticks count fourteen though the sampler saw sixteen",
     rows_text(16, wait=wait_lines(16, cpus=all16, ticks=['+0' if i in (0, 8) else '+30' for i in range(16)])),
     ['--kind', 'rows', '--smp', '16'], ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'}, why=r'ran on 14 processors')
case('a processor with one ring-3 tick did not run the children (the sampler or the parent may take a tick)',
     rows_text(4, wait=wait_lines(4, ticks=['+30', '+30', '+1', '+1'])), ['--kind', 'rows', '--smp', '4'],
     ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'}, why=r'ran on 2 processors')
# what settles a processor the ticks find starved (dev-final3, df3-retake and rows16: 8, twice missed, once 2 ticks):
# whether share() sent it a RESCHED and it found nothing, or never sent it one; and where the sampler sat
case("SMP-WAIT prints each processor's RESCHEDs over the children's window, where the sampler sat and how often each idled",
     rows_text(16, wait=wait_lines(16, cpus=','.join(str(i) for i in range(16) if i not in (0, 8)),
                                   ticks=['+0' if i == 8 else '+30' for i in range(16)],
                                   resched=['+0' if i == 8 else '+3' for i in range(16)],
                                   sampler=(48, [0], [0] * 8 + [48] + [0] * 7))),
     ['--kind', 'rows', '--smp', '16'], ALL6, set(),
     says=r'^PASS SMP-WAIT .*missed \[8\].*RESCHEDs taken 0:\+3 .*8:\+0 .*the sampler sat on \[0\] in 48 samples.*idle in samples .*8:48')
case("no SMP-WAIT user-ticks line (a probe from before the kernel's counters)", rows_text(4, wait=wait_lines(4, ticks=None)),
     ['--kind', 'rows', '--smp', '4'], ALL6 - {'SMP-WAIT'}, {'SMP-WAIT'}, why=r'no SMP-WAIT user-ticks line')
case('a kernel panic mid-run', rows_text(4, extra='PANIC page fault vector 14 error 0x0 rip 0xffffffff80012345 rsp 0xffffd00000027f00 frame 0xffffd00000027e40 cr2 0x0\n'),
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
# SMP-RUN's two checks that depend on the host running every virtual processor (each processor's ring-3 ticks at least
# half the phase's; workers seen on N-1 processors) hold only where the processors fit the host's CPUs, under KVM or TCG
# alike (the hosted job: 16 under TCG on four threads); at 2 and 4 on four they hold.
few = run_lines(16, user=['+20'] * 16, seen={1, 2, 3, 4})
case('16 under TCG on 4 host CPUs: ring-3 ticks under half, workers on four: printed, not gated', rows_text(16, run=few),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '4'], ALL6, set(), meta=TCG)
case('16 under KVM on 4 host CPUs: the same, printed', rows_text(16, run=few),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '4'], ALL6, set())
case('16 under TCG on 20 host CPUs: the same, red', rows_text(16, run=few),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '20'], ALL6 - {'SMP-RUN'}, {'SMP-RUN'}, meta=TCG,
     why=r'gained fewer than half')
case('4 under TCG on 4 host CPUs: a processor under half its ring-3 ticks, red',
     rows_text(4, run=run_lines(4, user=['+100', '+100', '+20', '+100'])), ['--kind', 'rows', '--smp', '4', '--host-cpus', '4'],
     ALL6 - {'SMP-RUN'}, {'SMP-RUN'}, meta=TCG, why=r'gained fewer than half')
case('signals over a tick at 16 on 4 host CPUs: printed, not gated', rows_text(16, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '16', '--host-cpus', '4'], ALL6, set())
case('signals over a tick at 4 on 4 host CPUs: red', rows_text(4, signal=signal_lines(usr1=tick, tgk=tick)),
     ['--kind', 'rows', '--smp', '4', '--host-cpus', '4'], ALL6 - {'SMP-SIGNAL'}, {'SMP-SIGNAL'})

# --- the stress ----------------------------------------------------------------------------------
def stress_text(stage=2, extra='', lost=0, done=True, gains=None):
    n = 4
    p = proc(n, active=1 if stage == 1 else n, stage=stage)
    t = head('stress') + block('start', p)
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
    t += block('stress', p)
    if done:
        t += 'SMP-LOCK done\n' + tail()
    return t


sa = ['--kind', 'stress', '--smp', '4', '--boot', '3']
case('stress green', stress_text(), sa, {'SMP-LOCK'}, set())
case('stress at stage 1: red at the gate', stress_text(stage=1), sa, set(), {'SMP-LOCK'})
# kernel/sched's duplicate-running check (`take_next`): a slot the queue hands back that a processor still runs;
# SMP-DUP carries that line verbatim in every kind (the W_CPU plant's name), and no other panic is it
DUP = 'PANIC sched: slot 12 running on two processors: state 1, cpu 0, taken from the queue by cpu 2\n'
case('the plant lock: a slot on two processors, the boot dies', stress_text(extra=DUP, done=False), sa, set(),
     {'SMP-LOCK', 'SMP-DUP'})
case('a slot on two processors in a rows boot', head('rows') + DUP, ['--kind', 'rows', '--smp', '4'], set(),
     ALL6 | {'SMP-DUP'})
case('a slot on two processors in a cap2 boot', head('cap') + DUP, ['--kind', 'cap2', '--smp', '4', '--cap', '2'], set(),
     {'SMP-CAP', 'SMP-DUP', 'SMP-DEAD'})
case('a slot on two processors at one processor', head('one') + DUP, ['--kind', 'one', '--smp', '1'], set(),
     {'SMP-ONE', 'SMP-DUP', 'SMP-REFUSE'})  # the boot dies before the probe's refusals
case('a lost signal in the storm', stress_text(lost=1), sa, set(), {'SMP-LOCK'})
# the kernel lock's door (kernel/interrupts): a processor carrying the lock into ring 3 panics by name, and
# SMP-KLOCK carries that line; another panic (the slot on two processors, above) is not the lock's door
KLOCK = 'PANIC klock: entered from ring 3 holding it, cpu  0x0000000000000000\n'
case('the lock plant in a stress boot: red by the door\'s line', stress_text(extra=KLOCK, done=False), sa, set(),
     {'SMP-LOCK', 'SMP-KLOCK'})
case('the lock plant in a rows boot: the probe stops at its first entry', head('rows') + KLOCK,
     ['--kind', 'rows', '--smp', '4'], set(), ALL6 | {'SMP-KLOCK'})
case('the lock plant at one processor', head('one') + KLOCK, ['--kind', 'one', '--smp', '1'], set(),
     {'SMP-ONE', 'SMP-KLOCK', 'SMP-REFUSE'})  # the boot dies before the probe's refusals
# contract §3.7 (c) as amended: the console kernel starts no heap, so the runtime can allocate nothing on any
# processor, locked or not; every /proc/pax-cpus says `heap-started 0` and an allocation panics by name
HEAP = 'PANIC heap: alloc before heap.start, asked 0x0000000000000010\n'
case('the heap not started, said in every /proc/pax-cpus', rows_text(4), ['--kind', 'rows', '--smp', '4'],
     ALL6 | {'SMP-NOHEAP'}, set())
case('stress: the heap not started', stress_text(), sa, {'SMP-LOCK', 'SMP-NOHEAP'}, set())
case('the plant apalloc in a stress boot: an application processor allocates before the lock',
     stress_text(extra=HEAP, done=False), sa, set(), {'SMP-LOCK', 'SMP-NOHEAP'}, why=r'PANIC heap: alloc before heap\.start')
case('the plant apalloc in a rows boot: the boot dies at an application processor\'s first entry', head('rows') + HEAP,
     ['--kind', 'rows', '--smp', '4'], set(), ALL6 | {'SMP-NOHEAP'}, why=r'SMP-NOHEAP .*PANIC heap: alloc before heap\.start')
case('a kernel whose heap was started', rows_text(4, heap=1), ['--kind', 'rows', '--smp', '4'], ALL6, {'SMP-NOHEAP'},
     why=r'SMP-NOHEAP .*heap-started 1')
case('a /proc/pax-cpus that does not say whether the heap was started', rows_text(4, heap=None),
     ['--kind', 'rows', '--smp', '4'], ALL6, {'SMP-NOHEAP'})
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


def end_text(how, stage=2, order='right', hup=False):
    n = 4
    p = proc(n, active=1 if stage == 1 else n, stage=stage)
    t = head('end') + block('start', p)
    t += f'SMP-END spinners 4 on cpus {"0" if stage == 1 else "0,1,2,3"}\nSMP-END asking reboot(2) {how}\n'
    stop = 'cpus: 3 application processors stopped for the end\n' if stage == 2 else ''
    the_end = 'PAX: the end: SIGTERM to 5 processes, 5 ended within 0 ms\n'
    if hup:  # the controlling process (pid 1) ends by SIGTERM and its terminal's hangup ends the spinners (rel2's lines)
        the_end = ('user: smpprobe pid 1 killed: SIGTERM after 27 runs\n'
                   + ''.join(f'user: smpprobe pid {p} killed: SIGHUP after 2 runs\n' for p in (4, 2, 3)) + the_end)
    line = f'user: smpprobe pid 1 reboot(2): the volumes written and marked clean; {"restarting" if how == "restart" else "halting"}\n'
    t += (stop + the_end if order == 'early' else the_end + stop) + line
    return t + ('halt\n' if how == 'halt' else '')


halted = regs(0, KTEXT, rfl=0x2) + ''.join(regs(k, KTEXT + 0x40, rfl=0x2) for k in range(1, 4))
idle_dump = regs(0, KTEXT, rfl=0x2) + ''.join(regs(k, SYMS['pax_ap_halt'][0] + 3, rfl=0x246) for k in range(1, 4))
case('end halt green', end_text('halt'), ['--kind', 'end-halt', '--smp', '4'], {'SMP-END'}, set(), dumps=[halted] * 3)
# the end's own SIGHUP: pid 1, the controlling process, ends first, and its terminal's hangup reaches the spinners in its
# foreground group before their SIGTERM (a lower signal number is taken first); a SIGHUP kill before the end asks is red
case('end halt: the spinners ended by the terminal\'s hangup', end_text('halt', hup=True), ['--kind', 'end-halt', '--smp', '4'],
     {'SMP-END'}, set(), dumps=[halted] * 3)
case('end halt: a program killed by SIGHUP before the end',
     end_text('halt').replace('SMP-END asking', 'user: smpprobe pid 7 killed: SIGHUP after 3 runs\nSMP-END asking'),
     ['--kind', 'end-halt', '--smp', '4'], set(), {'SMP-END'}, dumps=[halted] * 3, why=r'killed: SIGHUP')
# the STOP step's test kinds (a test build) and the shipped kernel given the test words
NOOFF = 'poweroff: not done (pax.nopoweroff, a test kernel)\n'
case('end-nooff green', end_text('halt') + NOOFF, ['--kind', 'end-nooff', '--smp', '4'], {'SMP-END-NOOFF'}, set(),
     dumps=[halted] * 3)
case('end-nooff: the power-off done after all', end_text('halt'), ['--kind', 'end-nooff', '--smp', '4'], set(),
     {'SMP-END-NOOFF'}, dumps=[halted] * 3)
case('end-nooff: processors ticking after the end', end_text('halt') + NOOFF, ['--kind', 'end-nooff', '--smp', '4'],
     set(), {'SMP-END-NOOFF'}, dumps=[idle_dump] * 3)
P1 = 'SMP-PANIC spinners 4\nPANIC testwords: a test panic, cpu  0x0000000000000001\n'
P2 = P1 + "PANIC cpu 2 (a second panic, cpu 1's first): testwords: a test panic, cpu  0x0000000000000002\n"
case('panic green', head('spin') + P1, ['--kind', 'panic', '--smp', '4'], {'SMP-PANIC-STOP'}, set(), dumps=[halted] * 3)
case('panic: a processor spinning on', head('spin') + P1, ['--kind', 'panic', '--smp', '4'], set(), {'SMP-PANIC-STOP'},
     dumps=[idle_dump] * 3)
case('panic: a late processor named', head('spin') + P1 + 'cpus: cpu 3 did not stop for the panic\n',
     ['--kind', 'panic', '--smp', '4'], set(), {'SMP-PANIC-STOP'}, dumps=[halted] * 3)
case('panic under TCG: printed, not gated', head('spin') + P1 + 'cpus: cpu 3 did not stop for the panic\n',
     ['--kind', 'panic', '--smp', '4'], {'SMP-PANIC-STOP'}, set(), meta=TCG, dumps=[halted] * 3)
case('panic2 green', head('spin') + P2, ['--kind', 'panic2', '--smp', '4'], {'SMP-PANIC-TWO'}, set(), dumps=[halted] * 3)
case('panic2: the two lines interleaved (a timed-out wait): read by their texts',
     head('spin') + 'SMP-PANIC spinners 4\nPANIC testwPANIC cpu 2 (a second panic, cpu 1\'s first): testwords: a test panic, '
     'cpu  0x2\nords: a test panic, cpu  0x0000000000000001\n', ['--kind', 'panic2', '--smp', '4'], set(), {'SMP-PANIC-TWO'},
     dumps=[halted] * 3)
case('panic2: the two lines interleaved, each text whole', head('spin') + 'SMP-PANIC spinners 4\nPANIC testwords: a test '
     "panic, cpu  0x1PANIC cpu 2 (a second panic, cpu 1's first): testwords: a test panic, cpu  0x2\n",
     ['--kind', 'panic2', '--smp', '4'], {'SMP-PANIC-TWO'}, set(), dumps=[halted] * 3)
case('panic2: the second panic printed in full (two owners)', head('spin') + P1 + P1.split('\n')[1] + '\n',
     ['--kind', 'panic2', '--smp', '4'], set(), {'SMP-PANIC-TWO'}, dumps=[halted] * 3)
TW = 'testwords: pax.nopoweroff ignored (not a test kernel)\ntestwords: pax.panictest ignored (not a test kernel)\n'
case('testwords green', head('end') + TW, ['--kind', 'testwords', '--smp', '4', '--qemu-status', '0'], {'SMP-TESTWORDS'}, set())
case('testwords: a word not reported', head('end') + TW.split('\n')[0] + '\n',
     ['--kind', 'testwords', '--smp', '4', '--qemu-status', '0'], set(), {'SMP-TESTWORDS'})
case('testwords: the power-off skipped', head('end') + TW, ['--kind', 'testwords', '--smp', '4', '--qemu-status', '1'],
     set(), {'SMP-TESTWORDS'})
# the shipped ELF holds a test mark: the test op or test panic by name (the native tier), or the test op's static
# `fired`, which the release tier's inlining keeps where it removes both names
for mark in ('_Wtestwords.fire$d0d02dc177140c90', '_Wtestwords.test_panic$be7c8dfa707358fc', '_Wtestwords.fired.s334a994a33b36f9'):
    case(f'testwords: the shipped ELF holds {mark.split("$")[0].split(".s3")[0]}', head('end') + TW,
         ['--kind', 'testwords', '--smp', '4', '--qemu-status', '0'], set(), {'SMP-TESTWORDS'},
         files={'syms': [mark]}, why=r'test symbols')
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
def refuse_lines(write_ro='yes', fetch_nx='yes', kernel_read='yes'):
    st = {'yes': '0xb00', 'no': '0x0'}
    return ''.join(f'SMP-REFUSE {w} refused {v} status {st[v]}\n' for w, v in
                   (('write-ro', write_ro), ('fetch-nx', fetch_nx), ('kernel-read', kernel_read))) + 'SMP-REFUSE done\n'


def one_text(n, cmdline_parked=False, stage=1, boot_line=None, mode='one', refuse=None):
    p = proc(n, active=1, started=1 if cmdline_parked or n == 1 else n, stage=1)
    t = 'PAX: the console\n' + (boot_line + '\n' if boot_line else '') + head(mode)[len('PAX: the console\n'):]
    return t + block('start', p) + active_line(1, 1) + (refuse_lines() if refuse is None else refuse) + block('end', p) + tail()


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
case('one green (stage 1)', one_text(1), ['--kind', 'one', '--smp', '1'], {'SMP-ONE', 'SMP-REFUSE'}, set())
# SMP-REFUSE: the refusals kernel/vm keeps beside its retry of a fault on a page present at routing
case('a write to a read-only page not refused', one_text(1, refuse=refuse_lines(write_ro='no')),
     ['--kind', 'one', '--smp', '1'], {'SMP-ONE'}, {'SMP-REFUSE'}, why=r'write-ro not refused')
case('a fetch from a page without PROT_EXEC not refused', one_text(1, refuse=refuse_lines(fetch_nx='no')),
     ['--kind', 'one', '--smp', '1'], {'SMP-ONE'}, {'SMP-REFUSE'}, why=r'fetch-nx not refused')
case('a read of the kernel half not refused', one_text(1, refuse=refuse_lines(kernel_read='no')),
     ['--kind', 'one', '--smp', '1'], {'SMP-ONE'}, {'SMP-REFUSE'}, why=r'kernel-read not refused')
case('no refusal lines at all', one_text(1, refuse=''), ['--kind', 'one', '--smp', '1'], {'SMP-ONE'}, {'SMP-REFUSE'})
case('one with a cpus: line', one_text(1, boot_line='cpus: application processors idle 0 of 0'),
     ['--kind', 'one', '--smp', '1'], set(), {'SMP-ONE'})
case('cap1 green (stage 1 ignores the word)', one_text(4), ['--kind', 'cap1', '--smp', '4', '--cap', '1'], {'SMP-CAP'}, set())


def dead_lines(statuses=('0x700',) * 3, revived=(0, 0, 0), running=(2, 2, 2), done=True):
    t = ''.join(f'SMP-DEAD round {r} status {s} running {g} revived {v}\n'
                for r, (s, g, v) in enumerate(zip(statuses, running, revived)))
    return t + ('SMP-DEAD done\n' if done else '')


def cap2_text(stage=2, kthreads=None, dead=None):
    p = proc(4, active=1 if stage == 1 else 2, stage=stage, cap=None if stage == 1 else 2, kthreads=kthreads)
    t = head('cap') + block('start', p) + active_line(4, stage, cap=2)
    t += run_lines(4, stage, rounds=1, cap=None if stage == 1 else 2)
    if stage == 2:
        t += dead_lines() if dead is None else dead
    return t + block('end', p) + tail()


case('cap2 green', cap2_text(), ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP', 'SMP-PIN', 'SMP-DEAD'}, set())
# SMP-DEAD: a thread another processor's exit_group ended while it ran is never run again (kernel/sched's
# `preempt` and `kick` switch a DEAD thread off; before them it was queued again, or resumed, and ran on)
case('a thread of the ended group current again', cap2_text(dead=dead_lines(revived=(0, 3, 0))),
     ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, {'SMP-DEAD'})
case('an exit_group with no status in 2 s', cap2_text(dead=dead_lines(statuses=('0xdead',), revived=(10,), running=(2,))),
     ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, {'SMP-DEAD'})
# SMP-PARK: exec's parked-space table (two at once; one word a slot, the first form, could not)
PARK = 'sched: parked spaces: 2 held parked at once, 0 left once let go\n'
case('the parked-space check green', PARK + cap2_text(), ['--kind', 'cap2', '--smp', '4', '--cap', '2'],
     {'SMP-CAP', 'SMP-DEAD', 'SMP-PARK'}, set())
case('one space parked where two were', PARK.replace(': 2 held', ': 1 held') + cap2_text(),
     ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP', 'SMP-DEAD'}, {'SMP-PARK'})
case('the table full at the second park', 'PANIC sched: more parked spaces than other processors (a kernel bug), slot 0\n'
     + cap2_text(), ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, {'SMP-PARK', 'SMP-DEAD'})
case('the group never on the second processor', cap2_text(dead=dead_lines(running=(2, 1, 2))),
     ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, {'SMP-DEAD'})
# kernel threads run on CPU 0 alone (stage 2's amendment to its contract's §3.6): an application processor's
# `runs` line counts none (`kthreads 0`); CPU 0's may count any number
case('a kernel thread on an application processor in a cap2 boot', cap2_text(kthreads={1: 3}),
     ['--kind', 'cap2', '--smp', '4', '--cap', '2'], {'SMP-CAP'}, {'SMP-PIN'})
case('a kernel thread on an application processor in a rows boot', rows_text(4, kthreads={2: 1}),
     ['--kind', 'rows', '--smp', '4'], ALL6, {'SMP-PIN'})
case('kernel threads on CPU 0 alone', rows_text(4, kthreads={0: 250}), ['--kind', 'rows', '--smp', '4'],
     ALL6 | {'SMP-PIN'}, set())
case('a runs line with no kthreads count', rows_text(4).replace(' kthreads 0', ''), ['--kind', 'rows', '--smp', '4'],
     ALL6, {'SMP-PIN'})
case('cap2 at stage 1: red', cap2_text(stage=1), ['--kind', 'cap2', '--smp', '4', '--cap', '2'], set(), {'SMP-CAP', 'SMP-DEAD'})
t = re.sub(r'^(SMP-RUN round 0 sample 1 .*) 3:i$', r'\1 3:201', cap2_text(), flags=re.M)
case('cap2 with a worker past the cap', t, ['--kind', 'cap2', '--smp', '4', '--cap', '2'], set(), {'SMP-CAP'})



# --- the traced group's exit and the interrupt (kind trace) -------------------------------------
# dev-final5's mpx5-trace hang at four processors: exit_group with PTRACE_O_TRACEEXIT parked the group's other
# traced thread for its PTRACE_EVENT_EXIT from the exiting thread's processor while it ran on another (kernel/sched's
# `trace_group_exit`): no RESCHED, no frame; it ran on, and its own futex call overwrote the stop. The kind's two rows:
# SMP-TRACE-EXIT, ten rounds (spinning and in a system-call loop, in turn) of a traced group whose second thread runs on
# another processor when the leader exits; SMP-TRACE-INT, nine PTRACE_INTERRUPTs of a seized tracee running on another
# processor, each stop's latency (8 of 9 within 2 ms under KVM; a tracee told nothing stops at its processor's tick).
def trace_exit_lines(n, rounds=10, tcpu=None, done=True, bad=None):
    # bad: {round: {field: value}}, the round's line as the probe prints it otherwise
    out = ''
    for r in range(rounds):
        f = dict(variant='spin' if r % 2 == 0 else 'yield', tcpu=(1 if n > 1 else -1) if tcpu is None else tcpu,
                 stops=2, leader='0x6057f', thread='0x6057f', ran=0, cur='-', deaths=2, st='0x2500 0x2500',
                 echild=-10, failed='none')
        f.update((bad or {}).get(r, {}))
        out += (f'SMP-TRACE-EXIT round {r} {f["variant"]} thread-cpu {f["tcpu"]} exit-stops {f["stops"]} '
                f'leader {f["leader"]} thread {f["thread"]} ran-after {f["ran"]} current-after {f["cur"]} '
                f'deaths {f["deaths"]} statuses {f["st"]} echild {f["echild"]} failed-at {f["failed"]}\n')
    return out + ('SMP-TRACE-EXIT done\n' if done else '')


def trace_int_lines(us=None, status='0x80057f', ran='yes', cpu=1, done=True):
    us = us or [40, 35, 31, 30, 33, 29, 31, 30, 32]
    out = f'SMP-TRACE-INT seize 0 cpu {cpu}\n'
    for k, u in enumerate(us):
        out += f'SMP-TRACE-INT round {k} cpu {cpu} req 0 status {status} us {u} cont 0 ran {ran}\n'
    return out + ('SMP-TRACE-INT done\n' if done else '')


# df6-2b3ac6fd's smp4-jobs line 89 (`SIGSTOP to it: it runs on yes`) at four processors: SMP-STOPWRITE, 24 stops of a
# process writing a pipe a byte a call on another processor; drained at once (settle 0) one byte may follow the stop,
# the write in progress when it came; drained 50 ms on (settle 50) none, and no ring-3 turn.
def stopwrite_lines(n, rounds=24, done=True, bad=None):
    # bad: {round: {field: value}}, the round's line as the probe prints it otherwise
    out = ''
    for r in range(rounds):
        settle = 50 if r % 2 else 0
        f = dict(settle=settle, wc=1 if n > 1 else '-', mc=0, looks=1, b=1 if settle == 0 and r % 4 == 2 else 0, t=0,
                 st='0x137f', ct='0xffff', again=1400)
        f.update((bad or {}).get(r, {}))
        out += (f'SMP-STOPWRITE round {r} settle {f["settle"]} writer-cpu {f["wc"]} me-cpu {f["mc"]} looks {f["looks"]} '
                f'bytes-after {f["b"]} turns-after {f["t"]} stop-status {f["st"]} cont-status {f["ct"]} '
                f'bytes-resumed {f["again"]}\n')
    return out + ('SMP-STOPWRITE done\n' if done else '')


def trace_text(n, exit=None, intr=None, active=None, sw=None):
    p = proc(n, active=active)
    t = head('trace') + block('start', p) + active_line(n)
    t += trace_exit_lines(n) if exit is None else exit
    t += (trace_int_lines(cpu=1 if n > 1 else -1) if intr is None else intr)
    t += stopwrite_lines(n) if sw is None else sw
    return t + block('end', p) + tail()


TR = {'SMP-TRACE-EXIT', 'SMP-TRACE-INT', 'SMP-STOPWRITE'}
for n in (2, 4, 16):
    case(f'trace green at {n}', trace_text(n), ['--kind', 'trace', '--smp', str(n)], TR, set(),
         says=r'^PASS SMP-TRACE-EXIT smp=%d trace: 10 rounds \(5 spinning, 5 in a system-call loop\)' % n)
case('trace at 1: the exit green, the interrupt not asked', trace_text(1), ['--kind', 'trace', '--smp', '1'],
     {'SMP-TRACE-EXIT'}, set(), says=r'^NOT-ASKED SMP-TRACE-INT smp=1 trace: one processor')
farpark = {r: (dict(ran=41233 + r, cur=1) if r % 2 == 0 else dict(stops=1, thread='-', ran='-', deaths=0, st='-',
               echild='-', failed='exit')) for r in range(10)}
case('the far park: a spinning thread runs on past its reported stop, a looping one loses it',
     trace_text(4, exit=trace_exit_lines(4, bad=farpark)), ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'},
     {'SMP-TRACE-EXIT'}, why=r'round 0 \(spin\): the thread made 41233 spins in the 20 ms after its PTRACE_EVENT_EXIT '
                             r'stop was reported \(current on processor 1\)')
case('a looping thread\'s stop never reported', trace_text(4, exit=trace_exit_lines(4, bad={1: farpark[1]})),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'}, {'SMP-TRACE-EXIT'},
     why=r'round 1 \(yield\): 1 PTRACE_EVENT_EXIT stop of 2 reported within 2 s \(the thread\'s missing\)')
case('the thread not on another processor at its group\'s exit', trace_text(4, exit=trace_exit_lines(4, bad={0: dict(tcpu=-1)})),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'}, {'SMP-TRACE-EXIT'},
     why=r'round 0 \(spin\): the thread was not seen on another processor before its group\'s exit \(the case not set up\)')
case('a death not reported after the CONTs', trace_text(4, exit=trace_exit_lines(4, bad={2: dict(deaths=1, st='0x2500 -')})),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'}, {'SMP-TRACE-EXIT'},
     why=r'round 2 \(spin\): 1 death of 2 reported within 2 s of the CONTs')
case('a round that never began (the clone not reported)', trace_text(4, exit=trace_exit_lines(4, bad={3: dict(
     stops=0, leader='-', thread='-', ran='-', deaths=0, st='-', echild='-', failed='clone')})),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'}, {'SMP-TRACE-EXIT'}, why=r'round 3 \(yield\): failed at the clone')
case('the probe stopped inside the exit rounds', trace_text(4, exit=trace_exit_lines(4, rounds=4, done=False)),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-INT'}, {'SMP-TRACE-EXIT'},
     why=r'4 rounds of 10 and no `SMP-TRACE-EXIT done`')
tick = [3000, 7000, 500, 9000, 4000, 6000, 8000, 2500, 1000]
case('interrupts stopped at the tick, not at once (no RESCHED)', trace_text(4, intr=trace_int_lines(us=tick)),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-EXIT'}, {'SMP-TRACE-INT'},
     why=r'2 of 9 PTRACE_INTERRUPT stops within 2 ms \(8 wanted under KVM\)')
case('interrupts at the tick under TCG: printed, not gated', trace_text(4, intr=trace_int_lines(us=tick)),
     ['--kind', 'trace', '--smp', '4'], TR, set(), meta=TCG)
case('an interrupt stop of the wrong kind', trace_text(4, intr=trace_int_lines(status='0x137f')),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-EXIT'}, {'SMP-TRACE-INT'},
     why=r'round 0: status 0x137f, want 0x80057f \(PTRACE_EVENT_STOP\)')
case('a tracee not running again after its CONT', trace_text(4, intr=trace_int_lines(ran='no')),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-EXIT'}, {'SMP-TRACE-INT'}, why=r'round 0: not running 20 ms after its CONT')
case('the tracee never on another processor', trace_text(4, intr=trace_int_lines(cpu=-1)),
     ['--kind', 'trace', '--smp', '4'], {'SMP-TRACE-EXIT'}, {'SMP-TRACE-INT'},
     why=r'round 0: the tracee not seen on another processor before its interrupt')
case('one processor runs threads: the three red at the gate', trace_text(4, active=1), ['--kind', 'trace', '--smp', '4'],
     set(), TR, why=r'active 1 of 4')
# trace74's red point: the unfixed kernel panicked in most boots at 2 and 4 after a lost stop (a kernel page fault),
# the rounds after it never printed; the rows name the kernel's line, whatever else the boot printed
PAN = 'PANIC page fault vector 14 error 0x0000000000000000 rip 0xffffffff8016fbfc rsp 0xffffd0000003f960 cr2 0x0000000000000098\n'
case('a kernel panic in a trace boot: the three red by its line', trace_text(4).replace('SMP-TRACE-INT done\n', 'SMP-TRACE-INT done\n' + PAN),
     ['--kind', 'trace', '--smp', '4'], set(), TR, why=r'the kernel said: \[\'PANIC page fault vector 14')
TX = {'SMP-TRACE-EXIT', 'SMP-TRACE-INT'}
SW = ['--kind', 'trace', '--smp', '4']
for n in (1, 2, 4, 16):
    case(f'stop-write green at {n}', trace_text(n), ['--kind', 'trace', '--smp', str(n)], {'SMP-STOPWRITE'}, set(),
         says=r'^PASS SMP-STOPWRITE smp=%d trace: 24 stops .* \(6 of 12 a write in progress\)' % n)
# the plant stoprun (signal.on_return's park skipped): a stopped process's thread runs on in ring 3 while nothing else
# is queued on its processor, writing a pipe's worth in the 300 ms
stoprun = {r: dict(b=65536, t=900 + r) for r in range(24)}
case('the plant stoprun: the writer runs on after its stop', trace_text(4, sw=stopwrite_lines(4, bad=stoprun)), SW, TX,
     {'SMP-STOPWRITE'}, why=r'round 0 \(settle 0 ms\): 65536 bytes written after the stop \(at most the one write in progress\)')
case('two writes after a stop drained at once', trace_text(4, sw=stopwrite_lines(4, bad={4: dict(b=2)})), SW, TX,
     {'SMP-STOPWRITE'}, why=r'round 4 \(settle 0 ms\): 2 bytes written after the stop')
case('a byte after the stop had taken effect', trace_text(4, sw=stopwrite_lines(4, bad={3: dict(b=1)})), SW, TX,
     {'SMP-STOPWRITE'}, why=r'round 3 \(settle 50 ms\): 1 bytes and 0 ring-3 turns after the stop had taken effect')
case('a ring-3 turn after the stop had taken effect', trace_text(4, sw=stopwrite_lines(4, bad={5: dict(t=1)})), SW, TX,
     {'SMP-STOPWRITE'}, why=r'round 5 \(settle 50 ms\): 0 bytes and 1 ring-3 turns after the stop had taken effect')
case('the writer not on another processor before its stop', trace_text(4, sw=stopwrite_lines(4, bad={0: dict(wc='-', looks=200)})),
     SW, TX, {'SMP-STOPWRITE'}, why=r'round 0 \(settle 0 ms\): the writer not seen on another processor in 2 s of '
                                   r'looking \(200 looks; the case not set up\)')
case('the writer on the prober\'s own processor', trace_text(4, sw=stopwrite_lines(4, bad={2: dict(wc=0, looks=200)})),
     SW, TX, {'SMP-STOPWRITE'}, why=r'round 2 \(settle 0 ms\): the writer not seen on another processor')
# df7-0ec7099b's red at two processors: round 0's writer not seen elsewhere in 20 looks; the set-up now looks for 2 s,
# the looks printed: a set-up that took many is green and says so
case('a set-up that took 37 looks: green, its looks said', trace_text(2, sw=stopwrite_lines(2, bad={0: dict(looks=37)})),
     ['--kind', 'trace', '--smp', '2'], {'SMP-STOPWRITE'}, set(),
     says=r'^PASS SMP-STOPWRITE smp=2 trace: .* the set-up\'s looks most 37, 1 rounds more than one')
# the plant pinned: the application processors take no process's thread, every one on the boot processor; each row's
# set-up names it, never a pass
pinned = {r: dict(wc=0, looks=200) for r in range(24)}
pinned_tx = {r: dict(tcpu=-1) for r in range(10)}
case('the plant pinned: no thread ever on another processor, every set-up named',
     trace_text(4, exit=trace_exit_lines(4, bad=pinned_tx), intr=trace_int_lines(cpu=-1), sw=stopwrite_lines(4, bad=pinned)),
     SW, set(), TR, why=r'round 0 \(settle 0 ms\): the writer not seen on another processor in 2 s of looking \(200 looks')
case('a stop not reported', trace_text(4, sw=stopwrite_lines(4, bad={6: dict(st='-')})), SW, TX, {'SMP-STOPWRITE'},
     why=r'round 6 \(settle 0 ms\): stop status - and continue status 0xffff')
case('the writer not writing again after SIGCONT', trace_text(4, sw=stopwrite_lines(4, bad={7: dict(again=0)})), SW, TX,
     {'SMP-STOPWRITE'}, why=r'round 7 \(settle 50 ms\): no byte in the 30 ms after SIGCONT')
case('the probe stopped inside the stop rounds', trace_text(4, sw=stopwrite_lines(4, rounds=10, done=False)), SW, TX,
     {'SMP-STOPWRITE'}, why=r'10 rounds of 24 and no `SMP-STOPWRITE done`')
case('a stop-write round under TCG: judged the same', trace_text(4, sw=stopwrite_lines(4, bad={4: dict(b=2)})), SW, TX,
     {'SMP-STOPWRITE'}, meta=TCG, why=r'round 4 \(settle 0 ms\): 2 bytes written after the stop')


# --- the leave kind (SMP-EXEC-LEAVE): a test kernel's `pax.slowleave=MS` holds each application processor whose thread
# was ended in place before it switches it off; the rounds' statuses, the holds' lines, and no panic. The red the rows
# at 4 on two host CPUs met at f4942845: `PANIC sched: no process area for slot 0x…06` after an exec round's child line.
SLOW_WORD = ('testwords: pax.slowleave=200 (a test kernel): a thread ended in place held 20 ticks on its application '
             'processor before it is switched off\n')


def settle_lines(n, rounds=20, held=(0, 2, 3, 5, 8), short=(), left=(), st='0x900', late=480000, keys=True,
                 mcpu=lambda r: 1, mkey=True):
    """The leave mode's exec-settle rounds (the exec'ing sibling waits to see the main thread current on an application
    processor, each round's MemFree read at its wait4, settled, and 500 ms on): `held` the rounds whose wait4 came back
    with the space the exec left still parked (1392 kB out), `short` those whose settled reading is still out (the
    settle read too soon), `left` those with a thread still current when the settle gave up; keys=False: a line with no
    MemFree readings; `mcpu(r)` the processor the main thread was seen on at round r's exec (-1: not seen on an
    application processor in 2 s); mkey=False: a line without it."""
    run = min(4, n)
    out = ''
    for r in range(rounds):
        waited = late - 1392 if r in held else late
        settled = late - 1392 if r in short else late
        ms = 2000 if r in left else 200 if r in held and r not in short else 0
        mem = (f' waited-kb {waited} settled-kb {settled} late-kb {late} settle-ms {ms} left {1 if r in left else 0}'
               if keys else '')
        mem += f' main-cpu {mcpu(r)}' if mkey else ''
        out += f'SMP-EXIT exec-child pid {300 + 4 * r}\nSMP-LEAVE exec-settle {r} status {st} running {run} of 4{mem}\n'
    return out


def leave_lines(n, leader=('0xa00',) * 4, execs=30, kills=5, exec_st='0x900', kill_st='0x9', done=True, stop_after=None,
                settles=None):
    """The probe's SMP-LEAVE lines; stop_after: the transcript ends after that many exec rounds' child lines (a panic's
    or a hang's place), with no done; settles: the exec-settle rounds' lines (`settle_lines(n)` when None)."""
    run = min(4, n)
    out = ''.join(f'SMP-LEAVE leader-exit {r} status {st} running {run} of 4\n' for r, st in enumerate(leader))
    for r in range(execs):
        out += f'SMP-EXIT exec-child pid {60 + 4 * r}\n'
        if stop_after is not None and r >= stop_after:
            return out
        out += f'SMP-LEAVE exec {r} status {exec_st} running {run} of 4\n'
    for r in range(kills):
        out += f'SMP-EXIT exec-child pid {200 + 4 * r}\nSMP-LEAVE exec-kill {r} status {kill_st} running {run} of 4\n'
    out += settle_lines(n) if settles is None else settles
    return out + ('SMP-LEAVE done\n' if done else '')


def leave_text(n, word=True, slows=12, lines=None, extra='', end=True, tgid=lambda i: 0 if i % 3 == 0 else 60 + 4 * i):
    t = (SLOW_WORD if word else '') + head('leave') + block('start', proc(n)) + active_line(n)
    t += ''.join(f'testwords: a slow leave, cpu {1 + i % (n - 1)}, slot {5 + i % 3}, tgid {tgid(i)}\n' for i in range(slows))
    t += (lines if lines is not None else leave_lines(n)) + extra
    return t + (block('end', proc(n)) + tail() if end else '')


PANIC6 = 'PANIC sched: no process area for slot 0x0000000000000006\npanic: halt\n'
for n in (2, 4):
    case(f'leave green at {n}', leave_text(n), ['--kind', 'leave', '--smp', str(n)], {'SMP-EXEC-LEAVE'}, set(),
         says=rf'^PASS SMP-EXEC-LEAVE smp={n} leave: 4 leader-exit, 30 exec, 5 exec-kill and 20 exec-settle rounds')
    # The rows at 4 on two host CPUs at b06378bb: the last exec round read MemFree 1392 kB short once settled, `left
    # 0`. An exec gives its old leader's pid to the caller (kernel/sched's exec_alone), and /proc/pax-cpus names a
    # processor still running that thread `current kernel`; the settle looked for the group's thread ids alone, so it
    # read while that processor's CR3 still held the space the exec had parked. The exec-settle rounds open that window
    # on purpose: the main thread says go only once a look shows it current on an application processor, where the
    # test word holds it, with the exec'ing sibling current beside it (`main-cpu`). Left to the scheduler, boots under
    # KVM at 2 never had it there at the exec (no hold of a thread with tgid 0 in 40 rounds over two boots).
    case(f'leave at {n}: an exec-settle round read MemFree with the space the exec left still parked',
         leave_text(n, lines=leave_lines(n, settles=settle_lines(n, short=(3,)))), ['--kind', 'leave', '--smp', str(n)],
         set(), {'SMP-EXEC-LEAVE'},
         why=r'exec-settle round 3: MemFree settled 478608 kB, 1392 kB below the reading 500 ms on \(480000 kB\)')
    case(f'leave at {n}: the exec\'d leader collected while a sibling\'s processor held it (the panic at 4 on two host CPUs)',
         leave_text(n, lines=leave_lines(n, stop_after=1), extra=PANIC6, end=False), ['--kind', 'leave', '--smp', str(n)],
         set(), {'SMP-EXEC-LEAVE'}, why=r'the kernel said: \[.PANIC sched: no process area for slot 0x0000000000000006')
case('leave under TCG: judged the same', leave_text(4), ['--kind', 'leave', '--smp', '4'], {'SMP-EXEC-LEAVE'}, set(), meta=TCG)
case('leave: the parent never woken after a hold (a hang: no more rounds, no done)',
     leave_text(4, lines=leave_lines(4, stop_after=3), end=False), ['--kind', 'leave', '--smp', '4'], set(),
     {'SMP-EXEC-LEAVE'}, why=r'1 of 3 exec rounds, 0 of 0 exec-kill|no `SMP-LEAVE done`')
case('leave: a shipped kernel (the word not taken)', leave_text(4, word=False, slows=0), ['--kind', 'leave', '--smp', '4'],
     set(), {'SMP-EXEC-LEAVE'}, why=r'no `testwords: pax.slowleave=')
case('leave: the word taken but no processor held', leave_text(4, slows=0), ['--kind', 'leave', '--smp', '4'], set(),
     {'SMP-EXEC-LEAVE'}, why=r'0 slow leaves')
case('leave at 2: holds only of threads with no process (an exec\'s old leader, charged nothing)',
     leave_text(2, tgid=lambda i: 0), ['--kind', 'leave', '--smp', '2'], set(), {'SMP-EXEC-LEAVE'},
     why=r'12 slow leaves, none of a thread with a tgid')
case('leave green at 2 says how many holds were of a thread with a tgid', leave_text(2), ['--kind', 'leave', '--smp', '2'],
     {'SMP-EXEC-LEAVE'}, set(), says=r'12 slow leaves, 8 of a thread with a tgid')
case('leave at 2: the leader check\'s panic is the row\'s red',
     leave_text(2, lines=leave_lines(2, stop_after=2), extra="PANIC sched: a thread's leader is another process's, slot 0x0000000000000007\npanic: halt\n", end=False),
     ['--kind', 'leave', '--smp', '2'], set(), {'SMP-EXEC-LEAVE'}, why=r"the kernel said: \[.PANIC sched: a thread's leader is another process's")
case('leave: an exec round with the wrong status', leave_text(4, lines=leave_lines(4, exec_st='0xdead')),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'exec round 0: status 0xdead, want 0x900')
case('leave: an exec-kill round not killed', leave_text(4, lines=leave_lines(4, kill_st='0x900')),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'exec-kill round 0: status 0x900, want 0x9')
case('leave: a leader round with the wrong status', leave_text(4, lines=leave_lines(4, leader=('0xa00', '0x0', '0xa00', '0xa00'))),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'leader-exit round 1: status 0x0, want 0xa00')
case('leave: an exec-child line missing', leave_text(4, lines=leave_lines(4).replace('SMP-EXIT exec-child pid 64\n', '')),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'54 exec-child lines for 55 execs')
case('leave at 2: no exec-settle round\'s wait4 came back with the space still held (the window never opened)',
     leave_text(2, lines=leave_lines(2, settles=settle_lines(2, held=()))), ['--kind', 'leave', '--smp', '2'], set(),
     {'SMP-EXEC-LEAVE'}, why=r'NOT-FORCED: 0 of 20 exec-settle rounds opened at 2, want 5')
case('leave at 4: no exec-settle round held at its wait4: printed, not wanted (the siblings beside the exec are held too)',
     leave_text(4, lines=leave_lines(4, settles=settle_lines(4, held=()))), ['--kind', 'leave', '--smp', '4'],
     {'SMP-EXEC-LEAVE'}, set(), says=r'the space the exec left still held at the wait4 in 0 of 20')
case('leave at 2 says the rounds held at their wait4 and the settle\'s longest wait',
     leave_text(2), ['--kind', 'leave', '--smp', '2'], {'SMP-EXEC-LEAVE'}, set(),
     says=r'the space the exec left still held at the wait4 in 5 of 20, each settled reading within 64 kB of the '
          r'reading 500 ms on \(settled in at most 200 ms\)')
case('leave: an exec-settle round with a thread still current when the settle gave up',
     leave_text(4, lines=leave_lines(4, settles=settle_lines(4, left=(5,)))), ['--kind', 'leave', '--smp', '4'], set(),
     {'SMP-EXEC-LEAVE'}, why=r'exec-settle round 5: 1 of its threads still current on a processor 2000 ms after its wait4')
case('leave: no exec-settle rounds (a probe from before them)', leave_text(4, lines=leave_lines(4, settles='')),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'0 of 20 exec-settle')
case('leave: an exec-settle round with the wrong status', leave_text(4, lines=leave_lines(4, settles=settle_lines(4, st='0x0'))),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'exec-settle round 0: status 0x0, want 0x900')
case('leave: an exec-settle round with no MemFree readings', leave_text(4, lines=leave_lines(4, settles=settle_lines(4, keys=False))),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'},
     why=r'exec-settle round 0: no MemFree readings \(`waited-kb`, `settled-kb`, `late-kb`, `settle-ms`, `left`\)')
case('leave at 2 says in how many rounds the main thread was on an application processor at the exec',
     leave_text(2, lines=leave_lines(2, settles=settle_lines(2, mcpu=lambda r: -1 if r in (4, 9) else 1))),
     ['--kind', 'leave', '--smp', '2'], {'SMP-EXEC-LEAVE'}, set(),
     says=r'the main thread on an application processor at the exec in 18 of 20, the space the exec left still held at '
          r'the wait4 in 5 of 20')
case('leave at 2: the main thread never on an application processor at the exec (the window never opened)',
     leave_text(2, lines=leave_lines(2, settles=settle_lines(2, held=(), mcpu=lambda r: -1))),
     ['--kind', 'leave', '--smp', '2'], set(), {'SMP-EXEC-LEAVE'},
     why=r'NOT-FORCED: 0 of 20 exec-settle rounds opened at 2, want 5 .*\(the main thread on an application processor at '
         r'the exec in 0 of 20\)')
# At 2 the probe goes on past twenty exec-settle rounds until five have opened, sixty at most; fewer than five opened is
# NOT-FORCED, a named red: too few rounds held the old leader across the wait4 to judge the settle by (twenty boots under
# KVM at 2 opened 8 to 16 of 20 at 2ef2f9d6's fix head, one under TCG 2 of 20). At 4 the rounds stay twenty, the count
# printed.
case('leave at 2: the rounds go on past twenty until five have opened (here 26)',
     leave_text(2, lines=leave_lines(2, settles=settle_lines(2, rounds=26, held=(3, 9, 15, 21, 25)))),
     ['--kind', 'leave', '--smp', '2'], {'SMP-EXEC-LEAVE'}, set(), says=r'still held at the wait4 in 5 of 26')
case('leave at 2: NOT-FORCED when sixty rounds open four',
     leave_text(2, lines=leave_lines(2, settles=settle_lines(2, rounds=60, held=(1, 2, 3, 4)))),
     ['--kind', 'leave', '--smp', '2'], set(), {'SMP-EXEC-LEAVE'}, why=r'NOT-FORCED: 4 of 60 exec-settle rounds opened at 2, want 5')
case('leave at 2: more than sixty exec-settle rounds', leave_text(2, lines=leave_lines(2, settles=settle_lines(2, rounds=61))),
     ['--kind', 'leave', '--smp', '2'], set(), {'SMP-EXEC-LEAVE'}, why=r'61 of 20 to 60 exec-settle')
case('leave at 4: the exec-settle rounds stay twenty', leave_text(4, lines=leave_lines(4, settles=settle_lines(4, rounds=21))),
     ['--kind', 'leave', '--smp', '4'], set(), {'SMP-EXEC-LEAVE'}, why=r'21 of 20 exec-settle')
case('leave: an exec-settle round that does not say where the main thread was (a probe from before the look)',
     leave_text(4, lines=leave_lines(4, settles=settle_lines(4, mkey=False))), ['--kind', 'leave', '--smp', '4'], set(),
     {'SMP-EXEC-LEAVE'}, why=r'exec-settle round 0: no `main-cpu` \(where the main thread ran at the exec\), nor in rounds')


# --- the share kind (SMP-SHARE): N + 1 threads spin on N processors, each counting its own progress, three rounds of a
# second; each thread's part of a round's progress against the fair 1/(N + 1). A processor that kept one thread while the
# other two took turns on CPU 0 would give that thread 1/2 of the progress and the other two 1/4 each, 0.75 of fair. The
# looks (/proc/pax-cpus after each 10 ms sleep) are said as what they are: samples taken at timer wakes, which under a
# steady tick see the queue's turn at one phase (a fair boot under KVM at 2 saw one thread opposite the looker in every
# look while each made a third of the progress), never where a thread lives.
def share_lines(n, rounds=3, counts=None, looks=None, procs=None, done=True):
    out = ''
    for r in range(rounds):
        c = counts(r) if counts else [1000000] * (n + 1)
        out += f'SMP-SHARE round {r} threads {len(c)} processors {procs or n} looks 99 ms 1000\n'
        for i, ci in enumerate(c):
            lk = looks(r, i) if looks else [99 // (n + 1)] * n
            out += f'SMP-SHARE round {r} thread {i} count {ci} on ' + ','.join(f'{k}:{v}' for k, v in enumerate(lk)) + '\n'
        for k in range(procs or n):
            out += f'SMP-SHARE round {r} cpu {k} user +100 resched +0\n'
    return out + ('SMP-SHARE done\n' if done else '')


def share_text(n, lines=None, end=True):
    p = proc(n)
    t = head('share') + block('start', p) + active_line(n) + (lines if lines is not None else share_lines(n))
    return t + (block('end', p) + tail() if end else '')


KEPT = dict(counts=lambda r: [2000000, 1000000, 1000000], looks=lambda r, i: [0, 99] if i == 0 else [49, 0])
SH2 = ['--kind', 'share', '--smp', '2', '--host-cpus', '2']
case('share at 2 under KVM, a host CPU for each: fair, gated, green', share_text(2), SH2, {'SMP-SHARE'}, set(),
     says=r'^PASS SMP-SHARE smp=2 share: 3 rounds of 3 threads on 2 processors, every thread at least 1.00 of its fair share')
case('share at 2 under KVM: a processor that keeps one thread while the other two share CPU 0: red',
     share_text(2, lines=share_lines(2, **KEPT)), SH2, set(), {'SMP-SHARE'},
     why=r'round 0: thread 1 had 0.75 of its fair share of the progress \(1/3\), under 0.85; looks by processor 0:49,1:0')
case('share at 2: the looks are said as samples at timer wakes, by processor, beside the parts',
     share_text(2, lines=share_lines(2, **KEPT)), SH2, set(), {'SMP-SHARE'},
     says=r"^INFO SMP-SHARE smp=2 share: round 0: .* \[1.5, 0.75, 0.75\]; the looks \(samples at timer wakes, one phase of "
          r"the turn, not where a thread lives\) by processor \['0:0,1:99', '0:49,1:0', '0:49,1:0'\]")
case('share at 2 under TCG: printed, not gated', share_text(2, lines=share_lines(2, **KEPT)), SH2, {'SMP-SHARE'}, set(),
     meta=TCG, says=r"^PASS SMP-SHARE smp=2 share: .*0.75 of its fair share of the progress \(printed\).*tcg: not gated")
case('share at 4 on two host CPUs: printed, not gated',
     share_text(4, lines=share_lines(4, counts=lambda r: [2, 2, 2, 1, 1])), ['--kind', 'share', '--smp', '4', '--host-cpus', '2'],
     {'SMP-SHARE'}, set(), says=r'kvm: not gated: 4 processors on 2 host CPUs')
case('share: a thread with no progress is red, gated or not', share_text(2, lines=share_lines(2, counts=lambda r: [5, 0, 5])),
     SH2, set(), {'SMP-SHARE'}, meta=TCG, why=r'round 0: thread 1 made no progress')
case('share: two rounds and no done', share_text(2, lines=share_lines(2, rounds=2, done=False)), SH2, set(), {'SMP-SHARE'},
     why=r'2 of 3 rounds, no `SMP-SHARE done`')
case('share at 2 where one processor runs threads (stage 1)', share_text(2, lines=share_lines(2, procs=1, counts=lambda r: [1, 1])),
     SH2, set(), {'SMP-SHARE'}, why=r'round 0: 2 threads on 1 processors that run threads, want 3 on 2')


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
    for name, text, args, meta, dumps, files, passes, fails, why, says in cases:
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
        nm = td / 'nm.txt'
        if 'syms' in files:  # the ELF's symbols and these besides (a shipped kernel holding a test mark)
            nm = td / 'nm-case.txt'
            nm.write_text((td / 'nm.txt').read_text() + ''.join(f'{0xffffffff80600000:016x} {8:016x} B {k}\n' for k in files['syms']))
        r = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'rows.py'), str(s), *argv, '--symbols', str(nm)],
                           capture_output=True, text=True)
        got_pass = set(re.findall(r'^PASS (\S+)', r.stdout, re.M))
        got_fail = set(re.findall(r'^FAIL (\S+)', r.stdout, re.M))
        wrong = (passes - got_pass) | (fails - got_fail) | (got_fail - fails) | (passes & got_fail)
        code_ok = (r.returncode != 0) == bool(fails)
        why_ok = why is None or any(re.search(why, x) for x in re.findall(r'^FAIL .*$', r.stdout, re.M))
        says_ok = says is None or re.search(says, r.stdout, re.M) is not None
        if wrong or not code_ok or r.stderr or not why_ok or not says_ok:
            bad += 1
            print(f'FAIL ROWS-SELFTEST {name}: want pass {sorted(passes)} fail {sorted(fails)}'
                  f'{"" if why is None else f" by {why!r}"}{"" if says is None else f", saying {says!r}"}; '
                  f'got pass {sorted(got_pass)} fail {sorted(got_fail)} exit {r.returncode}')
            print(r.stdout + r.stderr)
        else:
            print(f'PASS ROWS-SELFTEST {name}: fails {sorted(got_fail) or "none"}')
print(f'rows-selftest: {len(cases) - bad} of {len(cases)} cases as expected')
sys.exit(1 if bad else 0)
