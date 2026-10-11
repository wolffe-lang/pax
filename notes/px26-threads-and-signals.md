# px26 — Threads and signals (the new pelt and the long listing on PAX)

Contract: px26's, `sprints/pax/26-threads-and-signals/` in wolffe-lang/wolf
(read 2026-10-11). Branch `px26` in pax, cut from pax trunk `0cc43be`
(px21a merged). §1–§3 are committed before the first change to the
kernel, the tests or the pins; §2's straces were taken first, as the
contract's first act.

One deliverable: PAX's shell image runs the current pelt (sh05,
`b32bebc`) and the current boreutils (bu20, `870815c`) unmodified. That
takes threads (`clone3` with `CLONE_THREAD`), `futex` and signals
delivered to a program's handlers, with typed sessions byte-identical
to Linux: `ls -l /bin`, `stat`, `readlink`, `env`, `exec`, a `trap`,
and Ctrl-C at the prompt and on a running child.

## 1. Forbidden, absolutely

- No kernel's, libc's or threading library's source is read (ruling
  #22), and none is searched for; the refs clone's sparse checkout is
  never widened. Facts come from the Linux man pages (`clone(2)`,
  `clone3(2)`, `futex(2)`, `set_tid_address(2)`, `set_robust_list(2)`,
  `signal(7)`, `sigaction(2)`, `sigprocmask(2)`, `sigreturn(2)`,
  `sigaltstack(2)`, `kill(2)`, `tgkill(2)`, `madvise(2)`, `prctl(2)`,
  `termios(3)`, `sendfile(2)`, `copy_file_range(2)`, `rtc(4)`), the
  x86-64 psABI, the Intel SDM, the uapi headers the sparse checkout
  holds, QEMU's documentation, and black-box runs on Linux: strace of
  the real binaries and small static C programs that print what they
  see.
- `kernel/tcp`, `kernel/socket`, `kernel/udp`, `kernel/ip`,
  `kernel/netd` and the `mpx4-*` tests are px23's: not touched.
- Test binaries for PAX are built in the Ubuntu 24.04 container on
  kasumi (`px13-ubuntu`) or on the CI runner, never with kasumi's own
  glibc. pelt and boreutils are used as built from their own
  repositories at their pins, never read for how they work.
- A toolchain pin comes from the RELEASE ARCHIVES by digest; nothing is
  built from wolf-lang's trunk.
- No `rm` outside `~/lanes/px26/` on any host; no scratch in `/tmp` on
  any host; no `git add -A`; nothing under `~/.claude`; no merge, no
  tag; no `2>/dev/null` on a checkout; no trailer of any kind on a
  commit or the PR. No build on nomad-1. Nothing is installed anywhere.
- No "seen red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, `WOLF_PAIRING_REQUIRE_SIBLING=1`,
  full output kept, SKIP counted; `wolf build` exit 2 is a compile
  error; the thread, signal and spawning rows also under
  `taskset -c 0-3` on kasumi.
- kasumi and hasu: remote commands wrapped in `bash`, jobs under
  `setsid` with a pid file, ended by that pid only; signal tests
  started through `env --default-signal=INT,QUIT,HUP,TERM`.
- One CPU, as today: no SMP.
- A planted break fails fast: the suite it reddens has a deadline
  before the break is planted.

## 2. Inputs, verified (2026-10-11)

