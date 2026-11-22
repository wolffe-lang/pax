"""SMP stage 2's rows: user code on every processor under one kernel lock.

  rows.py SERIAL --kind KIND --smp N [--cap C] [--boot K] [--scaling gate|report] [--host-cpus K]
          [--qemu-status S] [--expected JSON] [--elf KERNEL.elf | --symbols NM.txt]

SERIAL is one boot's transcript (tests/mpx6-smp boots tests/mpx6-smp.d/probe.c, or bench.c for
`build`); SERIAL.meta is tools/qemu-run's (its `accel:` line: a timed bound is gated under KVM alone
and printed under TCG); SERIAL.cmdK are the monitor's answers where the suite asked for register
dumps (`stop`, `info registers -a`, `cont`, three times: dumps in .cmd2, .cmd5, .cmd8); SERIAL.times
is build.py's host-observed batch times. --host-cpus is how many host CPUs the boot's QEMU had (the take's
`nproc`): a timed bound is gated only under KVM and only when the boot's processors fit them (N virtual
processors on fewer host threads cannot all run at once, whatever the kernel does); otherwise it is printed.

What stage 2 prints, and these rows read (the kernel's text is defined here):
  /proc/pax-cpus, after stage 1's head lines (`available`, `active`, `source`, `online-capable`,
  `disabled`, `started`, `idle`): `unlocked-allocations U`, the runtime's allocations made while no
  processor held the kernel lock (always 0). `active` is the processors that run threads. A line a
  processor:
    cpu 0 apic A boot current pid P|kernel|idle ticks T user U resched R kthreads K tlb S nmis N
    cpu I apic A runs current pid P|kernel|idle ticks T user U resched R kthreads K tlb S wakes W nmis N
    cpu I apic A idle current idle ticks T wakes W nmis N        (stage 1's: left out by pax.cpus=N)
    cpu I apic A stopped cause C rip 0x<R> | never entered | parked   (stage 1's)
  `user` this processor's ticks that interrupted ring 3; `resched` the RESCHED IPIs it took; `kthreads`
  its switches to a kernel thread (0 on every processor but CPU 0, which alone runs them); `tlb` the
  shootdown requests it answered; `pid` the running thread's id (gettid). /sys/devices/system/cpu/
  online `0-(N-1)`, sched_getaffinity N bits, sched_setaffinity accepted (0), /proc/self/status's
  `Cpus_allowed` the mask in hex and `Cpus_allowed_list` as online. At the end, after the processes
  are ended (`PAX: the end: …`) and before the end's own line (`user: <name> pid <p> reboot(2): …`):
    cpus: N application processors stopped for the end

The kinds and their rows (every row of the default kind starts with the gate `active N`):
  rows        SMP-ACTIVE   the real count everywhere user space reads it (above).
              SMP-RUN      N workers of one second of work each, three rounds, after one alone: every
                           processor's `user` ticks gain half the phase's ticks or more; N-1 processors
                           at least seen running a worker in the sampler's reads; each worker's CPU
                           time 0.8 of the lone worker's or more; statuses 0; under KVM the N-worker
                           wall 1.5 times the lone wall or less (minimum of three rounds each).
              SMP-TLB      B spins on a page on another processor: A's mprotect(PROT_NONE) makes B
                           fault (4 of 5 rounds within 1 ms under KVM), A's MAP_FIXED over the page
                           and a write of a new pattern leave B no stale read, a shootdown counted
                           (`tlb`) each time; B running elsewhere at each change.
              SMP-SIGNAL   SIGUSR1 and tgkill to a thread spinning elsewhere handled (8 of 9 within 2 ms
                           under KVM; tgkill on the thread it named), SIGKILL to the reaped status
                           (4 of 5 within 2 ms under KVM), SIGSTOP held and SIGCONT resumed.
              SMP-EXIT     exit_group from the main thread and from a sibling with four threads running,
                           execve from a sibling with the others running: statuses 0x700, 0x800,
                           0x900; min(4, N) of the group seen running at once; MemFree after four
                           exec rounds within 64 kB of before; no processor stopped.
              SMP-WAIT     16 children of 20 to 320 ms of work: 16 statuses right, the children's CPU
                           0.8 of the work or more, children seen on max(2, min(N, 16) - 1) processors.
  stress      SMP-LOCK     ten processes for SECS seconds (four fork-exit-wait loops, two pipe
                           ping-pongs, two futex ping-pong thread pairs, a map/protect/unmap churner
                           beside a reader thread, a signal storm): every count right, every status
                           0, every processor's `user` gained, `unlocked-allocations 0`, no PANIC, no
                           stopped processor, no slot on two processors, no program killed by a fault.
  end-halt, end-poweroff, end-reboot
              SMP-END      a spinner a processor, then root's reboot(2): the line above once, after
                           `PAX: the end:` and before the end's line; for halt, every application
                           processor halted (HLT=1) with interrupts off in the kernel in the last dump;
                           for power-off and restart, QEMU ended by itself (--qemu-status 0).
  nosmp       SMP-NOSMP    stage 1's `nosmp`: the boot line, `started 1`, `active 1`, the processors
                           outside the kernel (TCG: halted in pax_ap_park), and every other row
                           `NOT-ASKED … one processor: not asked`. A regression guard: green at stage 1.
  one         SMP-ONE      at -smp 1: no `cpus:` line, `started 1`, `active 1`; the rest not asked.
  cap2, cap1  SMP-CAP      `pax.cpus=C` at -smp N: `active C`, `started N`, online and the mask C
                           processors; processors C and up on stage 1's idle line, never running a
                           worker and gaining no `user` tick (cap2's one SMP-RUN round).
  build       SMP-BUILD    the census's pack fixture: one job and four jobs, three interleaved rounds, at
                           -smp 1 and -smp N; 15 pack/index pairs as the host oracle's; at -smp N the
                           gate `active N`, and with --scaling gate under KVM the four-job wall 1.6
                           times the one-job wall or less (minimum of three rounds each).

  every kind  SMP-KLOCK    no `PANIC klock: …` line (kernel/klock's checks; the door in `pax_interrupt`:
                           `klock: entered from ring 3 holding it`): red by that line verbatim, silent when green.
              SMP-DUP      no `PANIC sched: slot N running on two processors…` line (kernel/sched's `take_next`: a
                           slot the queue hands back that is RUNNING or still names a processor): red by
                           that line verbatim, silent when green.
              SMP-PIN      kernel threads run on CPU 0 alone: in every /proc/pax-cpus the boot printed, each
                           application processor's `runs` line says `kthreads 0`. Red naming the processor and
                           its count (or a `runs` line with no count); green when an application processor ran
                           threads; silent when none did.

A row prints `PASS ROW tag: …` or `FAIL ROW tag: …`, a row this boot does not ask `NOT-ASKED ROW
tag: …`, and what a red row found beyond its first reason `INFO ROW tag: …`. Exit 1 if any row failed.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True
KERNEL = 0xffffffff80000000
STOP_LINE = 'cpus: {n} application processors stopped for the end'
BAD = re.compile(r'^(PANIC .*|cpus: cpu \d+ stopped.*|.*running on two processors.*|.*did not answer a shootdown.*|'
                 r'user: \S+ pid \d+ killed: (?!SIGKILL|SIGTERM).*)$', re.M)
ROWS = ['SMP-ACTIVE', 'SMP-RUN', 'SMP-TLB', 'SMP-SIGNAL', 'SMP-EXIT', 'SMP-WAIT', 'SMP-LOCK', 'SMP-END', 'SMP-NOSMP',
        'SMP-ONE', 'SMP-CAP', 'SMP-BUILD']

ap = argparse.ArgumentParser()
ap.add_argument('serial')
ap.add_argument('--kind', required=True, choices=('rows', 'stress', 'end-halt', 'end-poweroff', 'end-reboot', 'nosmp',
                                                  'one', 'cap2', 'cap1', 'build'))
ap.add_argument('--smp', required=True, type=int)
ap.add_argument('--cap', type=int)
ap.add_argument('--boot', type=int)
ap.add_argument('--scaling', default='report', choices=('gate', 'report'))
ap.add_argument('--qemu-status', type=int)
ap.add_argument('--host-cpus', type=int, default=0, help='the host CPUs the boot had (0: not said)')
ap.add_argument('--expected')
ap.add_argument('--elf')
ap.add_argument('--symbols', help='`nm -S` output in a file, in place of --elf (rows-selftest)')
a = ap.parse_args()

N = a.smp
text = pathlib.Path(a.serial).read_text(errors='replace').replace('\r', '')
tag = f'smp={N}' + (f' cap={a.cap}' if a.cap else '') + (f' boot={a.boot}' if a.boot is not None else '') + \
    ('' if a.kind in ('rows', 'stress', 'build') else f' {a.kind}')
red = []


def fail(row, why, info=()):
    print(f'FAIL {row} {tag}: {why}')
    for x in info:
        print(f'INFO {row} {tag}: {x}')
    red.append(row)


def ok(row, what):
    print(f'PASS {row} {tag}: {what}')


def not_asked(rows, why):
    for r in rows:
        print(f'NOT-ASKED {r} {tag}: {why}')


def accel():
    p = pathlib.Path(f'{a.serial}.meta')
    m = re.search(r'^accel: (\w+)', p.read_text(errors='replace'), re.M) if p.exists() else None
    return m[1] if m else ''


KVM = accel() == 'kvm'
TIMED = KVM and (a.host_cpus == 0 or N <= a.host_cpus)
UNTIMED = '' if TIMED else (f'timed bounds printed, not gated: {N} processors on {a.host_cpus} host CPUs' if KVM else
                               f'timed bounds printed, not gated: {accel() or "no accelerator said"}')


# --- the probe's lines and /proc/pax-cpus ------------------------------------------------------
def lines(prefix):
    return re.findall(rf'^{prefix} (.*)$', text, re.M)


def proc(tagname):
    m = re.search(rf'^SMP-PROC {tagname} begin\n(.*?)^SMP-PROC {tagname} end$', text, re.M | re.S)
    if not m:
        return None
    body = m[1]
    head = {}
    for key in ('available', 'active', 'started', 'idle', 'unlocked-allocations'):
        mm = re.search(rf'^{key} (\d+)$', body, re.M)
        head[key] = int(mm[1]) if mm else None
    cpus = {}
    for mm in re.finditer(r'^cpu (\d+) apic (\d+) (boot|runs|idle|stopped|never entered|parked)(.*)$', body, re.M):
        rest = mm[4]
        cur = re.search(r'\bcurrent (pid (\d+)|idle|kernel)\b', rest)
        words = {k: int(v) for k, v in re.findall(r'\b(ticks|user|resched|kthreads|tlb|wakes|nmis) (\d+)\b', rest)}
        cpus[int(mm[1])] = dict(state=mm[3], cur=(int(cur[2]) if cur and cur[2] else (cur[1] if cur else None)),
                                words=words)
    head['cpus'] = cpus
    return head


def kv(s, key):
    """The value after `key ` in a probe line: an int, or the word as written (`-`, `yes`, `0x…`)."""
    m = re.search(rf'(?:^| ){re.escape(key)} (\S+)', s)
    if not m:
        return None
    v = m[1]
    return int(v) if re.fullmatch(r'-?\d+', v) else v


def cpu(v):
    return v if isinstance(v, int) and v >= 0 else None


def bad_lines():
    return [m[0] for m in BAD.finditer(text)]


def mask_hex(n):
    return format((1 << n) - 1, 'x')


def online(n):
    return '0' if n == 1 else f'0-{n - 1}'


# --- the register dumps ------------------------------------------------------------------------
def dumps():
    out = []
    for k in (2, 5, 8):
        p = pathlib.Path(f'{a.serial}.cmd{k}')
        if p.exists():
            out.append(p.read_text(errors='replace'))
    return out


def parse_dump(d):
    found = {}
    for part in re.split(r'^(?=CPU#\d+)', d, flags=re.M):
        m = re.match(r'CPU#(\d+)', part)
        if not m:
            continue
        r = {}
        for key, pat in (('rip', r'\b[RE]IP=([0-9a-f]+)'), ('hlt', r'\bHLT=([01])'), ('rfl', r'\b[RE]FL=([0-9a-f]+)')):
            mm = re.search(pat, part, re.M)
            r[key] = int(mm[1], 16) if mm else None
        found[int(m[1])] = r
    return found


def symbols():
    if a.symbols:
        out = pathlib.Path(a.symbols).read_text()
    else:
        out = ''
        for tool in ('nm', 'llvm-nm'):
            try:
                out = subprocess.run([tool, '-S', '--defined-only', a.elf], capture_output=True, text=True, check=True).stdout
                break
            except (OSError, subprocess.CalledProcessError, TypeError):
                continue
    syms = {}
    for ln in out.splitlines():
        f = ln.split()
        if len(f) == 4:
            syms[f[3]] = (int(f[0], 16), int(f[1], 16))
    return syms


# --- SMP-ACTIVE (and the one-processor and capped forms) ------------------------------------------
def active_facts(p, want_active, want_started, strict):
    """What SMP-ACTIVE checks, as a list of what is wrong; `strict` adds sched_setaffinity's answer."""
    why = []
    act = lines('SMP-ACTIVE')
    if p is None:
        return ['no /proc/pax-cpus read at the start (the probe died?)']
    if p['active'] != want_active or p['started'] != want_started:
        why.append(f'active {p["active"]} of {want_active}, started {p["started"]} of {want_started}')
    if not act:
        return why + ['no SMP-ACTIVE line']
    s = act[0]
    if str(kv(s, 'online')) != online(want_active):
        why.append(f'online {kv(s, "online")!r}, want {online(want_active)!r}')
    ret, mask = kv(s, 'affinity-ret'), kv(s, 'mask')
    if not isinstance(ret, int) or ret < 8 or mask != hex((1 << want_active) - 1):
        why.append(f'sched_getaffinity {ret} mask {mask}, want {hex((1 << want_active) - 1)}')
    if strict and kv(s, 'setaffinity-ret') != 0:
        why.append(f'sched_setaffinity {kv(s, "setaffinity-ret")}, want 0')
    if str(kv(s, 'cpus-allowed')) != mask_hex(want_active) or str(kv(s, 'cpus-allowed-list')) != online(want_active):
        why.append(f'status Cpus_allowed {kv(s, "cpus-allowed")} list {kv(s, "cpus-allowed-list")}, '
                   f'want {mask_hex(want_active)} and {online(want_active)}')
    return why


