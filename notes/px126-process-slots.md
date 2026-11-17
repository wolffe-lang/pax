# px126 — process slots: 64 to 1024

Base: trunk `309036ec`. PAX has 64 thread slots system-wide (`kernel/sched`, `SLOTS`). Measured on that trunk under
KVM by a probe that forked until refused: 60 children, then `fork` answered EAGAIN with `refused: no free process
slot`. Every wolf program runs two threads (its runtime starts a second one), so about 28 wolf processes fit in the
whole system, the login shell and the ssh server's sessions among them. A terminal multiplexer holding 32 ptys, a
pelt shell on each, had four shells' `clone3` refused and those shells end with status 71.

This note is written before the first change (§1–§5, the prediction) and filled in after (§6 on).

## 1. What SLOTS sizes today (trunk `309036ec`, read)

Static, in boot/sched.S's `.bss`, per slot:

| table | bytes a slot | 64 slots | what it is |
|---|---:|---:|---|
| `pax_threads` | 512 | 32 KiB | the thread record, 64 words, full since px102 |
| `pax_procs` | 49,152 | 3 MiB | the process area: descriptors (1,024), mapping records, signal actions, credentials |
| `pax_siginfo` | 1,024 | 64 KiB | two sets of 64 origin words (thread, process) |
| `pax_debugregs` | 64 | 4 KiB | DR0–DR7 as a tracer set them |
| `pax_trace_state` | 256 | 16 KiB | ptrace's side record |
| `pax_fpu_state` words | 8 | 512 B | the slot's FPU area's address |
| **total** | **51,016** | **3.11 MiB** | |

At boot: one frame per slot for the FPU area (`fpu.start`: 64 frames, 256 KiB, whether a slot is ever used or not),
and one page table taken by mapping and unmapping the last slot's stack (px24). Per live thread: its kernel stack,
four frames (16 KiB) mapped in a 64 KiB span of PML4 slot 416 whose low 48 KiB are the guard. The process area is
used only by a group's leader (a thread reads and writes its leader's), yet every slot has one: a thread costs
48 KiB of `.bss` it never touches.

Elsewhere: `kernel/fpu` and `kernel/trace_state` keep their own copy of the number 64 (they cannot import sched);
`kernel/procfs` keeps a task's slot in 7 bits of a reference (`(r >> 40) & 127`); `process_ends` keeps "the
children whose groups this end may orphan" as a 64-bit mask indexed by slot (`kids | (1 << t)`), which is wrong
for any slot past 63.

