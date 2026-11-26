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
  `disabled`, `started`, `idle`), then `heap-started 0|1`, whether the kernel's heap was started (the
  console kernel starts none: 0). `active` is the processors that run threads. A line a
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
                           wall 1.5 times the lone wall or less (minimum of three rounds each). The ring-3
                           ticks and the processors seen are held only where N fits the host's CPUs
                           (--host-cpus), under KVM or TCG; otherwise printed with the reason. The CPU
                           share is held where the timed bounds are (KVM, N fitting the host's CPUs):
                           the work is a loop count calibrated at boot, so its CPU time is the
                           processor's speed at the time, and under TCG the guest's TSC follows the
                           host's clock (on a shared host the lone worker read 361, 889 and 475 ms for
                           one second of work in one boot); elsewhere it is printed with the reason.
              SMP-TLB      B spins on a page on another processor: A's mprotect(PROT_NONE) makes B
                           fault (4 of 5 rounds within 1 ms under KVM), A's MAP_FIXED over the page
                           and a write of a new pattern leave B no stale read and no SIGSEGV (a fault
                           in the replacement's window runs again once routed), a shootdown counted
                           (`tlb`) each time; B running elsewhere at each change.
              SMP-SIGNAL   SIGUSR1 and tgkill to a thread spinning elsewhere handled (8 of 9 within 2 ms
                           under KVM; tgkill on the thread it named), SIGKILL to the reaped status
                           (4 of 5 within 2 ms under KVM), SIGSTOP held and SIGCONT resumed; every
                           processor a target was signalled on took a RESCHED across the row (`resched`
                           before and after: the raise paths' RESCHED, on both accelerators); the sleeper,
                           a SIGUSR1 to a process whose main thread blocks it and spins, taken by its
                           sleeping second thread, thirty times: under KVM every one within 5 ms and 27 of
                           30 within 2 ms, each latency and the worst printed; and twenty rounds of ten sent
                           5 ms apart with the main thread asleep between (tests/mpx3-threads' takers): under
                           KVM every round ten taken, each within 5 ms of its send (a pending signal ends the
                           sleep at once), with the kernel's signal counts printed (set, merged, taken, sleeps
                           entered with one pending).
              SMP-EXIT     exit_group from the main thread and from a sibling with four threads running,
                           execve from a sibling with the others running: statuses 0x700, 0x800,
                           0x900; min(4, N) of the group seen running at once; MemFree after four
                           exec rounds within 64 kB of before, each read once the round's threads are
                           off every processor and a wait4 with no child has run the kernel's reap
                           (what each round's settle gave back printed); no processor stopped.
              SMP-WAIT     16 children of 20 to 320 ms of work: 16 statuses right, the children's CPU
                           0.8 of the work or more (held where SMP-RUN's CPU share is), and the children
                           ran on max(2, min(N, 16) - 1)
                           processors by the kernel's ring-3 ticks (two at least each), the ones missed
                           printed on every boot; the sampler's sightings, each processor's RESCHEDs
                           over the window, where the sampler sat and each processor's idle reads
                           printed, not judged.
  stress      SMP-LOCK     ten processes for SECS seconds (four fork-exit-wait loops, two pipe
                           ping-pongs, two futex ping-pong thread pairs, a map/protect/unmap churner
                           beside a reader thread, a signal storm): every count right, every status
                           0, every processor's `user` gained, no PANIC, no
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
  one, nosmp, cap1
              SMP-REFUSE   the faults the page tables refuse are refused still (kernel/vm runs a fault again only when
                           its page is present at routing and allows the access): a write to a read-only page, a
                           fetch from a page without PROT_EXEC and a read of the kernel's half each end the child in
                           its SIGSEGV handler (`refused yes status 0xb00`).
  cap2        SMP-DEAD     three exit_groups from a group's main thread with its siblings spinning, one on the
                           other processor that runs threads: status 0x700 each within 2 s, and none of the
                           group's threads current on any processor in ten looks after (kernel/sched's
                           `preempt` and `kick` switch a thread ended in place off, never queue it again).
  cap2, cap1  SMP-CAP      `pax.cpus=C` at -smp N: `active C`, `started N`, online and the mask C
                           processors; processors C and up on stage 1's idle line, never running a
                           worker and gaining no `user` tick (cap2's one SMP-RUN round).
  trace       SMP-TRACE-EXIT ten rounds, spinning and in a system-call loop in turn, of a traced group (TRACECLONE and
                           TRACEEXIT) whose second thread runs on another processor when its leader calls exit_group:
                           both threads' PTRACE_EVENT_EXIT stops (0x6057f) reported within 2 s; the thread then makes
                           no spin in the 20 ms after its stop is reported and is current on no processor (stopped
                           means stopped); both deaths (0x2500) within 2 s of the CONTs, then ECHILD. At two
                           processors or more the thread is seen on another processor before each exit (the case set
                           up). Bounded everywhere: a round that misses is named, its group SIGKILLed and reaped.
              SMP-TRACE-INT  nine PTRACE_INTERRUPTs of a seized tracee spinning on another processor: each a
                           PTRACE_EVENT_STOP (0x80057f), the tracee running again 20 ms after its CONT; under KVM 8 of 9
                           stopped within 2 ms (a tracee told nothing stops at its processor's next tick, 10 ms).
                           Not asked at one processor.
              SMP-STOPWRITE  24 rounds of SIGSTOP to a process writing a pipe a byte a call (20 us apart) on another
                           processor: a write already in progress when the stop comes completes (Linux allows it), and
                           the stop takes effect before ring 3, so at most one byte follows the stop, never two (the
                           rounds drained at once); none, and no ring-3 turn, once it has taken effect (the rounds
                           drained 50 ms on); each stop and continue reported (0x137f, 0xffff), the writer writing
                           again after SIGCONT. At two processors or more the writer is seen on another processor
                           before each stop (the case set up; looked for up to 2 s, the looks printed, a round never
                           set up named). mpx5-jobs' `SIGSTOP to it: it runs on` is this case,
                           met once in a while.
  build       SMP-BUILD    the census's pack fixture: one job and four jobs, three interleaved rounds, at
                           -smp 1 and -smp N; 15 pack/index pairs as the host oracle's; at -smp N the
                           gate `active N`, and with --scaling gate under KVM the four-job wall 1.6
                           times the one-job wall or less (minimum of three rounds each).
  The test build's kinds (tools/build-kernel --test-words: tests/mpx6-smp.d/testwords.lu in kernel/testwords' place;
  never a shipped kernel) and the shipped kernel's answer to the same words:
  end-nooff   SMP-END-NOOFF  `pax.cpus=4 pax.nopoweroff` at 4: root's power-off answered `poweroff: not done
                           (pax.nopoweroff, a test kernel)`, the stop line once between `PAX: the end:` and the end's
                           line, and every application processor halted with interrupts off in the kernel in the last
                           dump (the end's halt, not QEMU's power-off).
  panic       SMP-PANIC-STOP `pax.panictest=1` at 4, four spinners running: 3 s after CPU 0's ticks begin, op 3 to CPU 1,
                           which panics in its answer: the text `PANIC testwords: a test panic, cpu ` once; under KVM
                           no `cpus: cpu K did not stop for the panic` line and every processor halted with interrupts
                           off in the kernel in the last dump (printed under TCG).
  panic2      SMP-PANIC-TWO  `pax.panictest=2`: op 3 to CPUs 1 and 2 at once: the owner's text once and the second's
                           (`(a second panic, cpu K's first): testwords: a test panic`) once, each whole (texts, not
                           lines: kernel/panic's print token serializes them, but its wait is bounded); the rest as
                           SMP-PANIC-STOP.
  testwords   SMP-TESTWORDS  the shipped kernel given `pax.nopoweroff pax.panictest=2`: each word ignored by name
                           (`testwords: W ignored (not a test kernel)`), root's power-off powers off (QEMU's status 0),
                           no PANIC, and neither `testwords.fire` nor `testwords.test_panic` in its ELF (the suite's
                           TESTWORDS-ELF also holds both present in the test build).
  leave       SMP-EXEC-LEAVE the test build given `pax.slowleave=MS` (`testwords: pax.slowleave=MS (a test kernel)…`):
                           an application processor that comes in from ring 3 with its thread ended in place gives the
                           lock back and holds MS ms before it switches that thread off (`testwords: a slow leave, cpu
                           K, slot S, tgid T`), what a host that has not run that processor does; one hold at least of a
                           thread with a tgid (one charged at its switch-off). The probe's `SMP-LEAVE KIND R status
                           S running M of 4` rounds: 4 leader-exit (the main thread exits alone, a sibling then calls
                           exit_group(10): 0xa00), 30 exec (a sibling execs a program that exits 9: 0x900), 5
                           exec-kill (the exec'd program killed by its own SIGKILL: 0x9), 20 exec-settle (at 2 on
                           past twenty until five have opened, sixty at most; 0x900, the main thread saying go once a
                           look shows it current on an application processor beside the exec'ing sibling: `waited-kb W
                           settled-kb S late-kb L settle-ms MS left K main-cpu C`),
                           `SMP-LEAVE done`; an `SMP-EXIT exec-child pid P` line for every exec; one hold at least;
                           each exec-settle round's settled MemFree (SMP-EXIT's settle) within 64 kB of its reading
                           500 ms on, with no thread of it still current, and where the main thread ran at the exec
                           said; at 2, five rounds at least whose wait4 came back with the space the exec left still
                           held (the old leader held on the application processor), fewer a red of its own name,
                           NOT-FORCED; no PANIC (an exec'd leader
                           collected while an ended sibling still ran: `sched: no process area for slot`).

  every kind  SMP-KLOCK    no `PANIC klock: …` line (kernel/klock's checks; the door in `pax_interrupt`:
                           `klock: entered from ring 3 holding it`): red by that line verbatim, silent when green.
              SMP-DUP      no `PANIC sched: slot N running on two processors…` line (kernel/sched's `take_next`: a
                           slot the queue hands back that is RUNNING or still names a processor): red by
                           that line verbatim, silent when green.
              SMP-NOHEAP   no allocation on any processor, locked or not: every /proc/pax-cpus the boot printed
                           says `heap-started 0` (the kernel's heap was never started, so the runtime can allocate
                           nothing) and no `PANIC heap: …` line (an allocation anyway panics by name, `heap: alloc
                           before heap.start`). Red by that line verbatim, or by a read that says otherwise or
                           nothing; green when a read was printed, silent when none was.
              SMP-PIN      kernel threads run on CPU 0 alone: in every /proc/pax-cpus the boot printed, each
                           application processor's `runs` line says `kthreads 0`. Red naming the processor and
                           its count (or a `runs` line with no count); green when an application processor ran
                           threads; silent when none did.
              SMP-PARK     kmain_console's own check of exec's parked-space table: `sched: parked spaces: 2 held
                           parked at once, 0 left once let go`; red on another count or the table's PANIC.

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
        'SMP-ONE', 'SMP-CAP', 'SMP-DEAD', 'SMP-PARK', 'SMP-END-NOOFF', 'SMP-PANIC-STOP', 'SMP-PANIC-TWO',
        'SMP-TESTWORDS', 'SMP-REFUSE', 'SMP-BUILD', 'SMP-TRACE-EXIT', 'SMP-TRACE-INT', 'SMP-STOPWRITE',
        'SMP-EXEC-LEAVE']

ap = argparse.ArgumentParser()
ap.add_argument('serial')
ap.add_argument('--kind', required=True, choices=('rows', 'stress', 'end-halt', 'end-poweroff', 'end-reboot', 'nosmp',
                                                  'one', 'cap2', 'cap1', 'build', 'end-nooff', 'panic', 'panic2',
                                                  'testwords', 'trace', 'leave'))
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
# The CPU shares (SMP-RUN's each worker 0.8 of the lone, SMP-WAIT's children 0.8 of their work) are held where the
# timed bounds are: fixed work's CPU time is the processor's speed, and under TCG the guest's TSC follows the host's clock.
SHARES = '' if TIMED else (f'kvm: not gated: {N} processors on {a.host_cpus} host CPUs' if KVM else
                           f'{accel() or "no accelerator said"}: not gated: CPU time of fixed work follows the host\'s speed under TCG')
# every run says its accelerator and the host's processors (--host-cpus: the take's nproc; 0 when not given)
print(f'INFO SMP-HOST {tag}: accel {accel() or "not said"}, {a.host_cpus or "unknown"} host CPUs for {N} processors; '
      f'timed bounds and CPU shares {"gated" if TIMED else "printed, not gated"}')


# --- the probe's lines and /proc/pax-cpus ------------------------------------------------------
def lines(prefix):
    return re.findall(rf'^{prefix} (.*)$', text, re.M)


def proc(tagname):
    m = re.search(rf'^SMP-PROC {tagname} begin\n(.*?)^SMP-PROC {tagname} end$', text, re.M | re.S)
    if not m:
        return None
    body = m[1]
    head = {}
    for key in ('available', 'active', 'started', 'idle'):
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


def bad_lines(ending=False):
    # ending: a boot that runs the end (the end kinds, testwords). There a program killed by SIGHUP between the probe's
    # `SMP-END asking reboot(2)` and `PAX: the end:` is the end's own: pid 1, the controlling process, ends first and
    # its terminal's hangup sends its foreground group SIGHUP, taken before their SIGTERM (a lower number first)
    lo, hi = (text.find('SMP-END asking reboot(2)'), text.find('PAX: the end:')) if ending else (-1, -1)
    return [m[0] for m in BAD.finditer(text)
            if not (0 <= lo < m.start() < hi and re.match(r'user: \S+ pid \d+ killed: SIGHUP\b', m[0]))]


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
    # two checks depend on the host running every virtual processor at once (each processor's ring-3 ticks, workers
    # seen on N-1 processors): held only where the processors that run threads fit the take's host CPUs (--host-cpus;
    # unknown counts as fitting), under KVM or TCG alike; otherwise printed with the reason (the hosted job: 16 under
    # TCG on a four-thread runner)
    fits = a.host_cpus == 0 or runners <= a.host_cpus
    loose = []
    for k, r in sorted(rounds.items()):
        if r['lone_status'] != '0x0' or r['bad'] != 0:
            why.append(f'round {k}: lone status {r["lone_status"]}, bad statuses {r["bad"]}')
        short = [c for c in r['cpus'] if c < 0.8 * r['lone_cpu']]
        if short or len(r['cpus']) != n:
            share = f'round {k}: workers\' CPU {r["cpus"]} us against the lone {r["lone_cpu"]} us (0.8 at least each)'
            if TIMED or len(r['cpus']) != n:
                why.append(share)
            else:
                info.append(f'{share}; {SHARES}')
        phase = r.get('phase') or 0
        lows = [i for i in range(runners) if (r['user'].get(i) or 0) < phase / 2]
        if lows:
            (why if fits else loose).append(f'round {k}: processors {lows} gained fewer than half the phase\'s {phase} '
                                            f'ticks in ring 3: { {i: r["user"].get(i) for i in sorted(r["user"])} }')
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
            (why if fits else loose).append(f'round {k}: workers seen running on {seen}, want {n - 1} processors at least')
    if loose:
        info.append(f'host-dependent checks printed, not gated: {runners} processors on {a.host_cpus} host CPUs: '
                    + '; '.join(loose))
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
        # three reasons, each its own: B's SIGSEGV (`b-fault yes`: a fault on the page A replaced, refused when it was
        # routed although the new page was present by then; B's thread ends in its handler, so no count follows), a
        # stale read (a count above 0: B saw the old page after the new one was written), or no count at all
        if kv(s, 'b-fault') == 'yes':
            why.append(f'B took SIGSEGV on a page present at routing: {s}')
        elif isinstance(kv(s, 'stale'), int) and kv(s, 'stale') > 0:
            why.append(f'B read the old page after the new one was written: {s}')
        elif kv(s, 'stale') != 0:
            why.append(f'B never finished its reads of the new page: {s}')
        if kv(s, 'fixed') != 'yes':
            why.append(f'MAP_FIXED did not replace the page: {s}')
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
    # the sleeper: a SIGUSR1 to a process whose main thread blocks it, which only its sleeping second thread may take
    # (tests/mpx3-threads' takers), sent while the main thread spins; then ten 5 ms apart with it asleep between
    slp = [s for s in sig if s.startswith('sleeper ')]
    ten = [s for s in sig if s.startswith('sleeper-ten round ')]
    sst = [s for s in sig if s.startswith('sleeper-status ')]
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
    # SIGSTOP held: the target's spins stand still for 30 ms after its stop status (`held no`: it ran on, the stop
    # never parked it; kernel/sched parks it when its processor next switches, so a processor that returned to it
    # because nothing else was queued is this red)
    if stop and 'held no' in stop[0]:
        why.append(f'SIGSTOP not held: the target spun on after its stop status: {stop[0]}')
    if stop and (kv(stop[0], 'status') != '0x137f' or kv(stop[0], 'cont') is None or 'cont status 0xffff' not in stop[0]
                 or 'resumed yes' not in stop[0] or 'held' not in stop[0]):
        why.append(f'stop and continue: {stop[0]}')
    if tst and kv(tst[0], 'tgkill-status') != '0x0':
        why.append(f'the tgkill process ended {tst[0]}')
    if len(slp) != 30 or len(ten) != 20 or len(sst) != 1:
        why.append(f'sleeper {len(slp)}, sleeper-ten rounds {len(ten)}, sleeper-status {len(sst)}: want 30, 20, 1')
    if any(not isinstance(kv(s, 'latency-us'), int) for s in slp):
        why.append(f'a sleeping thread\'s handler never ran: {[s for s in slp if not isinstance(kv(s, "latency-us"), int)][0]}')
    if sst and kv(sst[0], 'sleeper-status') != '0x0':
        why.append(f'the sleeper process ended {sst[0]}')
    # step 5's witness: every processor a target was signalled on (not the sender's) took a RESCHED in the row
    rs = [s for s in sig if s.startswith('resched')]
    gains = {int(a): int(b) for a, b in re.findall(r'(\d+):(\d+)', rs[0])} if rs else {}
    targets = sorted({cpu(kv(s, f'{who}-cpu')) for group, who, me in ((usr1, 'w', 'p'), (kill, 'w', 'p'), (tgk, 't', 'm'))
                      for s in group if elsewhere(s, who, me)} - {None})
    quiet = [c for c in targets if gains.get(c, 0) <= 0]
    if targets and (not rs or quiet):
        why.append(f'the target processors {quiet or targets} took no RESCHED across the row (the raise paths\' RESCHED): '
                   f'`resched` gains {gains if rs else "missing"}')
    elif rs:
        info.append(f'RESCHEDs taken across the row: {gains}')
    if not TIMED:
        info.append(UNTIMED)
    if TIMED:
        for name, group, need in (('usr1', usr1, 8), ('kill', kill, 4), ('tgkill', tgk, 8)):
            n = sum(1 for s in group if isinstance(kv(s, 'latency-us'), int) and kv(s, 'latency-us') <= 2000)
            if group and n < need:
                why.append(f'{name}: {n} of {len(group)} within 2 ms ({need} at least)')
        # the sleeper woken where it can run, judged on its distribution: every one within 5 ms (the takers' send
        # interval: a wake later than that is a SIGUSR1 still pending when the next comes) and 27 of 30 within 2 ms
        lat = [kv(s, 'latency-us') for s in slp if isinstance(kv(s, 'latency-us'), int)]
        if lat and max(lat) > 5000:
            why.append(f'sleeper: the worst {max(lat)} us, beyond the 5 ms between the takers\' sends: a sleeping thread woken late')
        n = sum(1 for x in lat if x <= 2000)
        if slp and n < 27:
            why.append(f'sleeper: {n} of {len(slp)} within 2 ms (27 at least): a sleeping thread woken late')
    for name, group in (('usr1', usr1), ('kill', kill), ('tgkill', tgk), ('sleeper', slp)):
        info.append(f'{name} latencies {[kv(s, "latency-us") for s in group]} us')
    lat = [kv(s, 'latency-us') for s in slp if isinstance(kv(s, 'latency-us'), int)]
    if lat:
        info.append(f'the sleeper\'s worst {max(lat)} us')
    if ten:
        # ten sent 5 ms apart, twenty rounds, each with the worst send-to-handler time and the kernel's signal counts
        # across it (set, merged into one pending, taken, sleeps entered with one pending). A pending signal ends the
        # sleeper's interruptible sleep at once, so each is handled long before the next is sent and none merges: a
        # round short of ten, or one handled 5 ms or more after its send, is a wake the kernel lost (held under the
        # timed bounds, printed otherwise)
        bad = [s for s in ten if kv(s, 'taken') != 10 or not isinstance(kv(s, 'worst-us'), int) or kv(s, 'worst-us') > 5000]
        if TIMED and bad:
            s0 = bad[0]
            why.append(f'sleeper round {kv(s0, "round")}: taken {kv(s0, "taken")} of ten, the worst {kv(s0, "worst-us")} us, '
                       f'merged {kv(s0, "merged")}, sleeps entered with one pending {kv(s0, "slept-pending")} ({len(bad)} rounds so)')
        tot = {k: sum(kv(s, k) for s in ten if isinstance(kv(s, k), int)) for k in ('set', 'merged', 'took', 'slept-pending')}
        info.append(f'the sleeper took ten of ten in {sum(1 for s in ten if kv(s, "taken") == 10)} of {len(ten)} rounds '
                    f'(taken {[kv(s, "taken") for s in ten]}, worst {[kv(s, "worst-us") for s in ten]} us); the kernel: '
                    f'set {tot["set"]}, merged {tot["merged"]}, took {tot["took"]}, sleeps entered with one pending {tot["slept-pending"]}')
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
    # each round read once its threads were off every processor and a wait4 with no child had run the kernel's reap,
    # which frees the space an exec parked while an ended sibling's processor still held it (kernel/sched's
    # leave_space) and the siblings' stacks the departure rule put off: the frames the round's own wait4 may leave out
    keys = ('rss-kb', 'waited-kb', 'settled-kb', 'settle-ms', 'left')
    missing = [k for k, s in enumerate(exe) if not all(isinstance(kv(s, x), int) for x in keys)]
    if missing:
        why.append(f'exec round {missing[0]}: no settled MemFree reading (`settled-kb`, `left`)'
                   + (f', nor in rounds {missing[1:]}' if len(missing) > 1 else ''))
    for k, s in enumerate(exe):
        if k not in missing and kv(s, 'left'):
            why.append(f'exec round {k}: {kv(s, "left")} of its threads still current on a processor '
                       f'{kv(s, "settle-ms")} ms after its wait4')
    fr = [s for s in ex if s.startswith('frames-kb ')]
    if not fr or not isinstance(kv(fr[0], 'before'), int) or not isinstance(kv(fr[0], 'after'), int) \
            or kv(fr[0], 'before') == 0 or kv(fr[0], 'after') < kv(fr[0], 'before') - 64:
        why.append(f'MemFree around the four exec rounds: {fr[0] if fr else "no line"} (within 64 kB, each read once settled)')
    if exe and not missing and fr:
        info.append(f'MemFree before {kv(fr[0], "before")} kB, after {kv(fr[0], "after")} kB, each read once the round\'s '
                    f'threads were off every processor and a reap had run (settled in at most '
                    f'{max(kv(s, "settle-ms") for s in exe)} ms); given back by each round\'s settle '
                    f'{[kv(s, "settled-kb") - kv(s, "waited-kb") for s in exe]} kB; the group\'s VmRSS before each exec '
                    f'{[kv(s, "rss-kb") for s in exe]} kB')
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
    share = []
    if not isinstance(kv(s, 'cpu-us'), int) or kv(s, 'cpu-us') < 0.8 * kv(s, 'expected-us'):
        low = f'the children\'s CPU {kv(s, "cpu-us")} us against {kv(s, "expected-us")} us of work (0.8 at least)'
        if TIMED or not isinstance(kv(s, 'cpu-us'), int):
            why.append(low)
        else:
            share = [f'{low}; {SHARES}']
    seen = [int(x) for x in str(kv(s, 'cpus')).split(',') if x.isdigit()]
    need = max(2, min(n, 16) - 1)
    # the processors the children ran on, by the kernel's own ring-3 ticks gained while they ran: two ticks at least
    # (a child's shortest work is 20 ms; the sampler and the parent run ring 3 for microseconds a wake, so either may
    # take a stray tick). The sampler's list stays as INFO: it never sees a child on the processor it runs on itself.
    ut = next((x for x in w if x.startswith('user-ticks')), None)
    if ut is None:
        why.append('no SMP-WAIT user-ticks line (the kernel\'s per-processor ring-3 ticks around the children)')
        return why, [f'children seen on {seen} (the sampler)']
    gains = {int(i): d for i, d in re.findall(r' (\d+):(\S+)', ut)}
    ran = [i for i in range(n) if re.fullmatch(r'\+\d+', gains.get(i, '-')) and int(gains[i]) >= 2]
    missed = [i for i in range(n) if i not in ran]
    if len(ran) < need:
        why.append(f'the children ran on {len(ran)} processors by the kernel\'s ring-3 ticks, want {need} at least')
    info = f'the children ran on {len(ran)} of {n} processors by the kernel\'s ring-3 ticks, missed {missed or "none"}' \
           f' (ticks {" ".join(f"{i}:{gains.get(i, chr(45))}" for i in range(n))}); the sampler saw {seen}'
    # what settles a starved processor: the RESCHEDs each took while the children ran (share() sends one to the
    # lowest-numbered idle processor with none in flight), where the sampler sat, and how often each one idled
    rs = next((x for x in w if x.startswith('resched')), None)
    if rs:
        took = dict(re.findall(r' (\d+):(\S+)', rs))
        info += f'; RESCHEDs taken {" ".join(f"{i}:{took.get(str(i), chr(45))}" for i in range(n))}'
    sm = next((x for x in w if x.startswith('samples ')), None)
    if sm:
        on = [int(x) for x in str(kv(sm, 'sampler-on')).split(',') if x.isdigit()]
        idle = dict(re.findall(r' (\d+):(\d+)', sm.split(' idle', 1)[1] if ' idle' in sm else ''))
        info += (f'; the sampler sat on {on} in {kv(sm, "samples")} samples; idle in samples'
                 f' {" ".join(f"{i}:{idle.get(str(i), chr(45))}" for i in range(n))}')
    return why, share + [info]


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
    # end-nooff (a test build, `pax.nopoweroff`): root asks power-off, which is not done; the end halts, every
    # application processor already stopped (SMP-END-NOOFF)
    erow = 'SMP-END-NOOFF' if how == 'nooff' else 'SMP-END'
    if how == 'nooff' and 'poweroff: not done (pax.nopoweroff, a test kernel)' not in text:
        why.append('no `poweroff: not done (pax.nopoweroff, a test kernel)` line')
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
    if how in ('halt', 'nooff'):
        ds = [parse_dump(d) for d in dumps()]
        last = ds[-1] if ds else {}
        wrong = [(k, hex(c.get('rip') or 0), c.get('hlt'), hex(c.get('rfl') or 0)) for k, c in sorted(last.items())
                 if k and not (c.get('hlt') == 1 and c.get('rfl') is not None and not c['rfl'] & 0x200
                               and (c.get('rip') or 0) >= KERNEL)]
        if not ds or len(last) != N or wrong:
            why.append(f'application processors not halted with interrupts off in the kernel: {wrong or len(last)}')
    elif a.qemu_status != 0:
        why.append(f'QEMU ended with status {a.qemu_status} (0: the machine {"powered off" if how == "poweroff" else "reset"})')
    bad = bad_lines(ending=True)
    if bad:
        why.append(f'the kernel said: {bad[:3]}')
    if why:
        fail(erow, why[0], why[1:])
    else:
        ok(erow, f'{want}, between the processes\' end and the end\'s line ({how})')
elif a.kind in ('panic', 'panic2'):
    # a test build's `pax.panictest=1|2`: one test panic, or two at once (one owns it, the other says one line);
    # every processor halted with interrupts off in the last dump (gated under KVM; printed under TCG)
    row = 'SMP-PANIC-STOP' if a.kind == 'panic' else 'SMP-PANIC-TWO'
    why, info = [], []
    # the two lines' texts, not whole lines: kernel/panic's print token serializes the panicking processors' lines,
    # but a token wait past its bound, or a lock holder's line in progress, can put bytes beside them; each text must
    # still be there whole, exactly once (a text broken by another's bytes is red)
    firsts = re.findall(r'PANIC testwords: a test panic, cpu ', text)
    seconds = re.findall(r"\(a second panic, cpu \d+'s first\): testwords: a test panic", text)
    want2 = 1 if a.kind == 'panic2' else 0
    if 'SMP-PANIC spinners' not in text:
        why.append('the spinners never started')
    if len(firsts) != 1 or len(seconds) != want2:
        why.append(f'{len(firsts)} first and {len(seconds)} second test panics, want 1 and {want2}')
    late = re.findall(r'^cpus: cpu \d+ did not stop for the panic$', text, re.M)
    ds = [parse_dump(d) for d in dumps()]
    last = ds[-1] if ds else {}
    wrong = [(k, hex(c.get('rip') or 0), c.get('hlt'), hex(c.get('rfl') or 0)) for k, c in sorted(last.items())
             if not (c.get('hlt') == 1 and c.get('rfl') is not None and not c['rfl'] & 0x200 and (c.get('rip') or 0) >= KERNEL)]
    facts = f'late {late or "none"}; not halted with interrupts off: {wrong or ("none" if ds else "no dumps")}'
    if TIMED:
        if late:
            why.append(f'processors late for the panic\'s stop: {late}')
        if not ds or len(last) != N or wrong:
            why.append(f'not every processor halted with interrupts off: {wrong or len(last)}')
    else:
        info.append(f'{UNTIMED}; {facts}')
    if why:
        fail(row, why[0], why[1:] + info)
    else:
        ok(row, f'{1 + want2} test panic{"s" if want2 else ""}, one owner; every processor stopped, interrupts off')
elif a.kind == 'testwords':
    # the shipped kernel given both test words: each ignored by name, root's power-off powers off, no PANIC,
    # and no test op or test panic in its ELF
    why = []
    for w in ('pax.nopoweroff', 'pax.panictest'):
        if f'testwords: {w} ignored (not a test kernel)' not in text:
            why.append(f'no `testwords: {w} ignored (not a test kernel)` line')
    if a.qemu_status != 0:
        why.append(f'QEMU ended with status {a.qemu_status} (0: the machine powered off)')
    # the test op and test panic by name, and the test op's static `fired`, which survives the release tier's inlining
    test = sorted(n for n in symbols() if n.startswith(('_Wtestwords.fire$', '_Wtestwords.test_panic$', '_Wtestwords.fired.')))
    if test:
        why.append(f'the shipped kernel holds test symbols: {test}')
    bad = bad_lines(ending=True)
    if bad:
        why.append(f'the kernel said: {bad[:3]}')
    if why:
        fail('SMP-TESTWORDS', why[0], why[1:])
    else:
        ok('SMP-TESTWORDS', 'both test words ignored by name, powered off, no test symbol in the shipped ELF')
elif a.kind == 'leave':
    # SMP-EXEC-LEAVE: a test kernel given `pax.slowleave=MS` (kernel/testwords) holds each application processor that
    # comes in from ring 3 with its thread ended in place, the lock given back, before it switches that thread off: what
    # a host that has not run that processor does (rows at 4 on two host CPUs: the exec'd leader collected while an
    # ended sibling still ran elsewhere, then `PANIC sched: no process area for slot 0x…06` at that sibling's
    # switch-off). The probe's rounds: four whose main thread exits alone and a sibling then calls exit_group(10), thirty
    # whose sibling execs a program that exits 9, five whose exec'd program is killed by its own SIGKILL; each round's
    # wait4 status, every exec's child line, at least one hold, no PANIC. Then twenty exec-settle rounds, the main
    # thread saying go once a look shows it current on an application processor (`main-cpu`), the exec'ing sibling
    # current beside it: the exec takes the main thread's pid, and a processor still running it shows
    # `current kernel` in /proc/pax-cpus, its CR3 still the space the exec parked. Each is read as SMP-EXIT's are (at
    # the wait4, settled) and 500 ms on, once every hold is long over; the settled reading must be the late one (the
    # rows at 4 on two host CPUs at b06378bb: a settle that looked for the group's thread ids alone read 1392 kB short).
    why = []
    word = re.search(r'^testwords: pax\.slowleave=(\d+) \(a test kernel\)', text, re.M)
    if not word:
        why.append('no `testwords: pax.slowleave=MS (a test kernel)` line: the word was not taken (a shipped kernel?)')
    holds = re.findall(r'^testwords: a slow leave, cpu \d+(?:, slot \d+, tgid (\d+))?$', text, re.M)
    slows = len(holds)
    # a hold of a thread with a tgid: one the exec re-pointed (or an exit_group's), whose switch-off is charged to its
    # leader's area; an exec's old leader has tgid 0 and is charged nothing, so holds of it alone test nothing
    followers = len([t for t in holds if t and t != '0'])
    lv = lines('SMP-LEAVE')
    want = {'leader-exit': (4, '0xa00'), 'exec': (30, '0x900'), 'exec-kill': (5, '0x9'), 'exec-settle': (20, '0x900')}
    got = {k: [x for x in lv if re.match(rf'{k} \d+ ', x)] for k in want}
    done = 'SMP-LEAVE done' in text
    # at 2 the exec-settle rounds go on past twenty until five have opened, sixty at most (the probe's `row_leave`)
    span = {k: ((20, 60) if k == 'exec-settle' and N == 2 else (w, w)) for k, (w, _st) in want.items()}
    if not done or any(not span[k][0] <= len(got[k]) <= span[k][1] for k in want):
        why.append(', '.join(f'{len(got[k])} of {span[k][0]}' + (f' to {span[k][1]}' if span[k][1] != span[k][0] else '')
                             + f' {k}' for k in want) + ' rounds' + ('' if done else ', no `SMP-LEAVE done`'))
    for k, (_w, st) in want.items():
        for r, x in enumerate(got[k]):
            if kv(x, 'status') != st:
                why.append(f'{k} round {r}: status {kv(x, "status")}, want {st}')
    execs = len(got['exec']) + len(got['exec-kill']) + len(got['exec-settle'])
    kids = len([x for x in lines('SMP-EXIT') if x.startswith('exec-child ')])
    if kids != execs:
        why.append(f'{kids} exec-child lines for {execs} execs')
    # the exec-settle rounds: `waited-kb` at the round's wait4, `settled-kb` once no processor runs a thread of the
    # round and a wait4 with no child has run the reap, `late-kb` after 500 ms more and another such reap
    keys = ('waited-kb', 'settled-kb', 'late-kb', 'settle-ms', 'left')
    sr = got['exec-settle']
    unread = [r for r, x in enumerate(sr) if not all(isinstance(kv(x, k), int) for k in keys)]
    if unread:
        why.append(f'exec-settle round {unread[0]}: no MemFree readings (`waited-kb`, `settled-kb`, `late-kb`, '
                   f'`settle-ms`, `left`)' + (f', nor in rounds {unread[1:]}' if len(unread) > 1 else ''))
    read = [(r, x) for r, x in enumerate(sr) if r not in unread]
    # where the main thread ran when it said go: an application processor's index, or -1 when no look in 3 s found it on
    # one beside the exec'ing sibling
    unsaid = [r for r, x in enumerate(sr) if not isinstance(kv(x, 'main-cpu'), int)]
    if unsaid:
        why.append(f'exec-settle round {unsaid[0]}: no `main-cpu` (where the main thread ran at the exec)'
                   + (f', nor in rounds {unsaid[1:]}' if len(unsaid) > 1 else ''))
    forced = len([1 for x in sr if isinstance(kv(x, 'main-cpu'), int) and kv(x, 'main-cpu') > 0])
    on_ap = f'the main thread on an application processor at the exec in {forced} of {len(sr)}'
    for r, x in read:
        if kv(x, 'left'):
            why.append(f'exec-settle round {r}: {kv(x, "left")} of its threads still current on a processor '
                       f'{kv(x, "settle-ms")} ms after its wait4')
        elif kv(x, 'settled-kb') < kv(x, 'late-kb') - 64:
            why.append(f'exec-settle round {r}: MemFree settled {kv(x, "settled-kb")} kB, '
                       f'{kv(x, "late-kb") - kv(x, "settled-kb")} kB below the reading 500 ms on ({kv(x, "late-kb")} kB): '
                       f'read while the space the exec left was still parked')
    # the window: a round whose wait4 came back with that space still held. At 2 a round whose main thread was on the
    # application processor at the exec has it there, held, while the wait4 comes back, unless it lost that processor
    # first; five such rounds are wanted, the probe going on past twenty for them (sixty at most), and fewer is
    # NOT-FORCED, a red of its own name: the settle was not put to the test often enough to be judged. At 4 the siblings
    # the exec re-pointed are held beside it and the wait4 waits for them, so the old leader may be gone by then:
    # printed there, not wanted
    opened = len([1 for _r, x in read if kv(x, 'waited-kb') < kv(x, 'late-kb') - 64])
    if word and read and not unread and opened < 5 and N == 2:
        why.append(f'NOT-FORCED: {opened} of {len(read)} exec-settle rounds opened at 2, want 5 (a wait4 back with the '
                   f'space the exec left still held: the window the settle must wait out) ({on_ap})')
    if word and slows == 0:
        why.append('0 slow leaves: no application processor held a thread ended in place (the window never opened)')
    elif word and followers == 0:
        why.append(f'{slows} slow leaves, none of a thread with a tgid: no held thread was one charged at its switch-off '
                   f'(the window held only threads with no process)')
    bad = bad_lines()
    if bad:
        why.append(f'the kernel said: {bad[:3]}')
    if why:
        fail('SMP-EXEC-LEAVE', '; '.join(why[:6]), why[6:])
    else:
        ok('SMP-EXEC-LEAVE', f'4 leader-exit, 30 exec, 5 exec-kill and {len(sr)} exec-settle rounds, each its status; '
                             f'{slows} slow leaves, {followers} of a thread with a tgid (an application processor held '
                             f'{word[1]} ms with its thread ended in place); the exec-settle rounds: {on_ap}, the space '
                             f'the exec left still held at the wait4 in {opened} of {len(read)}, each settled reading '
                             f'within 64 kB of the reading 500 ms on (settled in at most '
                             f'{max(kv(x, "settle-ms") for _r, x in read)} ms); no panic')
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
    # SMP-REFUSE: the probe's `one` mode, in each of these boots (one processor runs threads)
    refuse = {x.split()[0]: x for x in lines('SMP-REFUSE') if x.split()[0] != 'done'}
    rwhy = [f'{w} not refused: {refuse.get(w, "no line")}' for w in ('write-ro', 'fetch-nx', 'kernel-read')
            if 'refused yes status 0xb00' not in refuse.get(w, '')]
    if 'SMP-REFUSE done' not in text:
        rwhy.append('no `SMP-REFUSE done`')
    if rwhy:
        fail('SMP-REFUSE', rwhy[0], rwhy[1:])
    else:
        ok('SMP-REFUSE', 'a write to a read-only page, a fetch without PROT_EXEC and a read of the kernel half: SIGSEGV each')
    not_asked([r for r in ROWS if r not in (row, 'SMP-REFUSE')], 'one processor: not asked')
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
    # SMP-DEAD: a thread another processor's exit_group ended while it ran is never run again.
    dead = re.findall(r'^SMP-DEAD round (\d+) status (\S+) running (\d+) revived (\d+)$', text, re.M)
    dwhy = []
    if 'SMP-DEAD done' not in text or len(dead) != 3:
        dwhy.append(f'{len(dead)} rounds of 3 and `SMP-DEAD done` {"seen" if "SMP-DEAD done" in text else "missing"}')
    wrong = [(r, s) for r, s, _g, _v in dead if s != '0x700']
    if wrong:
        dwhy.append(f'statuses {wrong}, want 0x700 each (0xdead: no status in 2 s)')
    back = [(r, v) for r, _s, _g, v in dead if v != '0']
    if back:
        dwhy.append(f'a thread of the ended group current again after its status: {back}')
    alone = [(r, g) for r, _s, g, _v in dead if int(g) < c]
    if alone:
        dwhy.append(f'the group seen on fewer than {c} processors before its exit: {alone}')
    bad = bad_lines()
    if bad:
        dwhy.append(f'the kernel said: {bad[:3]}')
    if dwhy:
        fail('SMP-DEAD', dwhy[0], dwhy[1:])
    else:
        ok('SMP-DEAD', f'three exit_groups with a sibling running on another processor: status 0x700 each, '
                       f'none of the group current again')
elif a.kind == 'trace':
    gate = None if p0 and p0['active'] == N and p0['started'] == N else \
        f'active {p0["active"] if p0 else None} of {N} (started {p0["started"] if p0 else None}): one processor runs threads'
    # SMP-TRACE-EXIT: a traced thread running on another processor when its group exits stops for its tracer itself
    tx = lines('SMP-TRACE-EXIT')
    rounds = [x for x in tx if x.startswith('round ')]
    why, info = [], []
    if 'SMP-TRACE-EXIT done' not in text or len(rounds) != 10:
        why.append(f'{len(rounds)} rounds of 10 and {"`SMP-TRACE-EXIT done`" if "SMP-TRACE-EXIT done" in text else "no `SMP-TRACE-EXIT done`"}')
    for x in rounds:
        r, v = kv(x, 'round'), x.split()[2]
        at = f'round {r} ({v})'
        if kv(x, 'failed-at') not in ('none', 'exit'):
            early = kv(x, 'failed-at') in ('fork', 'initial-stop', 'options', 'clone', 'resume')
            why.append(f'{at}: failed at the {kv(x, "failed-at")}' + (' (before the group\'s exit)' if early else ''))
            if early:
                continue
        if N > 1 and not (isinstance(kv(x, 'thread-cpu'), int) and kv(x, 'thread-cpu') >= 0):
            why.append(f'{at}: the thread was not seen on another processor before its group\'s exit (the case not set up)')
        if kv(x, 'exit-stops') != 2 or kv(x, 'leader') != '0x6057f' or kv(x, 'thread') != '0x6057f':
            missing = [w for w in ('leader', 'thread') if kv(x, w) != '0x6057f']
            why.append(f'{at}: {kv(x, "exit-stops")} PTRACE_EVENT_EXIT stop of 2 reported within 2 s '
                       f'(the {" and ".join(missing)}\'s {"missing" if all(kv(x, w) == "-" for w in missing) else "wrong"})')
            continue
        if kv(x, 'ran-after') != 0:
            c = kv(x, 'current-after')
            why.append(f'{at}: the thread made {kv(x, "ran-after")} spins in the 20 ms after its PTRACE_EVENT_EXIT stop was '
                       f'reported' + (f' (current on processor {c})' if isinstance(c, int) else ''))
        elif isinstance(kv(x, 'current-after'), int):
            why.append(f'{at}: the thread current on processor {kv(x, "current-after")} after its stop was reported')
        if kv(x, 'deaths') != 2 or not x.split(' statuses ')[1].startswith('0x2500 0x2500 ') or kv(x, 'echild') != -10:
            why.append(f'{at}: {kv(x, "deaths")} death of 2 reported within 2 s of the CONTs '
                       f'(statuses {" ".join(x.split(" statuses ")[1].split()[:2])}, then {kv(x, "echild")}, want -10)')
    bad = bad_lines()
    if bad:
        why.insert(0, f'the kernel said: {bad[:3]}')
    cpus = [kv(x, 'thread-cpu') for x in rounds]
    info.append(f'the thread\'s processor at each exit {cpus}')
    if gate:
        fail('SMP-TRACE-EXIT', gate, why + info)
    elif why:
        fail('SMP-TRACE-EXIT', '; '.join(why[:4]), why[4:] + info)
    else:
        spins = sum(1 for x in rounds if x.split()[2] == 'spin')
        ok('SMP-TRACE-EXIT', f'{len(rounds)} rounds ({spins} spinning, {len(rounds) - spins} in a system-call loop): '
                             f'both threads\' PTRACE_EVENT_EXIT reported, the thread stopped when reported (no spin after, '
                             f'current nowhere), both deaths after the CONTs; {info[0]}')
    # SMP-TRACE-INT: a PTRACE_INTERRUPT reaches a seized tracee running on another processor at once
    if N == 1:
        not_asked(['SMP-TRACE-INT'], 'one processor: not asked')
    else:
        ti = lines('SMP-TRACE-INT')
        ir = [x for x in ti if x.startswith('round ')]
        why = []
        if 'SMP-TRACE-INT done' not in text or len(ir) != 9:
            why.append(f'{len(ir)} interrupts of 9 and {"`SMP-TRACE-INT done`" if "SMP-TRACE-INT done" in text else "no `SMP-TRACE-INT done`"}')
        for x in ir:
            k = kv(x, 'round')
            if not (isinstance(kv(x, 'cpu'), int) and kv(x, 'cpu') >= 0):
                why.append(f'round {k}: the tracee not seen on another processor before its interrupt')
            if kv(x, 'req') != 0 or kv(x, 'status') != '0x80057f':
                why.append(f'round {k}: status {kv(x, "status")}, want 0x80057f (PTRACE_EVENT_STOP), the request\'s return {kv(x, "req")}')
            if kv(x, 'cont') != 0 or kv(x, 'ran') != 'yes':
                why.append(f'round {k}: not running 20 ms after its CONT (the CONT said {kv(x, "cont")})')
        if bad:
            why.insert(0, f'the kernel said: {bad[:3]}')
        lat = [kv(x, 'us') for x in ir if isinstance(kv(x, 'us'), int)]
        fast = sum(1 for u in lat if u <= 2000)
        if TIMED and len(lat) == 9 and fast < 8:
            why.append(f'{fast} of 9 PTRACE_INTERRUPT stops within 2 ms (8 wanted under KVM)')
        figs = f'latencies {lat} us' + ('' if TIMED else f'; {UNTIMED}')
        if gate:
            fail('SMP-TRACE-INT', gate, why + [figs])
        elif why:
            fail('SMP-TRACE-INT', '; '.join(why[:4]), why[4:] + [figs])
        else:
            ok('SMP-TRACE-INT', f'nine interrupts of a seized tracee running on another processor, each a '
                                f'PTRACE_EVENT_STOP, the tracee running again after each CONT; {figs}')
    # SMP-STOPWRITE: after SIGSTOP at most one write already in progress completes, never two, and none after the stop
    # has taken effect
    sr = [x for x in lines('SMP-STOPWRITE') if x.startswith('round ')]
    why = []
    if 'SMP-STOPWRITE done' not in text or len(sr) != 24:
        why.append(f'{len(sr)} rounds of 24 and {"`SMP-STOPWRITE done`" if "SMP-STOPWRITE done" in text else "no `SMP-STOPWRITE done`"}')
    for x in sr:
        settle, b, t = kv(x, 'settle'), kv(x, 'bytes-after'), kv(x, 'turns-after')
        at = f'round {kv(x, "round")} (settle {settle} ms)'
        wc = cpu(kv(x, 'writer-cpu'))
        if N > 1 and (wc is None or wc == cpu(kv(x, 'me-cpu'))):
            why.append(f'{at}: the writer not seen on another processor in 2 s of looking ({kv(x, "looks")} looks; '
                       f'the case not set up)')
        if settle == 0 and not (isinstance(b, int) and b <= 1):
            why.append(f'{at}: {b} bytes written after the stop (at most the one write in progress)')
        elif settle != 0 and (b != 0 or t != 0):
            why.append(f'{at}: {b} bytes and {t} ring-3 turns after the stop had taken effect (none)')
        if kv(x, 'stop-status') != '0x137f' or kv(x, 'cont-status') != '0xffff':
            why.append(f'{at}: stop status {kv(x, "stop-status")} and continue status {kv(x, "cont-status")} '
                       f'(0x137f and 0xffff)')
        if not (isinstance(kv(x, 'bytes-resumed'), int) and kv(x, 'bytes-resumed') > 0):
            why.append(f'{at}: no byte in the 30 ms after SIGCONT (the writer not writing again)')
    if bad:
        why.insert(0, f'the kernel said: {bad[:3]}')
    at_once = [kv(x, 'bytes-after') for x in sr if kv(x, 'settle') == 0]
    looks = [kv(x, 'looks') for x in sr if isinstance(kv(x, 'looks'), int)]
    figs = (f'drained at once, the bytes after each stop {at_once} ({sum(1 for v in at_once if v == 1)} of '
            f'{len(at_once)} a write in progress); drained 50 ms on, '
            f'{[kv(x, "bytes-after") for x in sr if kv(x, "settle") != 0]}; the set-up\'s looks '
            f'{"most " + str(max(looks)) + ", " + str(sum(1 for v in looks if v > 1)) + " rounds more than one" if looks else "not printed"}')
    if gate:
        fail('SMP-STOPWRITE', gate, why + [figs])
    elif why:
        fail('SMP-STOPWRITE', '; '.join(why[:4]), why[4:] + [figs])
    else:
        ok('SMP-STOPWRITE', f'{len(sr)} stops of a process writing a pipe on another processor: at most the one write in '
                            f'progress completed after each, none once the stop had taken effect, each stop and '
                            f'continue reported, the writer writing again; {figs}')
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
# SMP-PARK (every kind): the boot's own check that exec's parked-space table holds two held spaces at once and
# frees both once let go (kernel/sched's `park_selftest`); red on any other count or the table's PANIC.
park = re.findall(r'^sched: parked spaces: (\d+) held parked at once, (\d+) left once let go$', text, re.M)
pfull = re.findall(r'^PANIC sched: more parked spaces.*$', text, re.M)
if pfull or (park and park[0] != ('2', '0')):
    fail('SMP-PARK', pfull[0].strip() if pfull else f'{park[0][0]} held parked at once and {park[0][1]} left, want 2 and 0')
elif park:
    ok('SMP-PARK', 'two held spaces parked at once, both freed once let go')
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

# Every kind: no allocation on any processor (the stage 2 contract's §3.7 (c) as amended): the kernel says in every
# /proc/pax-cpus the boot printed that its heap was not started, so the runtime can allocate nothing, locked or not;
# an allocation anyway panics by name (`heap: alloc before heap.start`), and that line is this row's red verbatim
# (the plant apalloc's: an application processor allocating before kernel/klock's `enter`).
heap_panics = re.findall(r'^PANIC heap: .*$', text, re.M)
heap_reads = [re.search(r'^heap-started (\d+)$', blk[2], re.M)
              for blk in re.finditer(r'^SMP-PROC (\S+) begin\n(.*?)^SMP-PROC \1 end$', text, re.M | re.S)]
heap_off = [h[0] if h else 'no heap-started line' for h in heap_reads if not h or h[1] != '0']
if heap_panics:
    fail('SMP-NOHEAP', heap_panics[0], heap_panics[1:])
elif heap_off:
    fail('SMP-NOHEAP', f'a /proc/pax-cpus that does not say `heap-started 0`: {heap_off[:3]}')
elif heap_reads:
    ok('SMP-NOHEAP', f'the heap not started (`heap-started 0` in each of {len(heap_reads)} reads of /proc/pax-cpus), no heap panic')

sys.exit(1 if red else 0)