# --- SMP-RUN -------------------------------------------------------------------------------------
def run_rounds():
    rounds = {}
    for s in lines('SMP-RUN'):
        m = re.match(r'round (\d+) (.*)$', s)
        if not m:
            continue
        r = rounds.setdefault(int(m[1]), dict(samples=[]))
        rest = m[2]
        if rest.startswith('lone '):
            r['lone_wall'], r['lone_cpu'], r['lone_status'] = kv(rest, 'wall-us'), kv(rest, 'cpu-us'), kv(rest, 'status')
        elif rest.startswith('workers'):
            r['workers'] = [int(x) for x in rest.split()[1:]]
        elif rest.startswith('jobs '):
            r['jobs'], r['wall'] = kv(rest, 'jobs'), kv(rest, 'wall-us')
            c = kv(rest, 'cpu-us')
            r['cpus'] = [int(x) for x in str(c).split(',')] if c is not None else []
            r['bad'] = kv(rest, 'bad-status')
        elif rest.startswith('phase-ticks'):
            r['phase'] = kv(rest, 'phase-ticks')
            r['user'] = {int(i): (None if d == '-' else int(d)) for i, d in re.findall(r' (\d+):([+-]?\d+|-)', rest)}
        elif rest.startswith('sample'):
            r['samples'].append({int(i): v for i, v in re.findall(r' (\d+):(\S+)', rest)})
            sp = re.search(r' sampler (\d+)', rest)
            if sp:
                r.setdefault('sampler', set()).add(sp[1])
    return rounds


