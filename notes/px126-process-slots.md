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
