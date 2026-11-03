# px88 — fork for musl, and getrusage (pax#175, #185, #248)

Contract: `wolf/sprints/pax/88-the-fork/px88-the-fork.md` (crawl 54, batch C, launched 2026-11-02 on the maintainer's
word "Launch them"), under `sprints/the-lane-rules-1031.md` (every "Added 2026-11-01" item) and RULES §1–§10. Base
pax trunk `3e28a8bc`, branch `px88`. Footprint: cross-cutting (`kernel/sched`, the kernel's core; a comment in
`boot/sched.S`; CI's new `mpx5-forks` job, `tools/ci-tiers.map`, `tests/ci-plan`).

A static musl program's `fork()` asks system call 57 where x86-64 has it; glibc's and wolf's ask `clone` (56). PAX
answered 57 -ENOSYS, so every static musl program that forked failed on PAX (pax#175, found by ligature's ld01).
`getrusage` (98) was -ENOSYS too, so nothing could report a peak or a time (pax#185, #248: the installer printed
`unavailable (-38)`). px88 serves `fork` as `clone(SIGCHLD, 0)`, serves `getrusage` for RUSAGE_SELF, RUSAGE_CHILDREN
and RUSAGE_THREAD from accounting the scheduler now keeps, fills wait4's and waitid's rusage, and holds every row to
Linux with two static musl probes in a new suite, `tests/mpx5-forks`.

## Forbidden

No kernel's, libc's or firmware's source was read: not Linux's, not a BSD's, not musl's, not glibc's. musl appears
only as Ubuntu 24.04's packaged binaries (`musl`, `musl-dev`, `musl-tools` 1.2.4-2: `musl-gcc`), used as a tool to
build the two witnesses. Written from the man pages (fork(2), vfork(2), clone(2), execve(2), wait(2), wait4(2),
getrusage(2), sigaction(2), signal(7), posix_spawn(3), pthread_create(3), fcntl(2), pipe(2), lseek(2), nanosleep(2),
sched_getaffinity(2)), POSIX.1-2024, the syscall table, one uapi header (`include/uapi/asm-generic/signal-defs.h`
for SA_NOCLDWAIT, read in the planning repo's sparse refs clone), the Intel SDM (RDTSC, the time-stamp counter), and
black-box Linux (hasu's 7.2.4 from a rootless container: the exploration probe and `strace -f` of musl's fork, vfork
and posix_spawn). Each is in `docs/SOURCES.md` (px88's section). PAX's own tree and notes were read (px14's, px17's,
px26's, px62's, px71's, px78's, px85's, px86's).

kasumi was never touched (the brief's word, though the lane rules now say it is back); hasu's `:9308` and `:9364`
servers and the maintainer's data were not touched; nothing was installed on a host (the lane's image,
`localhost/px88-ubuntu:1`, is px75's with Ubuntu's `musl-tools` and `strace` added by apt inside the image). No label,
no merge, no dispatch, no issue filed or closed; no attribution trailers. Two scratch files went to the Mac's `/tmp`
by mistake (a list of script digests and a 128 KiB tarball of transcripts) and were removed at once.

## Inputs, verified

- **Base** `3e28a8bc79d7ff879f74c1872fe1bc9ccfa97a1f`, pax trunk at launch. Branch `px88`; the Mac clone
  `~/lanes/px88/pax` (git, `gh`, three compile checks); the hasu clone `/home/mfwolffe/lanes/px88/pax`, a worktree
  per tested commit (`wt-<sha>`), its git steps behind a lane-local lock.
- **Toolchain** wolf 0.2.35 by `kernel/wolf.pin` (archive `4cc4045b…`, copied from px85's cache, never moved; its
  sha256 read and `tools/fetch-wolf`'s own check every build), Limine 12.9.1 (the same cache). On the Mac, for
  compile checks only: the same release's `aarch64-apple-darwin` archive, `240b84d0…`, read twice (shasum and the
  release API's digest): both tiers 0 errors, 277 warnings, none on a line px88 wrote.
- **Image** `localhost/px88-ubuntu:1` (`0d6472c5…`): `localhost/px75-ubuntu:2` (QEMU 8.2.2, OVMF, clang, lld 18, gcc
  13.3.0) plus musl 1.2.4-2, musl-tools, strace 6.8 (`notes/px88/hasu/Containerfile`). CI's job gets the same
  `musl-tools` from the runner's apt.
- **Hosts** hasu, both block names held per chain (`notes/px88/hasu/launch.sh`: one `flock -w 21600` each, detached,
  a pid file, a log, an exit marker), `taskset` to the block's CPUs inside every container, `--memory 12g`,
  `/dev/kvm` for the boots; tools/linux-tree's containers through `notes/px88/hasu/podman-blk` (the same pinning and
  memory cap). The Mac: compile checks behind the Mac build lock (the 8 GiB gate, 60 s between turns).
- **The queue.** r2 and r3 waited six hours on block A behind another lane's conversion and ended exit 1 on the lock
  timeout, no test run (`notes/px88/hasu-logs/r2.log`, `r3.log`); requeued on block B at the orchestrator's word.
  r2-B then failed in 20 s: scp had left every hasu copy of the scripts at mode 644, and `podman-blk` is executed
  directly (`Permission denied`, exit 126); the modes restored to git's and every copy's sha256 compared with its
  commit, it ran again as r2-B2. r3-B read `exit=0` over a red suite because `r3.sh` returned its last step's status;
  every chain now returns its worst step's (`efff7957`). Two commits went to hasu as a git bundle, not a push, while
  the head was not yet green.

Commits (the prediction first; the failing rows before each fix):

- `4fa9e7de` notes/px88/prediction.txt, before any change
- `bc63b6f5`, `a09b74b1`, `25d25c85`, `7505f0cc`, `efff7957` notes/px88/hasu: the launcher, the container step, the
  image, the suite at a commit, the installer's row at a commit, the chains, the wrapper's worst-step exit
- `4cc7cc01` notes/px88/linux/explore.c: black-box Linux's numbers, before the witness
- `026692f6` user/elf/forks.c; `9298b362` user/elf/usage.c; `78173bf0` tools/mkforks
- `3df2ae18` tests/mpx5-forks (red: fork and getrusage -ENOSYS)
- `26872978` tests/mpx6-install: I-peak (red: `unavailable (-38)`)
- `8952728f` kernel/process: fork (57) is clone(SIGCHLD, 0); `48b8881f` kernel/user: its dispatch
- `624d73aa` kernel/sched: the accounting; `54c603eb` boot/sched.S: the record's size (a comment)
- `67f6e7ce` kernel/vm: the peak before every lowering call
- `bdbe71d2` kernel/process: getrusage, and wait4's and waitid's rusage
- `da375bf8` kernel/user: every system call bracketed; getrusage dispatched
- `8d48071e` ci: the mpx5-forks job; `18390307` tools/ci-tiers.map; `d57a9cba` tests/ci-plan
- `a6b2828f` kernel/sched: a parent ignoring SIGCHLD keeps no zombie (R-px88-9)
- `33a991d3` docs/SOURCES.md; `d262e497` kernel/README.md
- `d616e393` user/elf/usage.c: bounds as Linux reads RSS, a vfork child's exec row; `08d5ef50` kernel/sched: a vfork
  child's exec counts its parent's peak
- `a4fb4ec9` user/elf/usage.c: no hang on a kernel that cannot fork; `1ce14056` the 64 MiB peak itself
- `34568fd5` docs/CENSUS.md; `93687f55` docs/BOOT.md; `d628abf0` notes/px88: the chains' logs and transcripts
- `5caece74` README (a README-only commit); this note

## Prediction, scored

`notes/px88/prediction.txt` (`4fa9e7de`, 2026-11-02T17:55Z, pushed before the first change):

| predicted | measured |
|---|---|
| P1 base: forks red, fork -ENOSYS, the kernel logs 57 once; vfork and posix_spawn rows green at base | **right**: `fork: -38`, K3 `-ENOSYS for 'forks 57'`; every vfork and spawn row byte-identical to Linux's at base (`sessions/r2-red/`) |
| P2 base: usage red, every getrusage -ENOSYS, wait4's rusage zeros | **right**, and **not predicted**: at base the usage probe hung (its parent read a pipe whose write end it still held, waiting for a child fork never made): NOT HALTED within 600 s (r2-B2). Fixed in the probe (`a4fb4ec9`); on the fork-less kernel the fixed probe runs to its end (r4's hang check) |
| P3 the fork fix turns every forks row green, root and user, both tiers and firmwares | **right**: 49 lines byte-identical to Linux's, as root and as 1000:1000, native BIOS and release UEFI (r3-B, r4) |
| P4 every usage row byte-identical but the `~` rows (minflt 0 on PAX); majflt, inblock, oublock 0 on both; the seven unmaintained 0 on both | **right** at r4: 43 lines byte-identical, both users, both legs; K2 `~minflt: self 0`, Linux's 240 (root) and 267 (the user) |
| P5 maxrss: the 64 MiB touch adds 64-65 MiB on both | **wrong for Linux**: Linux reads RSS approximately (64 MiB touched read as +64,700 KiB; a 32 MiB child 32,640; a 48 MiB grandchild 49,120: `notes/px88/linux/r1-explore.log`), so the rows take 4 MiB of slack (`d616e393`); and a process's peak outlives exec, so on Linux's side the probe starts with tools/linux-tree's Python's peak and its growth from there is under 60 MiB: the rows hold the peak itself (`1ce14056`). PAX reads the count exactly |
| P5 the free leaves it unchanged; the children's and wait4's at least the child's; a grandchild's through the middle child | **right** on both kernels |
| P5 across exec Linux keeps the old image's peak | **right** (`before exec: maxrss 40960`, `after exec: maxrss 40960`); **not predicted**: a vfork child's exec carries its parent's peak (`small: maxrss 65440`), which PAX now does too (`08d5ef50`, the `vfork:` rows) |
| P6 times: the spin's utime 150-320 ms, stime under 50; the reads' stime at least 100, more than utime | **right** on both (Linux: +299 ms utime; +299 ms stime for the reads) |
| P7 switches: ten sleeps at least 10 voluntary; a shared spin at least 2 involuntary | **right**; **not predicted**: Linux counts a `sched_yield` that switches as involuntary (+20 nivcsw for 20 yields), as PAX does |
| P8 the installer prints `<N> KiB`, above Linux's 11884 KiB, 12-256 MiB | **right on the line, wrong on the size**: `Installer peak RSS through copy verification: 5904 KiB`, `Formatter children peak RSS: 28264 KiB`, below Linux's reference |
| P9 nothing else moves | the suites run here (the gauntlet, below) green; CI's `tier pr` runs every suite (kernel/sched is the core) |
| P10 the plant reddens the forks rows by name | see the plant, below |

Not predicted at all: a parent whose SIGCHLD is ignored keeps no zombie on Linux and does not count the child
(`ignored SIGCHLD: waitpid -1 errno 10`, the children's utime and maxrss unchanged), where PAX kept a zombie; the
usage probe's `ignored:` rows found it and `a6b2828f` serves it (R-px88-9).

## Evidence index

### Rulings (recommended and implemented, not decided)

- **R-px88-1, fork.** (A) 57 through kernel/process's existing fork path as `clone(SIGCHLD, 0)`; (B) a fork of its
  own. **A**: the path glibc's clone already proves.
- **R-px88-2, the CPU times.** (A) the TSC's cycles, counted by kernel/sched at every switch (a thread's run) and by
  kernel/user around every system call (its system part), converted to nanoseconds against kernel/clock (the rate
  fixed one second of ticks after the scheduler starts); (B) tick sampling (a tick charged to the thread it lands on,
  user or system by its frame); (C) kernel/clock read at every switch and call. **A**: PAX runs system calls with
  interrupts off, so a tick never lands in one and B would read stime as about 0; C costs a VM exit per read under
  KVM (the HPET is emulated in QEMU's own process).
- **R-px88-3, the peak.** (A) the space's mapped pages counted (kernel/paging's `user_pages`) before every call that
  can lower them (munmap, brk down, MADV_DONTNEED and MADV_FREE, mremap smaller, MAP_FIXED over pages, a truncate's
  cut, exec, the end) and when read; (B) an incremental count at every map and unmap; (C) at exec, the end and the
  read only. **A**: exact at page granularity (between two lowerings the count only grows), one walk per lowering
  call; B touches every map site in the kernel; C misses a freed peak (the probe's freed-64 MiB row).
- **R-px88-4, what PAX does not count.** (A) ru_minflt, ru_majflt, ru_inblock, ru_oublock 0, ru_minflt a `~` row
  held to its text; (B) PAX's own faults as ru_minflt. **A**: PAX maps anonymous memory at the call and takes none of
  the first-touch faults Linux counts, so B's number would mean something else; majflt and the block counts are 0 on
  Linux too for programs and files in memory (measured).
- **R-px88-5, wait4's and waitid's rusage.** (A) the reaped child's (its own and its reaped children's, the larger
  peak), as Linux; (B) zeros, as before. **A** (measured: `wait4 of middle: maxrss 49120`).
- **R-px88-6, RUSAGE_THREAD.** (A) served (the thread's own times and switches, the process's peak, as Linux
  answers); (B) -EINVAL. **A**.
- **R-px88-7, the witness's home.** (A) a new suite, `tests/mpx5-forks`, with its own CI job; (B) sessions of
  mpx3-maps. **A**: its own probes, builder and Linux side, and a plan entry of its own.
- **R-px88-8, times(2) and /proc.** (A) left as they are, an issue owed; (B) served here from the same counts. **A**:
  outside the contract's items.
- **R-px88-9, SIGCHLD ignored** (found by the witness). (A) a parent whose SIGCHLD is SIG_IGN, or whose action has
  SA_NOCLDWAIT, keeps no zombie: a wait answers -ECHILD once no child is left and the child is not counted (wait(2),
  getrusage(2), measured); (B) a `~` row and an issue. **A**: small, in the file px88 already changes, and
  RUSAGE_CHILDREN's own rule.

### The change

- **fork** (`8952728f`, `48b8881f`): kernel/user dispatches 57 with clone, clone3 and vfork; kernel/process's `clone`
  sends it to `fork(f, 0, 0, 0, 0)`: the copy of the space, the child's %rax 0, the parent's the child's pid.
- **The accounting** (`624d73aa`, `da375bf8`, `67f6e7ce`, `08d5ef50`): each thread's record gains five words (`cpu`,
  `sys`, `sysin`, `vcs`, `ics`; 464 of the slot's 512 bytes) and each process area ten (words 6084-6093, past
  kernel/vm's last): the process's sums and its reaped children's. `run_next`'s `account` charges the outgoing
  thread's run, closes and reopens a system call's bracket across a switch, and counts the switch (involuntary from a
  thread still ready, voluntary from one that waits). kernel/user's `syscall` brackets each call (`serve` inside).
  The peak is `note_rss`, called by kernel/vm before each lowering, by `exec_current` (the old space; for a vfork
  child, its parent's peak) and by `reap`. A wait's `zombie` folds the child's sums into the waiter's children's
  (times and switches added, the largest set kept). A fork's child starts at zero; exec keeps the process's sums.
- **getrusage** (`bdbe71d2`): `who` read as an int (0, -1, 1; else -EINVAL), then 144 writable bytes (else -EFAULT);
  ru_utime and ru_stime, ru_maxrss in KiB, ru_nvcsw, ru_nivcsw; everything else 0.

### The rows (hasu; `notes/px88/hasu-logs/`, `notes/px88/sessions/`)

| run | commit | what it showed |
|---|---|---|
| r1 (block B) | — | the image built; black-box Linux's numbers and musl's system calls (`notes/px88/linux/r1-explore.log`) |
| r2-B2 (block B) | `3df2ae18`, the suite before any fix | **red**: forks K1 and K3 (`-ENOSYS for 'forks 57'`), root and user; usage K1, K2, K3 (`usage 57`, `usage 98`) and NOT HALTED (the probe's hang) |
| r3-B (block B) | `7505f0cc` | forks green on both legs; usage two rows red where Linux's side, not PAX's, said `no` (the inherited peak); I-peak red at `26872978` by name (`AssertionError: FAIL I-peak: … ['unavailable (-38); not zero memory']`) and green at the head |
| r4 (block A) | `efff7957` | **green**: all four sessions on native BIOS and release UEFI (forks 49 lines, usage 43, byte-identical to Linux's, root and 1000:1000); the fixed usage probe runs to its end on the fork-less kernel (`4420a145`, a lane-only commit: `3df2ae18`'s kernel with the head's probe); `PASS I-peak: installer 5904 KiB, formatter children 28264 KiB` |

The probes (`probes.txt`): `forks` `e99479d9…` (73,472 bytes), `usage` `4d7f8226…` (68,640), both ET_EXEC, no
PT_INTERP, no `.dynamic`, no glibc; `as` `fb82459…` (glibc-static, the user sessions' `setuid` front).

What PAX answers differently from Linux, by name: ru_minflt (R-px88-4); a page fault's handling counts as user
time on PAX (only system calls are bracketed), where Linux counts it as system time (PAX's eager memory takes few);
a vfork child's exec counts the parent's whole peak, where Linux counts the borrowed space's peak since its last
exec (the same unless the parent's earlier image was larger).

### The plant

(Filled in after the gauntlet, below.)

### The gauntlet at the final head

(Filled in after the gauntlet, below.)

## Done-when

- [x] Item 1: fork served as `clone(SIGCHLD, 0)`; the static musl fork/exec/wait witness suite red first and then
  byte-identical to Linux's, as root and as a user, on native BIOS and release UEFI.
- [x] Item 2: getrusage for RUSAGE_SELF, RUSAGE_CHILDREN and RUSAGE_THREAD; ru_maxrss in KiB from PAX's own count,
  the times from the scheduler, the rest 0 where Linux's are (the seven unmaintained; majflt, inblock and oublock,
  measured) and ru_minflt named; each field measured against Linux by the same witness.
- [x] Item 3: the installer's two peak lines print KiB (I-peak, red first); docs/CENSUS.md's served section and its
  installer paragraph moved; docs/BOOT.md likewise.
- [x] Item 4: the clean room, as above.
- [ ] Item 5: the note, the plant, the PR, the audit (below).
- [x] README read against the pass: the Programs row and the suites table moved (`5caece74`, a README-only
  commit); nothing else in it moved.

**Issues** (none filed or closed by this lane): pax#175, #185 and #248 are fixed by this PR and are to be closed by
hand at the merge. Owed, for the orchestrator to file or drop:
- `times(2)` (100) is -ENOSYS; the same counts would serve it (R-px88-8).
- `/proc/<pid>/stat`'s utime, stime, cutime and cstime are 0 and `/proc/<pid>/status`'s VmHWM and VmPeak are the
  current count; both could read px88's counts.