def run_check(n, nrounds, cap=None):
    """SMP-RUN's checks over its rounds (cap: processors cap and up must stay out of it)."""
    rounds = run_rounds()
    why, info = [], []
    if 'SMP-RUN done' not in text:
        why.append('no `SMP-RUN done` (the probe stopped inside the row)')
    if sorted(rounds) != list(range(nrounds)) or any('wall' not in r or 'lone_wall' not in r for r in rounds.values()):
        return why + [f'rounds {sorted(rounds)} incomplete, want {nrounds}'], info
    runners = cap or n
    for k, r in sorted(rounds.items()):
        if r['lone_status'] != '0x0' or r['bad'] != 0:
            why.append(f'round {k}: lone status {r["lone_status"]}, bad statuses {r["bad"]}')
        short = [c for c in r['cpus'] if c < 0.8 * r['lone_cpu']]
        if short or len(r['cpus']) != n:
            why.append(f'round {k}: workers\' CPU {r["cpus"]} us against the lone {r["lone_cpu"]} us (0.8 at least each)')
        phase = r.get('phase') or 0
        lows = [i for i in range(runners) if (r['user'].get(i) or 0) < phase / 2]
        if lows:
            why.append(f'round {k}: processors {lows} gained fewer than half the phase\'s {phase} ticks in ring 3: '
                       f'{ {i: r["user"].get(i) for i in sorted(r["user"])} }')
        workers = set(r.get('workers', []))
        seen = sorted({i for s in r['samples'] for i, v in s.items() if v.isdigit() and int(v) in workers})
        # the sampler reads on a processor of its own each time, which can never show a worker then
        sat = sorted({i for s in r['samples'] for i, v in s.items() if v in r.get('sampler', set())})
        info.append(f'round {k}: wall {r["wall"]} us against the lone {r["lone_wall"]} us '
                    f'({r["wall"] / max(r["lone_wall"], 1):.2f}x); workers seen on {seen}'
                    + (f' (the sampler on {sat})' if sat else ''))
        if cap:
            outside = [i for i in seen if i >= cap]
            gained = [i for i in range(cap, n) if (r['user'].get(i) or 0) > 0]
            if outside or gained:
                why.append(f'round {k}: processors past the cap ran workers {outside} or gained ring-3 ticks {gained}')
        elif len(seen) < n - 1:
            why.append(f'round {k}: workers seen running on {seen}, want {n - 1} processors at least')
    if not TIMED and not cap:
        info.append(UNTIMED)
    if TIMED and not cap:
        ratio = min(r['wall'] for r in rounds.values()) / max(min(r['lone_wall'] for r in rounds.values()), 1)
        if ratio > 1.5:
            why.append(f'{n} workers took {ratio:.2f} times one worker\'s wall (1.5 at most, minimum of {nrounds} rounds)')
    return why, info


