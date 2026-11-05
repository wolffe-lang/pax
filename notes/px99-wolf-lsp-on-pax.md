# px99 — `wolf lsp` on PAX: the language server runs on the image

PAX's dev image ships `/usr/bin/wolf` 0.2.36, the musl-static compiler `tools/mkwolf` builds from wolf-lang's
`v0.2.36` tag, and that compiler carries the `lsp` subcommand: the Language Server Protocol over standard input and
output, on rust-analyzer's `lsp-server` transport (its own reader, writer and dropper threads), crossbeam channels and
a thread per diagnostics publication. Nothing had run it on PAX. This lane drives a whole session against it on PAX
under QEMU, and the same session against the same binary on Linux, and holds the frames to each other.

**What it found:** `wolf lsp` runs on PAX unchanged and asks nothing PAX does not already serve. Every frame of both
sessions, both ways, is byte-identical to Linux on every leg (both compiler tiers, both firmwares), as root and as
`pax`, with no normalisation of the frames at all. No kernel change was needed, and nothing was filed upstream. The
new suite, `tests/mpx5-lsp`, keeps the session as a row.

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any system. The program under test was read as a program:
  wolf-lang's `crates/wolf_lsp` and the driver's `lsp` entry at `v0.2.36`, the `lsp-server` 0.10.0 crate's stdio
  transport and framing, and wolf-lsp's `lspconf` scripts and recorded transcripts (recorded at the same pin). The
  editor client yew will port, sagitta's `src/mod/lsp/client.c` and `src/edit/job.c`, was read for how an editor starts
  and watches a server (three pipes and an exec-status pipe, `fork`, `setpgid`, a self-pipe for SIGCHLD, a group kill).
- **References:** the LSP 3.17 specification (base protocol framing, lifecycle, `textDocument/publishDiagnostics`),
  `pipe(2)`, `fork(2)`, `execve(2)`, `poll(2)`, `wait4(2)`, `setpgid(2)`, `kill(2)`, `sigaction(2)`, `signal(7)`,
  `futex(2)`, `clock_gettime(2)` and the uapi headers' numbers and layouts.
- **Black box:** the same client and server on Linux under `strace -f` (strace 6.8), for the calls the server makes
  (§4.4). `docs/SOURCES.md` lists it all under px99.

## 2. Inputs, verified

- **Base:** pax trunk `411fc9f5`. The work began on `37217ba0` and was rebased once, with no conflict; shas from before
  the rebase are named as such, and that head is kept on origin as `px99-prerebase`.
- **The server:** `/usr/bin/wolf`, sha256 `2df1fb7660ce27dd6bd0d8c7395abec74bb399824842f89b8a407060be80ab59`,
  16,257,584 bytes, and `wolf-cimport-worker` `11850e70…`, the bytes `user/wolf.sums` records for `tools/mkwolf`'s
  build of wolf-lang `v0.2.36` (`5adf3d91`, Rust 1.97.1, `x86_64-unknown-linux-musl`). Three earlier builds of the
  same pin, made apart, agree to the byte, so the development runs used one of them (the suite checks the bytes
  against `user/wolf.sums` whichever way they came, and CI builds its own). `wolf --version` says
  `wolf 0.2.36 (wolfgang, pin 5adf3d9)`, the initialize answer `serverInfo` `wolf-lsp` `0.2.36`.
- **The std:** `tools/mkwolf-std` at `WOLF_STD_REV` `78b9d3cb`, at `/usr/share/wolf/compiler-std` with `WOLF_STD`
  naming it, where and how the dev image keeps it.
- **The client:** `user/elf/lspc.c`, built by `tools/mklspc` (C with no libc, static, no PIE): 15,528 bytes at the head.
  `/bin/as` from `tools/mkas`, `fb824591…`.
- **The kernel:** `kmain_console`, the dev image's kernel, at both tiers, built by the kernel's compiler
  (`kernel/wolf.pin`, wolf 0.2.35).
