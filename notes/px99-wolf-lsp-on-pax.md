# px99 — `wolf lsp` on PAX: the language server runs on the image

PAX's dev image ships `/usr/bin/wolf` 0.2.36, the musl-static compiler `tools/mkwolf` builds from wolf-lang's
`v0.2.36` tag, and that compiler carries the `lsp` subcommand: the Language Server Protocol over standard input and
output, on rust-analyzer's `lsp-server` transport (its own reader, writer and dropper threads), crossbeam channels and
a thread per diagnostics publication. Nothing had run it on PAX. This lane drives a whole session against it on PAX
under QEMU, and the same session against the same binary on Linux, and holds the frames to each other.

## 1. Forbidden, and what was read

- **Clean room.** No kernel, firmware or driver source of any system. The program under test was read as a program:
  wolf-lang's `crates/wolf_lsp` and the driver's `lsp` entry at `v0.2.36`, the `lsp-server` 0.10.0 crate's stdio
  transport and framing, and wolf-lsp's `lspconf` scripts and recorded transcripts (recorded at the same pin). The
  editor client yew will port, sagitta's `src/mod/lsp/client.c` and `src/edit/job.c`, was read for how an editor starts
  and watches a server (three pipes and an exec-status pipe, `fork`, `setpgid`, a self-pipe for SIGCHLD, a group kill).
- **References:** the LSP 3.17 specification (base protocol framing, lifecycle, `textDocument/publishDiagnostics`),
  `pipe(2)`, `fork(2)`, `execve(2)`, `poll(2)`, `wait4(2)`, `setpgid(2)`, `kill(2)`, `sigaction(2)`, `futex(2)` and
  the uapi headers' numbers and layouts.

## 2. Inputs, verified

(Filled in as the rows run.)

## 3. Prediction, scored

Written before the first change (2026-11-05), from the program's source and PAX's census.

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

(Filled in as the rows run.)

## 5. Done-when

- [ ] The prediction, committed first.
- [ ] A session on PAX under QEMU: `initialize`, `initialized`, `didOpen` of a file with a known type error, its
  diagnostics, a `didChange` that fixes it and the diagnostics clearing, `shutdown` and `exit`.
- [ ] The same client against the same `wolf` on Linux, the reference, and the frames held byte for byte, the
  normalisation named.
- [ ] The server's exit status and the time to first diagnostics recorded on both.
- [ ] Any PAX gap fixed red first, with its own row; any wolf or std gap filed upstream with the witness.
- [ ] The session as a PAX suite, wired into `tests/ci-plan` at its tier.
- [ ] What yew's client needs from PAX beyond this, each item shown or named as a gap.
- [ ] The gauntlet green at the head, every END line in the PR; the plant red by name in its own record; the audit.