# --- SMP-TLB -----------------------------------------------------------------------------------
def tlb_check():
    why, info = [], []
    prot = [s for s in lines('SMP-TLB') if s.startswith('protect ')]
    repl = [s for s in lines('SMP-TLB') if s.startswith('replace ')]
    if 'SMP-TLB done' not in text or len(prot) != 5 or len(repl) != 5:
        why.append(f'{len(prot)} protect and {len(repl)} replace rounds, want 5 each, and `SMP-TLB done`')
    fast = 0
    for s in prot + repl:
        b, c = cpu(kv(s, 'b-cpu')), cpu(kv(s, 'a-cpu'))
        if b is None or b == c:
            why.append(f'B not running on another processor at the change: {s}')
        d = kv(s, 'tlb')
        if not (isinstance(d, str) and re.fullmatch(r'\+\d+', d) and int(d) >= 1):
            why.append(f'no shootdown counted: {s}')
    for s in prot:
        if kv(s, 'faulted') != 'yes' or kv(s, 'mprotect') != 0:
            why.append(f'B read on past PROT_NONE: {s}')
        elif isinstance(kv(s, 'latency-us'), int) and kv(s, 'latency-us') <= 1000:
            fast += 1
    for s in repl:
        if kv(s, 'stale') != 0 or kv(s, 'fixed') != 'yes':
            why.append(f'B read the old page after the new one was written: {s}')
    if not TIMED:
        info.append(UNTIMED)
    if TIMED and prot and fast < 4:
        why.append(f'{fast} of {len(prot)} faults within 1 ms (4 at least)')
    info.append(f'protect latencies {[kv(s, "latency-us") for s in prot]} us')
    return why, info