| input | found |
|---|---|
| pax trunk | `0cc43be` (px21a merged, PR #26), as the contract says; trunk CI green at it (run 38118845800); one open PR, px23's (#27) |
| the kernel's pin | wolf 0.2.27 (`5e17eebe…`) / lupin 0.1.50 (`e2867a35…`) by archive digest (`kernel/wolf.pin`); a `region` may stay open across a switch; `Thread` has 24 words (`kernel/sched`) |
| `user/boreutils.pin` | `50d8907` (bu18's `ls`, wolf 0.2.25): still bu18's, one behind what the contract says (bu19 was never taken) |
| `user/pelt.pin` | `3e7516c` (sh03, wolf 0.2.26) |
| the new pins | pelt `b32bebc23fa6f7b6cb934ab6ca9e57ffe206a9bd` (sh05), boreutils `870815c84fe46904aaa327ce5036d62f1ea9a0b6` (bu20), both resolved on origin; each pins wolf 0.2.27 in its own `wolf-toolchain.toml` |
| the binaries the straces ran | built by pax's own `tools/mkpelt` and `tools/mkboreutils` (a copy of this tree with the two pin lines moved) in `px13-ubuntu` on kasumi, glibc 2.39 static: pelt `0f82c5e6…` (13,712,568 bytes), `ls` `3a08cf52…`, `stat` `0022e40b…`, `readlink` `003661e3…`, `env` `08064e56…`, `cat` `bfd44e48…`, `sleep` `99d35e1c…` |
| what PAX has (px09–px21a) | a process is one thread in one of 16 slots (14 spawnable), with a 4096-byte area a slot (break, mmap cursor, descriptors, working directory, signal actions); `clone3` only as `CLONE_VM\|CLONE_VFORK` and as a fork; `wait4`/`waitid`; pipes, with SIGPIPE as an immediate end of the writer (no handler run); `rt_sigaction` and `rt_sigprocmask` kept, nothing delivered; `kill`, `tkill`, `tgkill` refused by name; FS base and XSAVE state per thread; the line discipline with ISIG clear, Ctrl-C the byte 0x03; `mmap` backs every page with a zeroed frame at the call, PROT_NONE included; every clock counts from 0 at boot; nothing is a symbolic link, `readlinkat` answers -EINVAL for everything; unknown calls -ENOSYS, logged once |
| **sh05's list, re-taken** | `notes/px26/pelt-b32bebc-sigs.strace` (`b4169a2e…`, 621 lines) and `…-long.strace` (`ed4893d9…`), strace 6.8 in the container on Linux 7.2.8, a pseudo-terminal with ISIG set, the keys `strace-sigs.keys` and `strace-long.keys`. pelt's own process makes 44 distinct calls. **As the contract lists:** a second thread before the first prompt, by `clone3({flags=CLONE_VM\|CLONE_FS\|CLONE_FILES\|CLONE_SIGHAND\|CLONE_THREAD\|CLONE_SYSVSEM\|CLONE_SETTLS\|CLONE_PARENT_SETTID\|CLONE_CHILD_CLEARTID, child_tid, parent_tid, exit_signal=0, stack, stack_size=0x200100, tls}, 88)`; its stack `mmap(NULL, 2101248, PROT_NONE, MAP_PRIVATE\|MAP_ANONYMOUS\|MAP_STACK)` then `mprotect(+4096, 2097152, PROT_READ\|PROT_WRITE)`; `prctl(PR_SET_NAME, "wolf-signal")`; `futex(FUTEX_WAIT_BITSET_PRIVATE, val, an absolute CLOCK_MONOTONIC timespec or NULL, FUTEX_BITSET_MATCH_ANY)` and `futex(FUTEX_WAKE_PRIVATE, 2147483647 or 1)`; `rt_sigaction` with one handler, `SA_RESTORER\|SA_RESTART`, for TERM, QUIT, INT, TTIN (and glibc's own for signal 33, `SA_RESTORER\|SA_ONSTACK\|SA_RESTART\|SA_SIGINFO`); `rt_sigprocmask` (`SIG_BLOCK ~[]` around the clone, `SIG_SETMASK`, `SIG_UNBLOCK`); `rt_sigreturn`; `getpid` and `kill(getpid(), SIGTTIN)` after each reaped child; `pipe2(O_CLOEXEC)` with its write end made O_NONBLOCK (the handler writes one byte there, the second thread reads it); `execve` for `exec` with no `clone` before it (the second thread ends with it); `readlinkat("/proc/self/exe")`. **Not as listed:** no `madvise` at all on glibc 2.39 (`MADV_GUARD_INSTALL` is a newer glibc's); the second thread's first allocation is `mmap(NULL, 134217728, PROT_NONE, MAP_PRIVATE\|MAP_ANONYMOUS)` (128 MiB), two `munmap`s that trim it to 64 MiB, and `mprotect` of its first 135168 bytes — which PAX's `mmap` would back with 32768 frames, half its memory; no handler for HUP or USR2 in these sessions (pelt listens for a signal when a session needs it). The child of a spawn is a fork (`clone(CLONE_CHILD_CLEARTID\|CLONE_CHILD_SETTID\|SIGCHLD)`), as px17 measured. Not asked for, as listed: `setpgid`, `tcsetpgrp`, `tcsetattr`, `sigaltstack`, `waitid`, `tgkill` |
| what the signals did on Linux | Ctrl-C at the prompt: `--- SIGINT {si_signo=SIGINT, si_code=SI_KERNEL} ---` taken by pelt's first thread (the second has it unblocked too), the handler's `write` of a byte, `rt_sigreturn`; the terminal shows `^C` and no new line, and the line being typed is gone. With `trap 'echo caught' INT` the trap runs after the next line is entered. Ctrl-C on `sleep 30`: SIGINT to pelt (its `wait4` answers ERESTARTSYS and runs again after the handler) and to the child (`clock_nanosleep` interrupted, `killed by SIGINT`); `wait4` then answers the status and `$?` is 130. SIGCHLD reaches pelt with `CLD_KILLED`/`CLD_EXITED` and is not handled. `cat /bin/pelt \| true`: the writer's `sendfile(1, 4, NULL, 262144)` is -EPIPE and it is `killed by SIGPIPE` (`si_code=SI_USER`, `si_pid` its own) |
| **bu20's list, re-taken** | `notes/px26/bore-870815c-{ls,stat,readlink,env}.strace`: `readlinkat(AT_FDCWD, "/proc/self/exe", …, 4096)` before `main` in every one; `statx(1, "", AT_STATX_SYNC_AS_STAT\|AT_EMPTY_PATH, STATX_ALL)`; `ioctl(1, TCGETS)`; `/etc/passwd` and `/etc/group` opened, `statx`ed by descriptor and read whole; one `statx("/etc/localtime")` (-ENOENT is UTC; under `TZ=UTC0` one failed `statx("/usr/share/zoneinfo/UTC0")` instead); `statx(path, AT_SYMLINK_NOFOLLOW)` per operand and per entry; `openat(O_RDONLY\|O_NONBLOCK\|O_CLOEXEC\|O_DIRECTORY)`, `fstat`, `getdents64`; `readlink` (89, not `readlinkat`) for the operand. `cat` (in the pipeline) asks `copy_file_range` (-EINVAL into a pipe on Linux) and then `sendfile`. No signal call, no futex, no poll, as listed. `ls -l`'s `total` is the entries' blocks: Linux's file systems answer `ceil(size / 4096) * 8` (PAX answers `ceil(size / 512)`), and its dates need the wall clock (a file from 1970 prints its year on Linux; on PAX, whose clocks start at 0, it would print an hour) |
| wolf-lang#691 | open. pelt's barrier is the `kill(getpid(), SIGTTIN)` after each reaped child, followed by a futex wait until the second thread has read the handler's byte for it. What it asks of a kernel: a signal a thread sends itself is delivered to a handler on that thread before `kill` returns to it (so the barrier's byte is in the pipe before pelt waits for it), and every signal raised earlier for the process has reached its handler by then (so an earlier Ctrl-C's byte is in the pipe ahead of the barrier's) |
| kasumi | QEMU 11.1.1, TCG only; `px13-ubuntu` (`ad896450…`, Ubuntu 24.04, glibc 2.39-0ubuntu8.9, strace 6.8); `/home` 95% (51 GB free) |
| hasu | `/dev/kvm` present; KVM through `nix-shell -p qemu`; 353 GB free |

## 3. Prediction (committed before the first change)

### P1. The thread model

- **A thread is a slot** of kernel/sched's sixteen, as a process is
  today; a process is the group of slots that share one **leader**. A
  thread shares with its group, as the nine flags ask: the address
  space (one PML4, owned by the group and given back when its last
  thread is reaped), the process area (descriptors, working directory,
  break, mmap cursor, signal actions) and the pid. Its own: a tid (from
  the pid counter, as Linux numbers them; the leader's tid is the pid),
  a kernel stack, the user frame, the FS base (`CLONE_SETTLS`), the
  x87/SSE/AVX state, the signal mask, a pending set, the
  clear-child-tid address and its name (`PR_SET_NAME`).
- `clone3`/`clone` with `CLONE_THREAD` takes exactly the measured set:
  `CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM`
  with `CLONE_SETTLS`, `CLONE_PARENT_SETTID`, `CLONE_CHILD_SETTID`,
  `CLONE_CHILD_CLEARTID` optional. `CLONE_THREAD` without
  `CLONE_SIGHAND`, or `CLONE_SIGHAND` without `CLONE_VM`, is -EINVAL
  (`clone(2)`); a thread that would share memory but not descriptors
  or handlers (`CLONE_VM` without `CLONE_THREAD` or `CLONE_VFORK`) stays
  refused by name, -ENOSYS; no free slot is -EAGAIN.
- `exit` (60) ends the calling thread only: when the group lives on,
  the kernel writes 0 at its clear-child-tid address and wakes one
  futex waiter there (`set_tid_address(2)`), and the slot is free at
  the next reap with no zombie. The last thread's `exit` ends the
  process with that status. `exit_group` (231) ends every thread of the
  group at once and leaves `code << 8` for the parent. A fault or a
  fatal signal ends the group the same way with the signal's number.
  A leader that exits while its threads live is kept (the pid and the
  area are its slot's) until the last one ends.
- `wait4`/`waitid` see processes only: a thread is never a child to
  wait for; a child's parent is the group, and any thread of it may
  wait.
- `execve` from a group ends every other thread first; the caller
  keeps the pid.
- `getpid` answers the group's pid, `gettid` and `set_tid_address` the
  thread's tid.
- The second thread's memory: `mmap` with `PROT_NONE` **reserves**
  addresses and takes no frame; `mprotect` to a readable protection
  backs the pages it covers. The 128 MiB reservation costs no frame
  and the 2 MiB stack costs 512 at its `mprotect`. `madvise`:
  `MADV_GUARD_INSTALL` honoured (the pages lose user access, as a
  guard must fault; a reserved page already faults), `MADV_DONTNEED`
  honoured (the pages read zero again), the pure hints answered 0, the
  rest refused by name, -EINVAL. Predicted unused by this pelt (glibc
  2.39 makes no `madvise` here).

### P2. The futex table

- **No table**: a waiter is a thread in a new state, and its slot
  carries the key, the bitset and a sequence number; a wake walks the
  sixteen slots and readies waiters in the order they began to wait.
  The bound is the slot count.
- **The key** is the physical address of the 32-bit word (the caller's
  tables walked): two threads of a group meet on it, two processes
  never do, since PAX shares no frame between address spaces. So
  `FUTEX_PRIVATE_FLAG` changes nothing here, and a futex without it is
  the same futex.
- **On one CPU** the compare-and-wait needs no lock: a system call
  runs with interrupts off from entry to the switch, so no waker can
  run between the read of the word and the wait.
- Taken: `FUTEX_WAIT` (a relative timeout), `FUTEX_WAKE`,
  `FUTEX_WAIT_BITSET` (an absolute one, CLOCK_MONOTONIC, or
  CLOCK_REALTIME with `FUTEX_CLOCK_REALTIME`), `FUTEX_WAKE_BITSET`;
  -EAGAIN when the word is not the value, -ETIMEDOUT, -EINTR, -EFAULT
  for an unreadable word or timespec, -EINVAL for a word off a 4-byte
  boundary, a zero bitset or a bad timespec. Every other operation
  (FD, REQUEUE, CMP_REQUEUE, WAKE_OP, the PI family, WAIT_REQUEUE_PI,
  LOCK_PI2) is refused by name, -ENOSYS.

### P3. Signal delivery

- **When**: a pending, unblocked signal is taken when its thread is
  about to return to ring 3, from a system call, an interrupt or a
  switch in, and nowhere else. A thread waiting in a system call
  (`read` of the console or a pipe, `wait4`, `futex`, a sleep) is made
  ready by a signal that will run a handler or end it; a signal whose
  action is to be ignored wakes nobody.
- **Which thread**: a signal for a thread (`tgkill`, a fault, SIGPIPE)
  is that thread's. A signal for the process (`kill`, the terminal,
  SIGCHLD) is taken by the leader when the leader has it unblocked,
  else by the lowest-numbered thread that has (Linux: "an arbitrary
  thread", and measured, the first); with every thread blocking it, it
  stays pending for the process.
- **Masks** are per thread, inherited at `clone`, kept across `execve`;
  SIGKILL and SIGSTOP are never blocked. Pending sets: one per thread
  and one per process; one instance per signal (real-time signals do
  not queue: named drift).
- **Order**: the lowest-numbered pending signal first, and all that
  are pending before the thread runs, so (as on Linux, to be measured)
  the handler of the highest-numbered runs first and the others as
  each returns.
- **The frame** goes on the thread's own stack (no `sigaltstack`:
  -ENOSYS, and `SA_ONSTACK` is accepted and means nothing), below the
  128-byte red zone, top down: the extended state as XSAVE wrote it
  (the FXSAVE image with the software bytes at 464 — magic
  0x46505853, the sizes, XCR0's features — then the XSAVE header and
  AVX's part, then the magic 0x46505845), 64-aligned; the 128-byte
  siginfo; the ucontext (flags, link, the stack triple, the sigcontext
  with every general register, RIP, RFLAGS, the selectors, the old
  mask, CR2 and the pointer to the extended state; then the mask); the
  restorer's address, where `ret` will find it, with RSP + 8 a
  multiple of 16. The handler starts with RDI the number, RSI the
  siginfo, RDX the ucontext, RAX 0, the mask grown by `sa_mask` and
  the signal itself (unless `SA_NODEFER`), the action reset under
  `SA_RESETHAND`. `rt_sigreturn` reads the frame at RSP, restores every
  general register, RIP, RFLAGS (the user-settable bits), the mask and
  the extended state (checked: a bad XSAVE header or MXCSR ends the
  process with SIGSEGV rather than fault in ring 0), and leaves by
  IRETQ. A frame that does not fit the stack ends the process with
  SIGSEGV.
- **`SA_RESTART`**: a `read` of the console, a pipe or a socketpair, a
  `write` to a pipe, `wait4`, `waitid` and `futex` wait (its deadline
  kept) run again after a handler installed with it; without it they
  answer -EINTR. `clock_nanosleep` and `nanosleep` answer -EINTR
  always, the time left written for a relative sleep. A receive with
  a timeout answers -EINTR always (`signal(7)`).
- **Default actions**: terminate (the process ends, its wait status
  the signal's number; no core, so the core bit stays clear), ignore
  (SIGCHLD, SIGURG, SIGWINCH), and stop and continue **refused by
  name**: a SIGSTOP, SIGTSTP, SIGTTIN or SIGTTOU whose action is the
  default is dropped with a line, SIGCONT is dropped silently. pid 1
  takes only the signals it has a handler for (`kill(2)`).
- **`kill`** (62): a pid is that process; 0 and a negative group are
  every process (PAX has one group); -1 every process but pid 1 and
  the caller; signal 0 only checks; -ESRCH, -EINVAL. **`tgkill`**
  (234) and `tkill` (200): that thread. siginfo's `si_code` is SI_USER
  (0) or SI_TKILL (-6) with the sender's pid.
- **SIGPIPE** becomes a signal for the writing thread (SI_USER, its
  own pid, measured): the default still ends the process with status
  13, a handler now runs and the write answers -EPIPE. **SIGCHLD** is
  raised for the parent when a child ends, with CLD_EXITED or
  CLD_KILLED, the pid and the status.
- **Faults**: an exception in ring 3 raises its signal for the
  thread (SIGSEGV, SIGILL, SIGFPE, SIGBUS, SIGTRAP as px14 maps
  them) with `si_addr`; a handler runs, the default ends the process
  as today.

### P4. Ctrl-C without job control

- The line discipline's ISIG is set at start (Linux's default): VINTR
  (Ctrl-C) raises SIGINT, VQUIT (Ctrl-\) SIGQUIT, VSUSP (Ctrl-Z)
  SIGTSTP, each echoed as `^C`, `^\`, `^Z` (ECHOCTL) with the line
  being edited and the unread input discarded (NOFLSH clear).
- **"Foreground" is every process**: PAX has one session and one
  process group, the console their controlling terminal, so the signal
  is raised for each process, pid 1 included (which takes it only with
  a handler). pelt (no handler-less death as pid 1, a handler for INT)
  runs its handler; a child that kept the default ends, status 2.
- What Linux does differently: it signals the terminal's foreground
  process group only (`tcsetpgrp`), keeps sessions, and stops a
  background process that reads the terminal (SIGTTIN). With a shell
  that makes no process group — this pelt asks for none — the two
  agree: on Linux, measured, pelt and its child both receive the
  SIGINT.

### P5. Calls added, and each refusal's errno

- New numbers: `rt_sigreturn` (15), `sched_yield` (24), `madvise` (28),
  `sendfile` (40: a file of the initramfs to any descriptor),
  `readlink` (89), `rt_sigpending` (127), `futex` (202), `set_robust_list`
  (273: the head kept, nothing walked at exit: named),
  `copy_file_range` (285: -EINVAL always, as Linux answers a
  destination that is not a regular file, and PAX has none writable);
  `kill` (62), `tkill` (200), `tgkill` (234) answer; `exit` (60) ends a
  thread; `gettid`, `set_tid_address`, `getpid` answer thread and
  group; `clone`/`clone3` take the thread flags; `prctl` takes
  `PR_SET_NAME`; `statx` takes `AT_EMPTY_PATH` on any descriptor;
  `readlinkat`/`readlink` answer `/proc/self/exe` (the path the
  program was started by) and -EINVAL for what is not a link.
  CLOCK_REALTIME, `time` and `gettimeofday` read the CMOS clock at
  boot plus the ticks since. 11 new numbers ± 3.
- Refused by name: `futex`'s other operations -ENOSYS; a stop
  signal's default action (a line, the signal dropped); `clone` flags
  as P1; `madvise` advice PAX does not know -EINVAL. Still -ENOSYS
  and logged once: `rseq` (334), `sigaltstack` (131),
  `rt_sigsuspend`, `rt_sigtimedwait`, `signalfd`, `timer_create`,
  `setitimer`, `alarm`.

### P6. What moves

- **Every kernel's bytes** (each links kernel/sched) and so every ISO;
  the tour's frame counts and ending b's `rip`.
- `tests/mpx3-shell`: S4's -ENOSYS set becomes `334` alone (273
  answers); procs' `kill` refusal (62, -38) goes, and its SIGPIPE line
  keeps its text; new sessions `shell-long` (item 1) and `shell-sigs`
  (item 5), and a probe session against Linux.
- `tests/mpx3-console`: the sessions that type Ctrl-C as a byte move
  (ISIG is set on both sides now); `tests/mpx3-boreutils`: `cat` asks
  `copy_file_range` and `sendfile`; the run list's verdicts do not
  move. `tests/mpx3-speaker` types into the new pelt: its transcripts
  do not move.
- The px23 files do not move; `mpx4-*` verdicts do not move.
- No downstream repo moves: pax consumes pelt and boreutils at pins.

### P7. Numbers

- Boot to pelt's prompt on nomad-1 (TCG): **2.1 s ± 0.5** (px17
  measured 1.7–1.9 s; the new pelt backs 512 frames for its second
  thread's stack and is 0.96 MiB larger).
- The soak: 10,000 threads made and joined and 10,000 signals
  delivered to a handler, with the slot count, the free frames, the
  user stack pointer and the break the same after as before; under
  TCG in under 120 s (a guess).
- At least 100 KVM boots on hasu for the lane's suites, all green.
- Planted breaks: a signal frame that restores one callee-saved
  register wrong reddens the probe session on every leg and nothing
  else; a futex wake that wakes nobody reddens the probe session and
  `shell-sigs` (pelt never reaches its prompt) within each boot's
  deadline, and nothing else.

### P8. What fails first

- The new pelt on trunk's kernel: `clone3` with the thread flags is
  refused (`CLONE_VM without CLONE_VFORK`, -ENOSYS) and pelt does not
  reach a prompt: either it ends with a message of its own or it
  waits forever on a futex that answers -ENOSYS (a named guess: it
  ends, status not 0).
- The new boreutils on trunk's kernel: `ls -l /bin` prints, and
  differs from Linux in its `total` line and its dates; `readlink
  /proc/self/exe` prints nothing and fails.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: a thread is a slot in its leader's group, sharing the space, the area and the pid; its own tid, stack, frame, FS base, x87/SSE state, mask, pending set, clear-child-tid word, name | as built (`kernel/sched`, `kernel/process`), and every line of the probe's `ids:` and `exit:` cases is Linux's (`notes/px26/session-probes.{pax,linux}.txt`) |
| P1: `exit` ends one thread, zeroes the clear-child-tid word and wakes its futex; the last thread's `exit` ends the process with that status; `exit_group` ends all | **right**: `pthread_join` returns on PAX only because of that wake (plant B, below, hangs it); "main's exit(4) with a thread still running, which exits 6 later: status 0x600" on both |
| P1: `PROT_NONE` reserves and takes no frame; the 128 MiB costs none, the 2 MiB stack 512 | **right** as far as measured: the probe reserves 256 MiB with `PROT_NONE` and makes threads with 8 MiB stacks, and the soak's census has the whole process at 332 frames (64153 free before it, 63821 during); trunk's `mmap` would have taken 65536 frames for that reservation alone. pelt's own frame count at its prompt was not measured |
| P1: `madvise` unused by this pelt | **right** (no call 28 in either strace); the probe exercises MADV_DONTNEED and the guard pair |
| P2: no table; the key the word's physical address; **`FUTEX_PRIVATE_FLAG` changes nothing** | **wrong on the flag**: on Linux a wake without it does not reach a private waiter (the probe's "a wake without the private flag reaches a private waiter 0"), so the flag is a bit of the key (`kernel/futex`). The rest as predicted: waiters woken longest-waiting first ("in the order 0 1 2" on both) |
| P2: the errnos | **right**, each on both: -11, -110 (a timeout, and a deadline already past), -22 (a zero bitset, a word off a 4-byte boundary, a bad timespec), -14, -38 for an operation that does not exist |
| P3: taken at the return to ring 3; a self-sent signal delivered before `kill` returns | **right** ("the handler had run when it returned 1") |
| P3: the leader takes a process's signal when it has it unblocked, else the lowest-numbered thread; all blocking: it waits | **right** ("main took 10, the other 0; main blocking: main 0, the other 10; both blocking: delivered while blocked 0, then main 1") |
| P3: the lowest-numbered first, so the highest-numbered handler runs first | **right** ("in the order 15 12 10") |
| P3: the frame's layout | **right**, and measured where the prediction was silent: the ucontext 8 bytes above the handler's RSP and the siginfo 304 above that, the extended state above both on a 64-byte boundary, `uc_flags` 7, a zero stack triple (flags 0, not SS_DISABLE), the old mask in both `oldmask` and `uc_sigmask`; **not predicted**: the handler starts with a fresh x87/SSE state (MXCSR 0x1f80, FCW 0x037f) and the interrupted one comes back at its return. The selectors differ by name (PAX 0x23/0x1b, Linux 0x33/0x2b): the probe prints their ring |
| P3: SA_RESTART restarts a pipe or console read, a pipe write, wait4, waitid and **a futex wait "its deadline kept"** | **half wrong on futex**: a futex wait with NO timeout runs again; one with a timeout answers -EINTR even under SA_RESTART (measured), so no deadline is kept anywhere. The others right |
| P3: sleeps answer -EINTR always, the time left written | **right** (`nanosleep` and `clock_nanosleep`, both ways) |
| P3: default actions; pid 1 spared; stop refused by name | **right**: 0xf, 0x9, 0xa wait statuses; the refusal line for SIGTSTP is tests/mpx3-threads' T3. Not predicted and measured: an ignored signal that is also blocked stays pending ("pending while blocked 0x200"); SA_RESETHAND resets the handler and keeps the flags |
| P3: SIGPIPE to the writing thread, SI_USER from itself; SIGCHLD with CLD_*; faults to handlers with `si_addr` | **right**; not predicted: a fault whose signal is ignored, or blocked and handled, still ends the process (0xb on both) |
| P4: ISIG; every process is the foreground; pelt handles, a child dies with status 2 | **right** (`$?` 130, `user: sleep pid 3 killed: SIGINT`); Ctrl-\ added to the session (SIGQUIT, which pelt ignores at its prompt) |
| P5: 11 new numbers ± 3 | **9**: 15, 24, 28, 40, 89, 127, 202, 275 (`splice`, not predicted: `cat` asks it when its input is no file), 326 (`copy_file_range`; the prediction wrote 285, which is `fallocate`). **`set_robust_list` stays -ENOSYS**, against the prediction: `tests/mpx4-udp`'s U4 (px23's file) holds the -ENOSYS set to `273 334`, and glibc tolerates it for threads as for a process |
| P6: every kernel's bytes move; mpx3-shell's -ENOSYS set becomes `334` | the set **stays `273 334`** (above); procs' `kill` refusal is gone |
| P6: mpx3-console's Ctrl-C sessions move; mpx3-boreutils' verdicts do not | console **right, and more**: its Linux side had to run the program as pid 1 (`--pid1`), since Ctrl-C now kills a program that is not init; boreutils **wrong**: `ls -l /etc` is a long listing with bu20 where bu18 refused `-l`, so its Linux side needed the tree owned and dated as the initramfs says |
| P6: nothing else | **not predicted**: the shell's initramfs is 170 MiB with thirteen programs, and under OVMF Limine cannot place it in a 256 MiB machine (`PANIC: High memory allocator: Out of memory`); `tests/mpx3-shell` boots with 512 MiB |
| P7: boot to pelt's prompt on nomad-1 2.1 s ± 0.5 | **2.45 s** (five boots of the quiet image, 2.44 to 2.47; 2.82 with narration), inside the band at its edge; the image is 175 MB where px17's was smaller, and this lane did not re-time trunk's image with the same script |
| P7: the soak under 120 s under TCG | **right**: about 30 s a boot on kasumi (the suite's eight boots in 235 s) |
| P7: plant A reddens the probes on every leg and nothing else | **right in what, wrong in how much**: the suite stops at the first failing probes boot, so one leg ran: "registers not put back 1 r12" |
| P7: plant B reddens the probes and `shell-sigs` | **half wrong**: the probes hang at their first `pthread_join` and fail at the boot's 300 s deadline; **pelt does not need the wake** — every futex wait it makes carries a deadline or is re-armed by its own state, and all ten shell sessions stayed byte-identical with the plant in (kasumi, `notes/px26/kasumi-plant-b-rehearsal.mpx3-shell.out`) |
| P8: the new pelt on trunk's kernel: `clone3` refused, no prompt | **right**: `syscall 435: refused: CLONE_VM without CLONE_VFORK`, glibc's fallback `clone` (56) refused the same, `futex` (202) and `writev` (20) -ENOSYS, `tgkill` refused twice, and init ended without an exit status; no prompt (`notes/px26/kasumi-red-new-pelt-on-trunk-kernel.mpx3-shell.out`) |
| P8: the new boreutils on trunk's kernel: `ls -l` differs in its `total` and its dates; `readlink /proc/self/exe` fails | **right** (`notes/px26/kasumi-red-item1-tests-on-trunk-kernel.mpx3-shell.out`: S2 differs from the `total` line on; -ENOSYS for 89, and for 40, 275 and 326 in every session that runs `cat`) |

## 4. Evidence index

### The Linux side

- The straces of pax's own builds: `notes/px26/pelt-b32bebc-sigs.strace` (`b4169a2e…`), `pelt-b32bebc-long.strace` (`ed4893d9…`), `bore-870815c-{ls,stat,readlink,env}.strace`, the keys and `strace-sigs.sh` beside them (kasumi, `px13-ubuntu`, glibc 2.39, strace 6.8, Linux 7.2.8).
- Every PAX transcript's reference is taken live by the suite: `tools/linux-tty --root --pid1` (the same binaries chrooted in the tree the initramfs is made from, a pseudo-terminal with ISIG set, the program pid 1 of a fresh pid namespace).

### The probe (`user/elf/threads.c`, one static file on both)

- Linux and PAX, 48 compared lines, `cmp` equal: `notes/px26/session-probes.{linux,pax}.txt` (kasumi, native BIOS; the two `~` lines differ by design: FUTEX_REQUEUE and a stop, which PAX refuses by name and T3 holds to those two refusals).
- In CI the same comparison runs against the runner's own Linux (Ubuntu 24.04, its glibc and kernel), on both tiers, BIOS and UEFI: job `mpx3-threads` of the run at the head.

### The sessions

- `shell-long` (item 1) and `shell-sigs` (item 5), PAX against Linux, `cmp` equal: `notes/px26/session-shell-{long,sigs}.{pax,linux}.txt`; the PS/2 leg's whole boot under UEFI: `kasumi-native-uefi-shell-sigs-ps2.serial.log`. `tests/mpx3-shell` S2 holds every leg to it: 10 sessions on 2 tiers and 2 firmwares.

### The soak

- `notes/px26/kasumi-native-bios-soak.serial.log`: four thread census lines (2500 to 10000 made), each `slots busy 4, frames free 63821`; signal census lines from 2500 to 10000 (and 12000 after the round trip), the first four each `slots busy 4, frames free 63821, this frame at 0x00007fffffffe538`; the program's own lines (`session-soak.{pax,linux}.txt`): 10000 threads joined, results sum 49995000, the break moved 0 bytes, 10000 signals handled, the handler's stack moved 0 times, 2000 more into a spinning thread with 0 registers not put back; and the frames line after it: every frame back.

### Red first

- At trunk's kernel (`0cc43be`), on kasumi: the head's tests with the new pelt — no prompt, `clone3` refused (`kasumi-red-new-pelt-on-trunk-kernel.mpx3-shell.out`); item 1's tests with bu20's boreutils — `shell-long` S2 and S4 (`kasumi-red-item1-tests-on-trunk-kernel.mpx3-shell.out`).
- Planted break A (`rt_sigreturn` does not put %r12 back), commit 3617a09: CI run **38131582865**, job mpx3-threads **114446842823** the only failing job of 21, red 1 min 38 s after it started (`T1 native bios probes … registers not put back 1 r12`, then `stopped early`). Reverted in ce2f444. Rehearsed on kasumi first: `notes/px26/kasumi-plant-a-rehearsal.mpx3-threads.out`.
- Planted break B (a futex wake wakes nobody), commit 186947c: CI run **38131619277**, job mpx3-threads **114446948287** the only failing job of 21, red 6 min 55 s after it started (`no line matching /halt/ within 300s`, then `stopped early`). Reverted in acb7b7e. Rehearsed on kasumi first: `notes/px26/kasumi-plant-b-rehearsal.mpx3-threads.out`.
- The fail-fast in `tools/qemu-halt` (a typed boot whose first prompt never came stops the run's later typed boots) is seen in `kasumi-red-new-pelt-on-trunk-kernel.mpx3-shell.out`: the first session waits out 180 s, the next nine are `not booted`.

### Boot counts

BOOTS

### Item 1 alone

PIN

### CI

CIHEAD

### Drift from the contract, reported

1. **`set_robust_list` is not answered** (it stays -ENOSYS, logged once): px23's `tests/mpx4-udp` asserts the -ENOSYS set, and that file is not this lane's. One line there and one in `kernel/user` would answer it.
2. **`MADV_GUARD_INSTALL` is honoured, and no program in the image asks it**: the container's and the runner's glibc is 2.39, which guards a thread's stack with `mprotect`. The probe asks it directly (`~guard`, T2, on PAX; the line is not compared, since a Linux before 6.13 answers -EINVAL).
3. **The shell image needs 512 MiB under UEFI** (170 MiB of programs). BIOS still boots it in 256.
4. **`tools/linux-tty` keeps ISIG**, and `tests/mpx3-console`'s Linux side runs its program as pid 1 under `sudo -n`, as mpx3-shell's did already.
5. **A kernel line can land in the middle of a program's line** (`^Cuser: sleep pid 3 killed: SIGINT …`): the terminal echoes a control key with no newline. The suites cut such a line out with its newline; a quiet boot prints none.
6. **Item 1 is not one commit** but eleven (`0f8b57e` to `8696139`) and a twelfth it turned out to need (`3c75386`, the 512 MiB); branch `px26-pin` on origin is those alone on trunk, for whoever wants item 1 first.
7. **Not done, by name**: job control (process groups, sessions, `tcsetpgrp`, stopped processes: a stop's default action is refused); `sigaltstack`, `rt_sigsuspend`, `rt_sigtimedwait`, `signalfd`, timers; `rseq`; queued real-time signals; SIGCHLD's auto-reap under SIG_IGN or SA_NOCLDWAIT; a `PROT_NONE` page that once had a frame faults with the present bit set where Linux's does not; SMP.

### Filed

Nothing upstream: nothing in wolf, pelt, boreutils or QEMU stood in the way.

## 5. Done-when

DONE