Not sized by SLOTS, and so unchanged here: pids (one counter, never reused, 20 bits in a signal's origin word),
the run queue (a FIFO linked through the records), ptys (256), open files (2,048), pipes (512), eventfds (64),
epoll objects (16).

## 2. The scans (read)

Every one below walks every slot, `while s < SLOTS`, on every call:

| path | how often | what it walks |
|---|---|---|
| `wake_sleepers` | **every tick and every switch**: `preempt`, `switched`, and each wait (`sleep_current`, `block_input`, `block_pipe*`, `wait_child`, `futex_wait`, `vfork_wait`, `park_current`, `suspend_current`, `resuspend`, `trace_stop`, `yield_current`, `end_with`, `end_thread`) | two words a slot |
| `reap` and the free-slot search | every fork, thread, kernel start; `reap` also every `wait4`/`waitid` | one word a slot |
| `wake_pipes` | every change to a pipe, socket, pty, FIFO, flock, eventfd or epoll set (about forty call sites) | one word a slot, and every waiter made ready |
| `wake_input`, `wake_net` | every console or network interrupt | one word a slot |
| `futex_wake` | a futex wake: one walk per thread woken, one more when none | three words a slot |
| `wake_waiter`, `poke`, `taker` | a child's end, stop or continue; every signal raised, mask changed, thread ended | |
| `live_slot`, `proc_slot`, `tid_slot`, `trace_live`, `slot_of` | `kill(pid)`, `/proc/<pid>`, a parent found at an end or a stop, `setpgid`, ptrace | stops at the slot found |
| `proc_after` | each entry of a `/proc` listing: a listing walks P × SLOTS | |
| `raise_pgrp`, `group_exists`, `member_after`, `has_stopped`, `orphaned_but` | a group's signal, `setpgid`, `setsid`, job control; `orphaned_but` calls `live_slot` for each member, so it is SLOTS² | |
| `process_ends` | every process's end: for each child, `orphaned_but` of its group, and a pairwise loop over the children | SLOTS² to SLOTS³ in the worst case |
| `end_others`, `own_borrowed`, `reparent` (with `wake_waiter` for each zombie child), `unpark`, `discard`, `tty_leaves`, `threads_unreported` (for each zombie a wait finds), the trace walks | a process's end, exec, stop, continue, hangup, a wait | |
| outside sched: procfs' task listing and `trace_child` (P × SLOTS), `vm.cut_maps` (each truncate) | | |

A record is 512 bytes, so a walk touches one cache line a slot: 4 KiB at 64 slots, 64 KiB at 1,024, more than
a level-1 data cache holds.

## 3. The prediction

- **Raising SLOTS alone to 1,024 costs every switch.** `wake_sleepers` runs at every switch whatever runs; at 1,024
  slots it reads 2,048 words on 1,024 lines. Predicted under KVM: a yield between processes that costs about
  1–2 µs on trunk costs 2–4 µs more, at 16 processes as at 1,000 (the walk is the table's, not the live count's):
  two to three times slower. Under TCG the ratio is about the same.
- **Raising SLOTS alone to 1,024 costs 48 MiB of `.bss`** (the areas), 19% of a 256 MiB machine, before anything
  runs: the CI machine's free frames at the first program fall from about 58,000 to about 45,500.
- **With the design below:** the static cost falls to about 1.9 MiB at 1,024 slots (less than trunk's 3.1 MiB at
  64), plus 66 page-table frames taken at boot; a slot costs only while it lives: a thread 5 frames (stack and FPU
  area), a process 17 (and its address space); the switch costs what trunk's does at 16 and 64 processes, and at
  1,000 within twice that (the rest is caches and TLBs, not walks).
- **What 256 MiB holds.** Not 1,024 processes: PAX maps a process's 1 MiB initial stack eagerly (px82: 256 pages)
  and a fork copies every present page, so the smallest real process (a static C program) takes about 1.5 MiB,
  and 256 MiB holds about 120 of them before a fork is refused for frames by name (`no frames for a copy of the
  address space`, ENOMEM); a pelt shell takes about 16 MiB (its image is 15 MB), so about 12 shells. Threads are
  cheaper: one process's threads with small stacks reach the table's limit inside 256 MiB (about 1,020 threads,
  20 KiB of kernel each, 20 MiB). So on the CI machine memory, not slots, is the limit for processes; at 1–3 GiB
  the slots are.
- **The rows (§5), red on trunk by name:** the thread table fills at about 60 (row `slots-threads` wants ≥ 1,000);
  forks stop at about 60 (`slots-forks` wants 200 at once); 100 wolf processes stop at about 28 (`slots-wolf`);
  32 ptys with a pelt and a child each stop at about 15 shells (`slots-ptys`); the reuse loop stops at its first
  batch (`slots-reuse`). Green after. The existing scheduler, signal, session, job and ptrace suites unchanged.
- **Not predicted to change:** the wake-everyone rule (`wake_pipes`: every waiter runs its call again at every
  change). Its cost is per waiter, not per slot; px24 named its limit ("past about a hundred waiting threads this
  needs queues"), which 1,024 slots now make reachable. Measured here (§5's herd row), not fixed (R-px126-6).

## 4. The design

- **D1. 1,024 slots** (R-px126-1). The thread record, the signal origins, the debug registers and the trace
  record stay static: 1,856 bytes a slot, 1.81 MiB, plus 24 bytes a slot of new scheduler words (below).
- **D2. Process areas on demand.** A second region of PML4 slot 416 (`0xffffd04000000000`), 64 KiB a slot: the low
  48 KiB mapped from 12 frames while the slot leads a process, the top 16 KiB never mapped (an overrun faults
  instead of writing the next slot's area). Mapped (and zeroed) for MAIN at `start`, for a process the kernel
  starts, and for a fork's child; never for a thread of a group or a kernel thread; given back when the slot is
  cleared. `exec_alone` (a thread that is not the leader execs) moves the leader's 12 frames to its own span
  instead of copying 48 KiB, so it cannot fail. A slot with no area asked for one is a named panic. When no frame
  is left, the fork is refused by name (`no frames for a process's area`, EAGAIN), as a stack's is.
- **D3. FPU areas on demand.** A frame taken with a slot's kernel stack and given back with it; `fpu.start` takes
  only the template and MAIN's. A kernel without the FPU (the scheduler suite's) takes none: its stacks are still
  four frames.
- **D4. Page tables taken at `start`** for both regions (32 page tables each), so the first use of a high slot
  never takes a table frame no one gives back (the suites' "every frame back" rows hold). This replaces px24's
  map-and-unmap of the last slot.
- **D5. Walks bounded by the high water** (`S_TOP`, one past the highest slot that is not free). Slots are taken
  lowest first, so the bound follows the live count; clearing the top slot lowers it past free slots. Every
  `while s < SLOTS` walk in sched, procfs and vm runs to it.
- **D6. The next deadline** (`S_WAKE_AT`): `wake_sleepers` returns at once when no deadline has come; each way a
  thread gets one (`sleep`, `sleep_current`, `block_pipe_until`, `block_pipe_eintr`, `futex_wait`) lowers the
  word, and a walk that wakes recomputes it. The tick and the switch no longer walk.
- **D7. pid to slot** (`pax_pid_hint`, 4,096 words: `pid mod 4096` to slot + 1), written when a pid or tid is
  given; `live_slot`, `proc_slot`, `tid_slot` and `trace_live` read it first and walk only when it misses (a pid is
  in one slot at a time). `orphaned_but` and `process_ends` become linear.
- **D8. The children's set** is a mark word a slot, cleared as each group is handled, not a 64-bit mask.
- **D9. A refusal said once.** When no slot is free, `fork`, `clone` and `clone3` answer EAGAIN as before; the
  first refusal of a run of them writes the `refused: no free process slot` line, the rest are counted and not
  written, and the next slot taken ends the run.

## 5. The rows

A new suite, `tests/mpx5-slots`: one probe (`user/elf/slotprobe.c`, static glibc) and kmain_console, an image a
session, each the probe as PID 1 (`/etc/pax-run`). PAX's own limits, so no Linux side: each row is held to what PAX
must do, by name.

| row | session (memory) | asks |
|---|---|---|
| `slots-threads` | 256 MiB | one process makes threads (raw `clone`, 16 KiB stacks) until refused: at least 1,000, the refusal EAGAIN, written once (`refused: no free process slot` exactly once across four refused calls); all joined; every frame back |
| `slots-forks` | 1 GiB | 200 children alive at once (each blocked on a pipe), released, every one reaped with its status |
| `slots-256` | 256 MiB | forks until refused: the count printed, the refusal by name (frames or slots, never a panic), all reaped, every frame back |
| `slots-reuse` | 1 GiB | 3,200 forks in batches of 100 alive and 3,200 threads in batches of 100, every one reaped; pids never reused; every frame back |
| `slots-wolf` | 2 GiB | 100 wolf programs (boreutils `sha256sum`, each on its own pipe) alive at once with two threads each, then fed 64 KiB each and every digest right |
| `slots-ptys` | 2 GiB | 32 ptys, each a session with pelt and a child (`cat`) in its foreground; a line through each cat, then end of file and `exit`; every session's leader reaped with status 0 |
| `slots-switch` | 3 GiB | N processes yielding (`sched_yield`), N = 16, 64, 1,000, three interleaved rounds: the children's CPU time a yield, the minimum of the three; asks the 1,000's within twice the 16's |
| `slots-herd` | 3 GiB | measured, not asked: a pipe ping-pong's round trip with W processes parked in pipe reads, W = 0, 64, 1,000 |

Every session also asks: no PANIC, init ended with status 0, the frames line back to its start, the booted kernel
the one built. Each row prints `PASS <row>` or `FAIL <row>: why` at column 0 of the suite's output.

## 6. As built, and where it differs from §4 and §5

§1–§5 are the prediction as committed before the first change (`04c5069e`). Built as §4 says, with these
differences:

- **Two scheduler words a slot**, not three: `W_AREA` and `W_MARK` (16 bytes a slot).
- **D10. RLIMIT_NPROC** (R-px126-5), added: a real user other than root (and not privileged by its effective id,
  which stands for the capabilities getrlimit(2) names) may hold 512 threads at once, half the table, the probe's
  own among them; a zombie counts, as getrlimit(2)'s "extant" says. `fork`, `vfork`, `clone` and `clone3` ask
  before any work (no address space copied for a refusal) and answer -EAGAIN, `refused: a user's threads at
  RLIMIT_NPROC (512)`, written once a run as D9's is. `prlimit64` and `/proc/<pid>/limits` say 512, soft and
  hard (unlimited before); none can be set, as before. `tests/mpx3-tree.d`'s two pinned `Max processes` lines
  move with it.
- **The wolf row's worker is pelt.** boreutils' `sha256sum` and `cat` run one thread on PAX (measured on trunk:
  `threads 1 to 1 each`); pelt's runtime starts a second before its first prompt (user/pelt.pin, px26). So
  "every wolf program runs two threads" holds for pelt, not for every wolf program (R-px126-8). The row runs
  100 pelts (`sh -c`, a loop summing 1 to 300, then a line read from a pipe of its own) at 4 GiB.
- **The switch row** also measures a yield with nobody else to run (the call, no switch) and holds the yield
  among 16 to at most `SWITCH_ALONE` such yields: a walk of every slot at every switch (raising the table alone)
  breaks it, which the ratio of 1,000 to 16 alone cannot see (§7). Among 64 within 1.5 times the 16's, among
  1,000 within 4 times (2 in §5: measured 1.94, too near for another host; 3 next, until a take with the host's
  other blocks busy measured 2.80; the variant it must catch measures 5.5).
- **A session as a user**, `threads-user` (`slots-nproc`), for D10.
- **The fill row** wants 80 children at least (the old table held 60).
- **Three existing pins move, each with what it counts:** `tests/mpx3-user`'s U6 (a process of kmain_user's
  batches now takes 28 frames while it lives, not 16: its area's twelve, which were `.bss` before);
  `tests/mpx5-trace.d/layout.py` (the trace layout line says `slots=1024`); `tests/mpx3-tree.d`'s two
  `Max processes` lines (D10). Nothing else in those suites changes.

## 7. What was measured

Every number here is from a lane host under KVM, native kernels, BIOS, the suite's own sessions; each run's
log is named by its sha256 in §8. The CPU times are getrusage(2)'s (PAX counts them from the TSC), the least of
three interleaved rounds.

**What a slot costs.**

| | trunk `309036ec` (64 slots) | this head (1,024 slots) |
|---|---:|---:|
| static `.bss` sized by the table | 3,265,600 bytes (51,016 a slot and the FPU words) | 1,957,952 bytes (1,872 a slot, the pid hint, the FPU words) |
| frames taken at `start` for slots | 64 FPU areas and one page table | 64 page tables, MAIN's area (12) and FPU area (1) |
| frames free when the first program starts, 256 MiB, the same image | 61,676 | 61,977 (301 more, 1.2 MiB) |
| a thread, while it lives | 4 frames (its stack) | 5 (its stack and FPU area) |
| a process's leader, while it lives | 4 frames, its area static | 17 (and its area mapped), the probe's process 578 frames in all where trunk's took 565 |

**What 256 MiB holds** (the `fill` and `threads` sessions). One process's threads with 8 KiB stacks: 1,020, the
table's limit (1,024 less main, idle, the network's clock thread and the probe), twice, every one joined and every
frame back. Forked children of the probe, each blocked on a pipe: 100, then `fork` answered ENOMEM with
`refused: no frames for a copy of the address space` (each child about 610 frames, 2.4 MiB: the probe's present
pages, its eagerly mapped 1 MiB initial stack among them, copied by the fork); 99 with `as` in the image too.
So on a 256 MiB machine processes run out of memory long before slots; threads reach the table. Trunk's 64 slots
stopped both at 60.

**What the rows found** (at `36963e2f`, this branch but for this note and RLIMIT_NPROC's last fix): 1,020 threads
twice; 200 children at once; 3,200 forks and 3,200 threads in rounds of 100, pids rising from 2 to 3201, every
frame back; 100 pelts at once, two threads each (200), each `45150 go`; 32 ptys, each a session of pelt and cat
(64 processes, 96 threads), a line through each cat, `bye<i>` from each shell, every leader reaped with status 0.
As user 1000 the first round made 511 threads besides the probe and was refused, but the second made none: the
first round's threads, ended and not yet reaped, were still counted (`slots-nproc` red; fixed at `8c45ad86`, a
thread that has ended and waits only for its reap is not counted).

**A yield among N processes** (`slots-switch`: N processes released at once, each yielding 200,000 / N times).

| kernel | a lone yield | N = 16 | N = 64 | N = 1,000 |
|---|---:|---:|---:|---:|
| trunk `309036ec` | | 1,328 ns | (60 slots) | (60 slots) |
| the walks unbounded (`notes/px126/variant-unbounded.py`: every walk to 1,024, the tick and every switch walking; what raising SLOTS alone leaves) | 207 ns | 4,525 ns | 4,623 ns | 5,859 ns |
| the walks to the high water, but every switch walking (`notes/px126/variant-noskip.py`) | | 1,234 ns | 1,503 ns | 6,810 ns |
| this branch (`36963e2f`) | 199 ns | 1,128 ns | 1,187 ns | 2,028 ns |

Raising the table alone makes every yield 3.4 times trunk's, at 16 processes as at 1,000 (§3 predicted 2–3):
the walk of 1,024 records, about 3.3 ns a slot. Bounding the walks by the high water alone keeps 16 and 64 near
trunk and makes 1,000 5.5 times 16. With the next deadline, a yield among 16 and 64 costs less than trunk's (no
walk at all; trunk walked 64), and among 1,000 about twice the 16's, which is caches and the TLB (a thousand
address spaces, records, stacks and FPU areas), not walks. The row holds a yield among 16 to at most 10 lone
yields (5.7 here, 21.9 with the walks unbounded), among 64 to 1.5 times the 16's (1.05), among 1,000 to 4 times
(1.80 here; 1.94 and 2.18 in two earlier takes of the same kernel; 2.80, 1,126 and 3,156 ns, in the recorded take
at `73b10e0a`, with the build host's other blocks busy: a thousand processes' working set shares their caches;
5.5 with no deadline skip).