# --- SMP-SIGNAL ----------------------------------------------------------------------------------
def signal_check():
    why, info = [], []
    sig = lines('SMP-SIGNAL')
    usr1 = [s for s in sig if s.startswith('usr1 ')]
    kill = [s for s in sig if s.startswith('kill ')]
    tgk = [s for s in sig if s.startswith('tgkill ')]
    stop = [s for s in sig if s.startswith('stop ')]
    tst = [s for s in sig if s.startswith('tgkill-status ')]
    if 'SMP-SIGNAL done' not in text or len(usr1) != 9 or len(kill) != 5 or len(tgk) != 9 or len(stop) != 1:
        why.append(f'usr1 {len(usr1)}, kill {len(kill)}, tgkill {len(tgk)}, stop {len(stop)}: want 9, 5, 9, 1 and '
                   '`SMP-SIGNAL done`')

    def elsewhere(s, who, me='p'):
        w, p = cpu(kv(s, f'{who}-cpu')), cpu(kv(s, f'{me}-cpu'))
        return w is not None and w != p

    for group, who, me in ((usr1, 'w', 'p'), (kill, 'w', 'p'), (tgk, 't', 'm')):
        away = [s for s in group if not elsewhere(s, who, me)]
        if away:
            why.append(f'the target not running on another processor when signalled: {away[0]} ({len(away)} so)')
    lost = [s for s in usr1 + tgk if not isinstance(kv(s, 'latency-us'), int)]
    if lost:
        why.append(f'a handler never ran: {lost[0]}')
    if any(kv(s, 'tid-ok') != 'yes' for s in tgk):
        why.append('tgkill handled on a thread it did not name')
    if any(kv(s, 'status') != '0x9' for s in kill):
        why.append(f'SIGKILL statuses {[kv(s, "status") for s in kill]}, want 0x9')
    if stop and (kv(stop[0], 'status') != '0x137f' or kv(stop[0], 'cont') is None or 'cont status 0xffff' not in stop[0]
                 or 'held yes' not in stop[0] or 'resumed yes' not in stop[0]):
        why.append(f'stop and continue: {stop[0]}')
    if tst and kv(tst[0], 'tgkill-status') != '0x0':
        why.append(f'the tgkill process ended {tst[0]}')
    if not TIMED:
        info.append(UNTIMED)
    if TIMED:
        for name, group, need in (('usr1', usr1, 8), ('kill', kill, 4), ('tgkill', tgk, 8)):
            n = sum(1 for s in group if isinstance(kv(s, 'latency-us'), int) and kv(s, 'latency-us') <= 2000)
            if group and n < need:
                why.append(f'{name}: {n} of {len(group)} within 2 ms ({need} at least)')
    for name, group in (('usr1', usr1), ('kill', kill), ('tgkill', tgk)):
        info.append(f'{name} latencies {[kv(s, "latency-us") for s in group]} us')
    return why, info


# --- SMP-EXIT ----------------------------------------------------------------------------------
def exit_check(n):
    why, info = [], []
    ex = lines('SMP-EXIT')
    grp = [s for s in ex if s.startswith('group ')]
    exe = [s for s in ex if s.startswith('exec ')]
    kids = [s for s in ex if s.startswith('exec-child ')]
    if 'SMP-EXIT done' not in text or len(grp) != 4 or len(exe) != 5:
        why.append(f'{len(grp)} group and {len(exe)} exec rounds, want 4 and 5, and `SMP-EXIT done`')
    want = min(4, n)
    for k, s in enumerate(grp):
        st = '0x700' if k < 2 else '0x800'
        if kv(s, 'status') != st:
            why.append(f'group round {k}: status {kv(s, "status")}, want {st}')
        if kv(s, 'running') != want:
            why.append(f'group round {k}: {kv(s, "running")} of its 4 threads seen running at once, want {want}')
    for k, s in enumerate(exe):
        if kv(s, 'status') != '0x900':
            why.append(f'exec round {k}: status {kv(s, "status")}, want 0x900 (the new program\'s exit)')
        if k and kv(s, 'running') != want:
            why.append(f'exec round {k}: {kv(s, "running")} of 4 seen running at once, want {want}')
    if len(kids) != len(exe):
        why.append(f'{len(kids)} exec-child lines for {len(exe)} execs')
    fr = [s for s in ex if s.startswith('frames-kb ')]
    if not fr or not isinstance(kv(fr[0], 'before'), int) or not isinstance(kv(fr[0], 'after'), int) \
            or kv(fr[0], 'before') == 0 or kv(fr[0], 'after') < kv(fr[0], 'before') - 64:
        why.append(f'MemFree around the four exec rounds: {fr[0] if fr else "no line"} (within 64 kB)')
    st = [s for s in ex if s.startswith('stopped')]
    if st != ['stopped none']:
        why.append(f'processors stopped: {st}')
    return why, info