- **Hosts:**

  | role | hardware | how |
  |---|---|---|
  | builds, the Linux side, KVM boots | an x86-64 Linux laptop, 8 cores and 16 threads | one slot's 8 threads, in an Ubuntu 24.04 container (clang, lld 18, QEMU 8.2.2, OVMF, xorriso); the Linux side in throwaway containers through `tools/linux-tree` |
  | TCG boots | the same | the same container with no `/dev/kvm`, as CI's runners boot |
  | git, editing, the Python rows | an arm64 Mac | no build |

## 3. Prediction, scored

The prediction was committed first (`318d2a7a`; `faf8e5d4` before the rebase) and is kept below as written. Scored:

| | predicted | measured | |
|---|---|---|---|
| P1 | nothing new asked; threads for the transport and each publication; futex bitset waits with deadlines, wakes and musl's own; `sched_yield`; pipes; the workspace's reads; `exit_group(0)` | as predicted, and more: the server also sizes a worker pool from `sched_getaffinity` and the cgroup quota (`/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`, `/sys/fs/cgroup/cgroup.controllers`), 13 threads in open-fix on the reference's 8 CPUs; one plain FUTEX_WAIT; on PAX no -ENOSYS from it at all, and none refused (§4.4) | right on every call PAX had to serve; the pool and the cgroup reads not foreseen |
| P2 | the initialize answer, one E-coded error, the clearing after the debounce, `null`, status 0, one SIGCHLD; the hung server killed, signal 9 | E0401 (`this is \`str\`, but \`n\` is declared as \`int\``) at the literal, the related location at `int`; cleared 110 ms after the edit; the rest as predicted (§4.1) | right |
| P3 | byte-identical, no normalisation | byte-identical on every leg and every run; the only lines left out are the client's `time:` lines, by name (§4.2, §4.3) | right |
| P4 | status 0, one SIGCHLD, none for a thread; signal 9 for the killed server, every thread ended | so on every leg, as root and as `pax` | right |
| P5 | tens of ms on Linux, within ten times on PAX under KVM | under 1 ms on Linux; 0 to 20 ms on PAX, in whole 10 ms steps: PAX's monotonic clock is its 100 Hz tick (§4.5) | the scale was wrong on Linux; on PAX right within the clock's grain |
| P6 | if a gap, a timed futex wait first | none: the debounce's timed wait (`ETIMEDOUT` on Linux) wakes on time on PAX, the publication comes 110 ms after the edit | no gap |
| P7 | nothing typed, so no prompt | so | right |
| P8 | a plant in the witness's expectation turns LSP2 red, LSP1 green | to be shown by the plant's record (§4.8) | in the PR |
| P9 | pipes, poll over the terminal and pipes, SIGCHLD by self-pipe, a group kill: all served | all shown, and EPIPE for a write to a server that has gone (§4.6) | right |

The prediction as committed:

- **P1, the calls.** `wolf lsp` asks nothing PAX does not already serve. Beyond what every wolf process asks
  (`tests/mpx5-wolf`'s census), the server's own paths are:
  - **threads:** musl's `pthread_create` for the transport's three named threads (reader, writer, dropper) and one
    detached thread per publication: an anonymous `mmap` for the stack and its guard, `mprotect`, `clone` (56) with
    CLONE_VM, FS, FILES, SIGHAND, THREAD, SYSVSEM, SETTLS, PARENT_SETTID, CHILD_CLEARTID and DETACHED; in each new
    thread Rust's alternate signal stack (`mmap`, `mprotect`, `sigaltstack`) and `prctl(PR_SET_NAME)` for the named
    three;
  - **waits:** `futex` FUTEX_WAIT_BITSET with the private flag and an absolute CLOCK_MONOTONIC deadline (the main
    loop's `recv_timeout`: an hour when idle, 100 ms for the `didChange` debounce, a second in the handshake),
    FUTEX_WAKE, and musl's own FUTEX_WAIT and FUTEX_WAKE for its locks and joins; `sched_yield` from the channel's
    back-off; `clock_gettime` (PAX has no vDSO, so a system call every time);
  - **pipes:** the reader thread blocked in `read(0)` of up to 8 KiB while the main thread waits on a futex; each
    frame written as two `write(1)`s, the header and then the body;
  - **files:** the workspace read from the opened file's directory (`openat`, `getdents64`, `statx` or `fstat`,
    `read`, `close`), `WOLF_STD` checked for a directory, `/proc/self/exe` read for the std beside the binary;
  - **the end:** after `exit` the reader returns, the main loop returns 0, `IoThreads::join` waits on each thread's
    cleared child-tid word, a detached thread unmaps its own stack and exits, and `exit_group(0)`.
  No -ENOSYS but `set_robust_list` (273) and `rseq` (334), as for every wolf process, and no `refused:` line.
- **P2, the Linux reference.** The session the client types (§4) answers, in order: the `initialize` response
  (`serverInfo` `wolf-lsp` 0.2.36, `positionEncoding` utf-16 for a client that names none, full sync); one
  `publishDiagnostics` for the opened file carrying exactly one error, the type error by its code; after the
  `didChange` that fixes it and the 100 ms debounce, one `publishDiagnostics` with an empty list; `null` for
  `shutdown`; then end of file on the server's output, nothing on its standard error, exit status 0 and one SIGCHLD.
  In the hung-server session the deadline passes with no publication, the client kills the server's process group,
  and the server ends by signal 9 with one SIGCHLD.
- **P3, PAX against Linux.** Every frame byte-identical, both directions, with **no normalisation at all**: the Linux
  side runs the same tree at the same paths, so the file URIs are the same bytes. The only lines that differ are the
  client's `time:` lines, left out by name.
- **P4, the exit and the signals.** On both: exit status 0 after `shutdown` and `exit`; one SIGCHLD per server, none
  for a thread's end; signal 9 for the killed server, every thread of it ended.
- **P5, time.** Time to the first diagnostics, the client's clock from the `didOpen` write to the publication's last
  byte: tens of milliseconds on Linux in the container, within ten times that on PAX under KVM, and far slower under
  TCG. Evidence only, never a bound.
- **P6, where a gap would be, if there is one.** The likeliest, in order: a timed futex wait that does not wake at
  its deadline (the debounce's publication never comes, and the `didChange` step hangs); a pipe read blocking one
  thread while its siblings wait on futexes; musl's detached thread unmapping its own stack before its `exit`; a group
  kill that leaves a thread of the server running.
- **P7, the friendly prompt.** Nothing is typed. The client is the run list's program, so no shell starts and pelt's
  prompt never arises, as root or as `pax`.
- **P8, the plant.** One hunk that changes what the session's own witness expects (the first publication's count of
  diagnostics off by one) turns that row red by name, and the byte-for-byte row stays green: PAX and Linux still agree.
- **P9, what yew needs.** A child with three pipes and an exec-status pipe, `poll` over the terminal and the pipes
  together, SIGCHLD through a self-pipe, `setpgid` and a group kill: all served, and shown working by the rows.

## 4. Evidence index

### 4.1 The session, and the suite that keeps it

`tests/mpx5-lsp` builds one image: `kmain_console` with `/usr/bin/wolf` and its worker, the compiler's std,
`/usr/bin/lspc`, `/bin/as`, the two sessions under `/usr/share/lsp` (written by `tests/mpx5-lsp.d/session.py`) and the
workspace `/home/pax/lsp` holding `typed.lu` (`pax`'s, 1000:1000). Its run list types nothing:

| run | the line |
|---|---|
| root-open-fix | `/usr/bin/lspc /usr/share/lsp/open-fix.lsp` |
| root-hung | `/usr/bin/lspc /usr/share/lsp/hung.lsp` |
| pax-open-fix | `/bin/as 1000 1000 /usr/bin/lspc /usr/share/lsp/open-fix.lsp` |
| pax-hung | `/bin/as 1000 1000 /usr/bin/lspc /usr/share/lsp/hung.lsp` |

The client starts `/usr/bin/wolf lsp` in `/home/pax/lsp`, the way sagitta's client starts a server: three pipes and a
close-on-exec pipe on which the child reports a failed `execve`, `fork`, and in the child `setpgid(0, 0)`, `chdir`, the
`dup2`s and `execve`; the parent's read ends non-blocking. Every wait is one `poll` over the terminal (descriptor 0),
the server's output and error and a SIGCHLD self-pipe, with a deadline. It ignores SIGPIPE, as an editor does. It
prints every frame it sends and reads, one line each with its length, so the transcript is the protocol both ways.

- **open-fix:** `initialize` (a client that declares no capabilities) and `initialized`; `didOpen` of `typed.lu`,
  whose `let n: int = "seven"` is the type error; the diagnostics; a full-text `didChange` to `fixed.lu` (`= 7`),
  never saved; the diagnostics again; `shutdown`, `exit`, the input closed, the server's end.
- **hung:** the same, with the compiler's own test hook `WOLF_QUERY_TEST_SLOW_MS` (wolf_query's `TEST_SLOW_ENV`: each
  query sleeps first, in 5 ms slices) at ten minutes: no diagnostics within 3 s, so the client kills the server's
  process group with SIGKILL and reaps it, then writes one more frame to the server that has gone.

The open-fix transcript, every leg (from `tests/mpx5-lsp.d/open-fix.good`, the Linux side's, which PAX's equals):

```
s2c 543 {"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"diagnostics":[{"code":"E0401",
  "message":"this is `str`, but `n` is declared as `int`\nfound `str` here\nnote: expected `int`, found `str`",
  "range":{"end":{"character":24,"line":4},"start":{"character":17,"line":4}},"relatedInformation":[{"location":
  {"range":{"end":{"character":14,"line":4},"start":{"character":11,"line":4}},"uri":"file:///home/pax/lsp/typed.lu"},
  "message":"the annotation is here"}],"severity":1,"source":"wolf"}],"uri":"file:///home/pax/lsp/typed.lu"}}
s2c 126 {"jsonrpc":"2.0","method":"textDocument/publishDiagnostics","params":{"diagnostics":[],"uri":"file:///home/pax/lsp/typed.lu"}}
s2c 38 {"jsonrpc":"2.0","id":2,"result":null}
exit: status 0
sigchld: 1
```

(The first frame is wrapped here; the transcript has it on one line.) The hung transcript ends `deadline:
first-diagnostics not seen within 3000 ms`, `kill: the server's process group, SIGKILL: 0`, `exit: signal 9`, the
frame after the reap, `lspc: write to the server failed -32` (EPIPE), `sigchld: 1`.

The rows, per tier, firmware and run:
- **LSP0** the build: every program static, wolf the bytes `user/wolf.sums` records, the std the pin's, the image, and
  the container's four runs.
- **LSP1** the run's transcript, from `lspc: begin` to `lspc: end`, byte-identical to the container's. **The one
  normalisation, named in the row:** the client's `time:` lines, the only lines that measure a machine, are left out
  of both sides. The frames themselves are not touched: the container runs the same tree at the same paths.
- **LSP2** the session's own witness, `tests/mpx5-lsp.d/rows.py`, from this repository's files alone: the bodies sent
  are the session's; the initialize answer is wolf-lsp 0.2.36 with the capabilities wolf-lsp's own recordings hold at
  the same compiler pin for a client that declares none; one E0401 error from `wolf`, its range the literal and its
  related location the annotation, both found in `typed.lu`; the clearing; `null`; status 0 or signal 9; one SIGCHLD;
  EPIPE; nothing on the server's standard error, nothing read from the terminal. So a client or a server broken the
  same way on both sides, which LSP1 cannot see, is still red. Before any boot is read it proves itself:
  `tests/mpx5-lsp.d/test_rows.py` passes both recorded transcripts and fails each of 23 mutations at its own row.
- **LSP3** the kernel's end: no -ENOSYS but 273 and 334, no `refused:` line, no panic, init ended 0, halted.
- **LSP4** the times, a NOTE on every run, never a bound.

### 4.2 The first boots, and the witness red first

- **The first boot** (`6014b64a`, before the rebase; native BIOS, KVM): every run byte-identical to Linux, LSP3 clean,
  at the first try. It also showed a hole in the suite: LSP2 **passed with its witness absent**, because python's
  error went to standard error and an empty capture read as a pass (`notes/px99/dev1-vacuous-lsp2-6014b64a.txt`). A
  row that has never been red had passed for nothing. The fix (`bc02415e`) makes a witness that cannot run, or exits
  other than 0, a failure, and runs the witness's own proof first.
- **Red first** (`1421edf0`, before the rebase; `07eb969f` after; every leg under KVM): the fix and the self-test
  committed, the witness not yet. LSP2 red by name in the self-test and in all 16 runs; LSP0, LSP1 and LSP3 green on
  all four legs (`notes/px99/dev2-red-lsp2-1421edf0.txt`).
- **Green:** with `rows.py` (`c05e1106`) the self-test passes whole and every LSP2 row holds (§4.3).

### 4.3 At the head

(The development runs at the head: every leg under KVM, and native BIOS under TCG, as CI boots. Filled in from the
runs; the records are §4.8.)

### 4.4 The calls `wolf lsp` makes (`notes/px99/strace-census.txt`)

On Linux, under `strace -f`, the client's own pid left out (`notes/px99/linux-open-fix.strace`, `linux-hung.strace`):

- **open-fix:** 14 pids, the process and 13 threads; 654 calls of 32 kinds. `clone` 13 times, always CLONE_VM, FS,
  FILES, SIGHAND, THREAD, SYSVSEM, SETTLS, PARENT_SETTID and CHILD_CLEARTID; `futex` 67 times (FUTEX_WAIT_BITSET_PRIVATE,
  FUTEX_WAIT_PRIVATE, FUTEX_WAKE_PRIVATE and one FUTEX_WAIT), one ETIMEDOUT, the debounce; `sched_yield` 264 times;
  `mmap` (with MAP_STACK and MAP_FIXED), `mprotect`, `munmap`, `sigaltstack`, `prctl(PR_SET_NAME)` three times;
  `poll` of descriptors 0 to 2 once at the start; `read(0)` and `write(1)`; the workspace through `open` (its
  `wolf.pkg` ENOENT, the directory), `getdents64`, `stat`, `fstat`, `lseek`; `getrandom`; `sched_getaffinity` and the
  cgroup files (`/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`, `/sys/fs/cgroup/cgroup.controllers`), from which the
  server sizes a pool of workers (8 of the 13 threads, on the reference's 8 CPUs); `exit` for 5 threads, `exit_group`.
  No `clock_gettime` on Linux, whose vDSO answers it in user space.
- **hung:** 5 pids, 4 threads; `clock_nanosleep` 542 times, the hook's 5 ms slices for the 3 s before the kill.
- **On PAX** every one of these is served: LSP3 shows no -ENOSYS from `wolf` (musl makes neither 273 nor 334; the two
  in the log are `as`'s, a glibc program) and no `refused:` line on any leg. PAX's `sched_getaffinity` answers one CPU,
  so the server makes fewer workers there; no frame depends on it.

### 4.5 Time

`time:` lines, the client's CLOCK_MONOTONIC from the last frame written to the frame waited for:

| | Linux (container) | PAX, KVM |
|---|---|---|
| first diagnostics | 588–666 µs | 0, 10,000 or 20,000 µs |
| cleared, from the edit | 100 ms debounce plus well under a millisecond | 110,001 µs |
| the server's end, from `close` or the kill | 215–531 µs | 0 or 10,000 µs |

PAX's CLOCK_MONOTONIC is `ticks × 10 ms` (`kernel/user`'s `now_ns`), so every time a program measures on PAX is a
whole number of 10 ms ticks, and `clock_getres` (229) is not served. The server's 100 ms debounce wakes on time on
that clock. Evidence only (R-px99-2).

### 4.6 What yew's client needs from PAX

From yew's map for its LSP client (the client, its child and pipes, a wait over the terminal and the pipes, a server
that dies or hangs), each item against this suite:

| need | shown by | |
|---|---|---|
| the server as a child on three pipes, and an exec-status pipe | every run's `spawn:` and `exec: ok`; the frames both ways | working |
| non-blocking reads of the server's output and error | every run (EAGAIN ends each drain) | working |
| one `poll` over the terminal and the pipes together | every wait of every run (`tty: 0 bytes`: the terminal in the set, never readable) | working |
| SIGCHLD on the server's end, through a self-pipe | `sigchld: 1` after a clean exit and after a kill; none for a thread's end | working |
| a deadline, then a group kill of a hung server | the hung runs: `setpgid`, `kill(-pgid, SIGKILL)` 0, `exit: signal 9`, every thread ended | working |
| a write to a server that has gone answers EPIPE, not a death by SIGPIPE | the hung runs, SIGPIPE ignored: `-32` | working |
| the same as an ordinary user | the `pax` runs, through `as` | working |
| a timer finer than 10 ms | PAX's monotonic clock is the tick's | a limit to know (R-px99-2) |

Not shown here, and not known to be missing: non-blocking writes with POLLOUT to a server whose input pipe is full
(no frame here reaches the pipe's 64 KiB), a server that crashes by its own fault, and incremental `didChange` (the
server negotiates full sync). yew's own client rows meet them first.

### 4.7 Rulings (recommended and implemented)

- **R-px99-1, the row's home.** Options:
  - (A) its own suite and CI job, `tests/mpx5-lsp`;
  - (B) a third image in `tests/mpx5-wolf`, which already builds the dev compiler.

  Recommended and implemented: **A**. Its rows, its plant and its planner rows stay its own, and a change to the
  client or the sessions runs it alone. The cost is one more `tools/mkwolf` build on a CI runner whenever both suites
  run (mpx5-wolf's whole job, its cargo build included, took 27.5 minutes in a recent `tier all`). B saves that build
  at the price of a larger mpx5-wolf whose reds would mix two concerns.
- **R-px99-2, PAX's monotonic clock.** It advances only with the 100 Hz tick, and `clock_getres` is not served. Nothing
  here needs finer, and `wolf lsp`'s 100 ms debounce works. Options: (a) say so (README, this note) and leave it; (b)
  an issue for a later lane: a monotonic clock read between ticks (the TSC calibrated against the timer PAX already
  calibrates), and `clock_getres`. Recommended: **(b)**, filed by the coordinator if agreed; (a) is done here.
- **R-px99-3, no kernel change.** The contract's item 3 asks for a fix where `wolf lsp` meets a gap; it met none. So
  this lane's PAX change is the suite, its client and their wiring, and the plant is the witness's own (P8).

### 4.8 The gauntlet and the plant

(Taken at the coordinator's word, once trunk has settled: the record at the head, every END line, and the plant's.)

### 4.9 The CI wiring, red first

`tests/ci-plan` derives a suite's paths from its script. With the job added (`2143827c`; `47f4ffdb` before the
rebase) and nothing else, three rows went red by name, each because it lists its suites exactly and the derivation
now adds mpx5-lsp: `P2 as reaches every suite whose user run uses it`, `P2 tools/mkas reaches the user runs` and `P2
compiler pin and dev root reach both shared-stager readers`. The rows were right to go red. With mpx5-lsp in `@user`
and `@asuser` and on the dev compiler's map lines (`616fb9a3`), the three rows naming it and four new ones
(`3ca99979`: the client and its builder, the suite's own files, the dev compiler's bytes and builders, and the
futex, readiness and process modules), all 328 checks pass. That makes the change `cross-cutting`: CI's own files and
CI's own proof.

## 5. Done-when

- [x] The prediction, committed first.
- [x] A session on PAX under QEMU: `initialize`, `initialized`, `didOpen` of a file with a known type error, its
  diagnostics, a `didChange` that fixes it and the diagnostics clearing, `shutdown` and `exit` (§4.1).
- [x] The same client against the same `wolf` on Linux, the reference, and the frames held byte for byte; the one
  normalisation, the `time:` lines, named in LSP1 (§4.1, §4.2).
- [x] The server's exit status and the time to first diagnostics recorded on both (§4.5).
- [x] Any PAX gap fixed red first: none met (R-px99-3); nothing of wolf's or std's to file.
- [x] The session as a PAX suite, `tests/mpx5-lsp`, its CI job, `tools/ci-tiers.map`'s groups and `tests/ci-plan`'s
  rows, red first (§4.9).
- [x] What yew's client needs from PAX beyond this, each item shown or named (§4.6).
- [ ] The gauntlet green at the head, every END line in the PR; the plant red by name in its own record; the audit.