**The wake-everyone rule** (`slots-herd`, measured): a one-byte ping-pong between two processes over two pipes,
with W other processes parked in a read of one more pipe, round trips for a second.

| W parked | 0 | 64 | 1,000 |
|---|---:|---:|---:|
| this branch (`36963e2f`) | 6,426 ns | 99,603 ns (15 times) | 2,061,886 ns (321 times) |
| trunk | 7,205 ns | (60 slots) | (60 slots) |

Every change to any pipe makes every thread parked on any pipe, socket, pty or poll run its call again
(`wake_pipes`, px17 and px24). The walk is bounded now; the wakes are not, and they cost a system call and two
switches each. 64 waiters were reachable before (60 slots) and cost 15 times already; 1,000 are reachable now
(265 to 321 times in two takes).
Not changed here (R-px126-6).

## 8. Seen red, and the plant

Every row was seen red on trunk's kernel before any kernel change, by name, at the rows' commits:

- at `1506c6b5` (the rows' first form), log 10,408 bytes, sha256
  `a9bb69a20d499f317f9bfa1d630312e8cc9e7e5332493f686781ea5565b32647`: `slots-threads` (made 60), `slots-fill`
  (60, EAGAIN), `slots-forks` (60 of 200), `slots-reuse` (60 a round), `slots-wolf` (60, one thread each),
  `slots-ptys` (24 made, 18 through), `slots-switch` (N=64 and N=1,000 not made), `slots-machine` (8 refusal lines
  where 2 are asked; the others' refusals);
- at `ba6b087c` (the wolf row on pelt, the herd timed), log 8,805 bytes, sha256
  `4a337eb470b8ce96c7a293cbdcd1347a5faac4691602343c5c6e9ff1c59f4aa4`: the same rows, `slots-wolf` now 24 pelts
  at once and then EAGAIN, `slots-ptys` 25 made, 17 through;
- `slots-nproc` at `4bf82c8f` (the row, before RLIMIT_NPROC): user 1000 made 1,020 threads where 512 are its
  limit, and `slots-machine` saw `no free process slot` where the row asks for RLIMIT_NPROC's refusal, log 4,344
  bytes, sha256 `ad8a54e5c41f2ffbee1708f4b5d706b6b317fb886173467166a8c53fb1e99518`; and at `36963e2f`, before
  `8c45ad86`, its second round red by name (`made 0`, §7), log sha256
  `4e6765d3bd53eaa78805457a295a834907fcc842174271fa2adc4993fdeecd5c`;
- `slots-switch`'s two bounds each red on the variant that breaks it, each a patch in `notes/px126/`
  (`variant-unbounded.py`, `variant-noskip.py`) applied to this branch's kernel before RLIMIT_NPROC (`9d535928`'s
  `kernel/`), never merged: the walks unbounded, `a yield among 16 costs 4525 ns, more than 10 times a lone
  yield's 207 ns`, log sha256 `a9ab39760294f8e35b8123a3b0fd9ca587290f93317fa1a5d57f1bd9dee09aed`; the walks to the
  high water with no deadline skip, `a yield among 1,000 costs 6810 ns, more than twice the 16's 1234 ns` (the
  row's bound was twice then; 5.5 times), log sha256
  `1713309e801d62dda113746051b66e1c0bdd5953571c15e1fe65cfc55710ffa3`; again at the bound of four times, on this
  head's kernel, in the pull request.

An existing suite found one more: `tests/mpx5-trace`'s `clone-event` script at `36963e2f` panicked by name, `PANIC
sched: no process area for slot 0x0000000000000005`: a tracer's wait collected a traced thread's death, and
`child_usage` asked the thread's own area, which a thread no longer has (before, a zeroed static area answered
zeros). Fixed at `daa298ba`: a slot with no area reports no usage of its own, as before. Every other `own_area`
was read again for the same mistake: each is asked of a leader, MAIN, or a slot whose area it checks first.

`tests/ci-plan` found one in the rows: the `threads-user` session runs the probe through `/bin/as`, so `as` and
`tools/mkas` now select `tests/mpx5-slots`, and the two expectations that list the suites they reach did not name
it (`FAIL (2)` in the recorded take at `73b10e0a`). The list names it now.

The plant, `px126-plant-area-leak-2` (pushed, never merged; `px126-plant-area-leak` is the same break on
`73b10e0a`): `free_area` unmaps a process area's twelve pages and gives none back, so every non-quiet session's
`slots-machine` row says `frames not all back`. Its record is the pull request's.

## 9. Not measured

- UEFI and the release tier: CI's legs. Every number in §7 is native BIOS under KVM.
- TCG: none of these rows was run under TCG here (CI's runners have KVM).
- `tests/mpx5-forks`: built with musl-gcc, which no image with QEMU on the build host has; CI runs it.
- RLIMIT_NPROC against Linux: the value is PAX's own (Linux's default is half of threads-max, memory-dependent).
- A real machine: never; QEMU only.

## 10. Rulings (recommended and implemented)

- **R-px126-1 the number.** A. 1,024 static records (the record, signal origins, debug and trace words: 1.9 MiB of
  `.bss`, less than 64 slots took); B. a table that grows on demand (records mapped as the high water rises: no
  static cost and any ceiling, but every slot taken can fail for a frame, and the frames line needs the growth
  given back); C. 4,096 static (7.6 MiB, 3% of a 256 MiB machine, and four times the walks). A process costs at
  least 2 MiB of memory today (R-px126-7), so 1,024 threads is where 2–4 GiB machines meet the table, and a
  256 MiB machine pays less for it than for trunk's 64. **Recommended: A.**
- **R-px126-2 the process areas.** A. mapped per leader from frames while it lives (48 KiB, a guard above); B.
  static per slot (48 MiB of `.bss` at 1,024); C. from the kernel heap (its size classes stop at 2 KiB, its pages
  at 128 MiB). **Recommended: A.**
- **R-px126-3 the refusal said once.** A. the first of a run of refused clones writes its line, the rest are
  counted and silent, a slot taken ends the run; B. every refusal a line (trunk: a shell retrying a fork floods
  the log); C. once a boot. **Recommended: A**, for no free slot and for RLIMIT_NPROC alike.
- **R-px126-4 guest memory a row.** The rows set the guest's memory they need (256 MiB to 4 GiB, `--qemu -m`);
  `tools/qemu-run`'s default (256 MiB) is unchanged. **Recommended.**
- **R-px126-5 RLIMIT_NPROC.** PAX reported it unlimited and kept no count: one user could take every slot,
  root's login and an ssh session among them. A. Linux's rule (getrlimit(2)): a real user other than root holds at
  most RLIMIT_NPROC threads, root and the privileged exempt, 512 (half the table, as Linux's default is half of
  threads-max), reported by `prlimit64` and `/proc/<pid>/limits`, not settable; B. a reserve of slots for root
  only (no Linux ABI says it); C. nothing. **Recommended and implemented: A** (small: a walk at each clone of a
  user other than root).
- **R-px126-6 the wake-everyone rule.** Its walk is bounded now; its wakes are one a waiter at every change, about
  300 times a round trip's cost with 1,000 parked readers (§7). A. wait queues by object (a waiter keyed to the pipe,
  pty or socket it waits on, `poll` and `epoll_wait` registered on each of theirs): a readiness redesign across
  kernel/files, pty, tcp, udp, event and ready, a lane of its own with `slots-herd` as its red row; B. keys for
  plain pipe and pty reads only (poll's waiters, a shell at its prompt among them, still woken by everything); C.
  leave it. **Recommended: A, as the next lane.** Not done here.
- **R-px126-7 what a process costs.** The 1 MiB initial stack is mapped eagerly (px82) and a fork copies every
  present page (px17), so a forked C process costs about 2.4 MiB and a 256 MiB machine holds about 100. A stack
  backed on touch and copy-on-write fork would make the slots, not memory, the limit there. **Recommended as a
  later lane;** not this one's.
- **R-px126-8 wolf programs' threads.** boreutils' utilities run one thread on PAX; pelt two (its runtime's signal
  thread). The wolf row runs pelt. **Recorded.**

## 11. Done when

- `tests/mpx5-slots` green on every leg (CI's all tier), and its plant red by name;
- the scheduler, threads and signals, job control and sessions, ptrace, pty and fork suites green, unchanged but
  for the three pins of §6;
- the frames lines balanced in every suite (the page tables taken at `start`);
- a pull request at the settled head with its records.