# --- SMP-WAIT ----------------------------------------------------------------------------------
def wait_check(n):
    why = []
    w = lines('SMP-WAIT')
    s = next((x for x in w if x.startswith('statuses ')), None)
    if 'SMP-WAIT done' not in text or s is None:
        return ['no SMP-WAIT line, or no `SMP-WAIT done`'], []
    if kv(s, 'right') != 16:
        why.append(f'{kv(s, "right")} of 16 statuses right')
    if not isinstance(kv(s, 'cpu-us'), int) or kv(s, 'cpu-us') < 0.8 * kv(s, 'expected-us'):
        why.append(f'the children\'s CPU {kv(s, "cpu-us")} us against {kv(s, "expected-us")} us of work (0.8 at least)')
    seen = [int(x) for x in str(kv(s, 'cpus')).split(',') if x.isdigit()]
    need = max(2, min(n, 16) - 1)
    if len(seen) < need:
        why.append(f'children seen running on {seen}, want {need} processors at least')
    return why, [f'children seen on {seen}']


# --- the kinds ---------------------------------------------------------------------------------
p0 = proc('start')
if a.kind == 'rows':
    gate = None if p0 and p0['active'] == N and p0['started'] == N else \
        f'active {p0["active"] if p0 else None} of {N} (started {p0["started"] if p0 else None}): one processor runs threads'
    checks = [('SMP-ACTIVE', lambda: (active_facts(p0, N, N, True), [])), ('SMP-RUN', lambda: run_check(N, 3)),
              ('SMP-TLB', tlb_check), ('SMP-SIGNAL', signal_check), ('SMP-EXIT', lambda: exit_check(N)),
              ('SMP-WAIT', lambda: wait_check(N))]
    bad = bad_lines()
    for row, check in checks:
        why, info = check()
        if bad and row in ('SMP-EXIT', 'SMP-RUN'):
            why.append(f'the kernel said: {bad[:3]}')
        if gate and row != 'SMP-ACTIVE':
            fail(row, gate, why + info)
        elif why:
            fail(row, '; '.join(why[:6]), info)
        else:
            ok(row, '; '.join(info) if info else f'{N} processors run threads')
elif a.kind == 'stress':
    why = []
    gate = p0 and p0['active'] == N and p0['started'] == N
    if not gate:
        why.append(f'active {p0["active"] if p0 else None} of {N}: one processor runs threads')
    lk = lines('SMP-LOCK')
    names = [('forkwait', i) for i in range(4)] + [('pipe', i) for i in range(2)] + [('futex', i) for i in range(2)]
    for name, i in names:
        s = next((x for x in lk if re.match(rf'{name} {i} ', x)), None)
        if s is None or kv(s, 'wrong') != 0 or not kv(s, 'rounds'):
            why.append(f'{name} {i}: {s or "no line"}')
    s = next((x for x in lk if x.startswith('churn ')), None)
    if s is None or kv(s, 'wrong') != 0 or not kv(s, 'ops') or not kv(s, 'reader-reads'):
        why.append(f'churn: {s or "no line"}')
    s = next((x for x in lk if x.startswith('kill ')), None)
    if s is None or kv(s, 'lost') != 0 or not kv(s, 'sent') or kv(s, 'got') != kv(s, 'sent'):
        why.append(f'kill: {s or "no line"}')
    hung = [x for x in lk if x.startswith('component ') and ' hung ' in x]
    if hung:
        why.append(f'components hung past the deadline: {hung}')
    comp = [x for x in lk if x.startswith('component ') and ' hung ' not in x]
    if len(comp) != 10 or any(kv(x, 'status') != '0x0' for x in comp):
        why.append(f'component statuses: {[kv(x, "status") for x in comp]}')
    ut = next((x for x in lk if x.startswith('user-ticks')), '')
    gains = {int(i): d for i, d in re.findall(r' (\d+):(\S+)', ut)}
    idle = [i for i in range(N) if not re.fullmatch(r'\+\d+', gains.get(i, '-')) or int(gains[i]) < 1]
    if idle:
        why.append(f'processors {idle} gained no ring-3 tick in the stress: {gains}')
    ua = next((x for x in lk if x.startswith('unlocked-allocations-after ')), None)
    if ua is None or kv(ua, 'unlocked-allocations-after') != 0:
        why.append(f'allocations outside the kernel lock: {ua or "no line"}')
    if 'SMP-LOCK done' not in text:
        why.append('no `SMP-LOCK done` (the probe or the kernel stopped inside the stress)')
    bad = bad_lines()
    if bad:
        why.append(f'the kernel said: {bad[:3]}')
    if why:
        fail('SMP-LOCK', why[0], why[1:])
    else:
        ok('SMP-LOCK', f'ten processes, every count right; ring-3 ticks {gains}')
elif a.kind.startswith('end-'):
    why = []
    how = a.kind[4:]
    want = STOP_LINE.format(n=N - 1)
    tl = text.splitlines()
    at = [i for i, x in enumerate(tl) if x == want]
    the_end = [i for i, x in enumerate(tl) if x.startswith('PAX: the end:')]
    end_line = [i for i, x in enumerate(tl) if re.match(r'^user: \S+ pid \d+ reboot\(2\): ', x)]
    sp = next((x for x in lines('SMP-END') if x.startswith('spinners ')), None)
    seen = [int(x) for x in str(kv(sp, 'cpus') if sp else '').split(',') if x.isdigit()]
    if len(seen) < N - 1:
        why.append(f'spinners seen running on {seen} before the end, want {N - 1} processors at least')
    if len(at) != 1:
        why.append(f'{len(at)} lines {want!r}, want one')
    elif not end_line or not (at[0] < end_line[0]) or (the_end and not the_end[-1] < at[0]):
        why.append(f'the stop line at {at[0]}, `PAX: the end:` at {the_end}, the end\'s line at {end_line}: want after '
                   'the first, before the second')
    if how == 'halt':
        ds = [parse_dump(d) for d in dumps()]
        last = ds[-1] if ds else {}
        wrong = [(k, hex(c.get('rip') or 0), c.get('hlt'), hex(c.get('rfl') or 0)) for k, c in sorted(last.items())
                 if k and not (c.get('hlt') == 1 and c.get('rfl') is not None and not c['rfl'] & 0x200
                               and (c.get('rip') or 0) >= KERNEL)]
        if not ds or len(last) != N or wrong:
            why.append(f'application processors not halted with interrupts off in the kernel: {wrong or len(last)}')
    elif a.qemu_status != 0:
        why.append(f'QEMU ended with status {a.qemu_status} (0: the machine {"powered off" if how == "poweroff" else "reset"})')
    bad = bad_lines()
    if bad:
        why.append(f'the kernel said: {bad[:3]}')
    if why:
        fail('SMP-END', why[0], why[1:])
    else:
        ok('SMP-END', f'{want}, between the processes\' end and the end\'s line ({how})')
elif a.kind in ('nosmp', 'one', 'cap1'):
    row = {'nosmp': 'SMP-NOSMP', 'one': 'SMP-ONE', 'cap1': 'SMP-CAP'}[a.kind]
    started = N if a.kind == 'cap1' else 1
    why = active_facts(p0, 1, started, False)
    boot = re.findall(r'^cpus: .*$', text, re.M)
    if a.kind == 'nosmp':
        want = f'cpus: application processors left parked {N - 1} of {N - 1} (nosmp)'
        if boot != [want]:
            why.append(f'boot lines {boot}, want [{want!r}]')
        ds = [parse_dump(d) for d in dumps()]
        lo, size = symbols().get('pax_ap_park', (0, 0)) if accel() == 'tcg' else (0, 0)
        if not ds or len(ds[0]) != N:
            why.append(f'register dumps: {len(ds)}, processors in the first: {len(ds[0]) if ds else 0}')
        else:
            inside = [k for k, c in sorted(ds[0].items()) if k and (c['rip'] is None or c['rip'] >= KERNEL)
                      and not (lo <= (c['rip'] or 0) < lo + size and c['hlt'] == 1 and c['rfl'] is not None
                               and not c['rfl'] & 0x200)]
            if inside:
                why.append(f'application processors in the kernel: {inside}')
    elif a.kind == 'one':
        if boot:
            why.append(f'boot lines {boot}, want none')
    else:
        cpus = p0['cpus'] if p0 else {}
        idle = [i for i in range(1, N) if cpus.get(i, {}).get('state') != 'idle' or cpus[i]['cur'] != 'idle']
        if idle:
            why.append(f'processors past the cap not idle in PAX: {[(i, cpus.get(i)) for i in idle]}')
    if 'SMP-PROBE done' not in text:
        why.append('no `SMP-PROBE done`')
    if why:
        fail(row, why[0], why[1:])
    else:
        ok(row, {'nosmp': f'{N - 1} left parked, started 1, active 1', 'one': 'no cpus: line, started 1, active 1',
                 'cap1': f'active 1, {N - 1} processors idle in PAX'}[a.kind])
    not_asked([r for r in ROWS if r != row], 'one processor: not asked')
elif a.kind == 'cap2':
    c = a.cap or 2
    why = active_facts(p0, c, N, True)
    cpus = p0['cpus'] if p0 else {}
    past = [i for i in range(c, N) if cpus.get(i, {}).get('state') != 'idle']
    if past:
        why.append(f'processors past the cap not on the idle line: {[(i, cpus.get(i)) for i in past]}')
    rw, info = run_check(N, 1, cap=c)
    why += rw
    if why:
        fail('SMP-CAP', why[0], why[1:] + info)
    else:
        ok('SMP-CAP', f'active {c} of {N}; {"; ".join(info)}')
elif a.kind == 'build':
    why = []
    act = re.findall(r'^BENCH ACTIVE (\S+)$', text, re.M)
    if N > 1 and (not act or act[0] != str(N)):
        why.append(f'active {act[0] if act else None} of {N}: one processor runs the jobs')
    out = re.findall(r'^OUTPUT (\S+) (\S+) trailer-sha1=([0-9a-f]{40})$', text, re.M)
    expected = json.loads(pathlib.Path(a.expected).read_text()) if a.expected else {}
    wrong = [o for o in out if expected.get(o[1]) != o[2]]
    if len(out) != 30 or wrong or len(expected) != 2:
        why.append(f'{len(out)} outputs (want 30), {len(wrong)} not the oracle\'s: {wrong[:2]}')
    tp = pathlib.Path(f'{a.serial}.times')
    times = json.loads(tp.read_text()) if tp.exists() else []
    one = [t for _r, j, t in times if j == 1]
    four = [t for _r, j, t in times if j == 4]
    if 'BENCH DONE' not in text or len(one) != 3 or len(four) != 3:
        why.append(f'batches timed: {len(one)} of one job, {len(four)} of four (3 each), BENCH DONE '
                   f'{"seen" if "BENCH DONE" in text else "missing"}')
        ratio = None
    else:
        ratio = min(four) / min(one)
    guest = re.findall(r'^BENCH END round=(\d+) jobs=(\d+) .*guest_wall_us=(\d+)', text, re.M)
    fig = (f'one job {min(one) * 1000:.0f} ms, four jobs {min(four) * 1000:.0f} ms (host, minimum of three), '
           f'{ratio:.2f}x; guest walls {[(int(j), int(w) // 1000) for _r, j, w in guest]} ms') if ratio else 'no figures'
    if N > 1 and ratio is not None:
        if a.scaling == 'gate' and not TIMED:
            why.append(f'the scaling bound is asked where it cannot hold ({UNTIMED})')
        elif a.scaling == 'gate' and ratio > 1.6:
            why.append(f'four jobs took {ratio:.2f} times one job\'s wall (1.6 at most)')
    if why:
        fail('SMP-BUILD', why[0], why[1:] + [fig])
    else:
        ok('SMP-BUILD', fig + ('' if a.scaling == 'gate' or N == 1 else '; the 1.6 bound is the scaling hold\'s (reported)'))

# Every kind: the kernel lock's door (kernel/interrupts' `pax_interrupt`) panics when a processor comes in from
# ring 3 still holding the lock; that line, verbatim, is SMP-KLOCK's red (the lock plant's name). Silent when green.
klock = [ln.strip() for ln in re.findall(r'^PANIC klock: .*$', text, re.M)]
if klock:
    fail('SMP-KLOCK', klock[0], klock[1:])

# Every kind: kernel/sched's duplicate-running check (`take_next`) panics on a slot the run queue hands back that
# a processor still runs; that line, verbatim, is SMP-DUP's red (the W_CPU plant's name). Silent when green.
dup = [ln.strip() for ln in re.findall(r'^PANIC sched: slot \d+ running on two processors.*$', text, re.M)]
if dup:
    fail('SMP-DUP', dup[0], dup[1:])

# Every kind: kernel threads run on CPU 0 alone (stage 2's amendment to its contract's §3.6). Every
# /proc/pax-cpus the boot printed is read: an application processor's `runs` line must say `kthreads 0`
# (the count is cumulative, so the last read has the most). Green when one ran threads, silent when none did.
kseen, kmiss = {}, set()
for blk in re.finditer(r'^SMP-PROC (\S+) begin\n(.*?)^SMP-PROC \1 end$', text, re.M | re.S):
    for mm in re.finditer(r'^cpu (\d+) apic \d+ runs (.*)$', blk[2], re.M):
        if int(mm[1]) == 0:
            continue
        k = re.search(r'\bkthreads (\d+)\b', mm[2])
        if k:
            kseen[int(mm[1])] = max(kseen.get(int(mm[1]), 0), int(k[1]))
        else:
            kmiss.add(int(mm[1]))
if kmiss:
    fail('SMP-PIN', f'application processors {sorted(kmiss)} on a `runs` line with no kthreads count')
elif any(kseen.values()):
    fail('SMP-PIN', 'kernel threads ran on application processors: ' +
         ', '.join(f'cpu {i} kthreads {k}' for i, k in sorted(kseen.items()) if k))
elif kseen:
    ok('SMP-PIN', f'no kernel thread on application processors {sorted(kseen)} (kthreads 0 each)')

sys.exit(1 if red else 0)
