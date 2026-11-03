# px88 — fork for musl, and getrusage (pax#175, #185, #248)

Contract: `wolf/sprints/pax/88-the-fork/px88-the-fork.md` (crawl 54, batch C, launched 2026-11-02 on the maintainer's
word "Launch them"), under `sprints/the-lane-rules-1031.md` (every "Added 2026-11-01" item) and RULES §1–§10. Base
pax trunk `3e28a8bc`, rebased once onto `5da8daaf`; branch `px88`. Footprint: cross-cutting (`kernel/sched`, the kernel's core; a comment in
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

- **Base** `3e28a8bc79d7ff879f74c1872fe1bc9ccfa97a1f`, pax trunk at launch (rebased once, below). Branch `px88`; the Mac clone
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
  every chain now returns its worst step's (`9c8979cc`). Two commits went to hasu as a git bundle, not a push, while
  the head was not yet green.
- **The rebase.** Rebased once, at the orchestrator's word, from `3e28a8bc` onto trunk `5da8daaf` (pm00's ten
  commits, notes only), the old head `f7472de8` and the rebased head `835fb70c` differ by exactly trunk's four
  `notes/pm00*` files with the lane's own diff byte-identical, so the gauntlet's evidence, and every run here named
  by the sha it ran at before the rebase (`notes/px88/rebase-map.txt` pairs each commit with its twin), stands for
  the code at the new head.

Commits, by their rebased shas (the prediction first; the failing rows before each fix):

- `955b203c` notes/px88/prediction.txt, before any change
- `79049170`, `69d3bb81`, `216945d2`, `7ea9cbce`, `9c8979cc` notes/px88/hasu: the launcher, the container step, the
  image, the suite at a commit, the installer's row at a commit, the chains, the wrapper's worst-step exit
- `b22051a4` notes/px88/linux/explore.c: black-box Linux's numbers, before the witness
- `315aa9aa` user/elf/forks.c; `a182013b` user/elf/usage.c; `9961da28` tools/mkforks
- `64821aa2` tests/mpx5-forks (red: fork and getrusage -ENOSYS)
- `04ee8e44` tests/mpx6-install: I-peak (red: `unavailable (-38)`)
- `373ee5e4` kernel/process: fork (57) is clone(SIGCHLD, 0); `9d278ba0` kernel/user: its dispatch
- `bb7bb4c1` kernel/sched: the accounting; `0d07b4ae` boot/sched.S: the record's size (a comment)
- `5e0b6362` kernel/vm: the peak before every lowering call
- `239e1d5d` kernel/process: getrusage, and wait4's and waitid's rusage
- `8d75e8cf` kernel/user: every system call bracketed; getrusage dispatched
- `1d0c24e8` ci: the mpx5-forks job; `6989829a` tools/ci-tiers.map; `56cff3c1` tests/ci-plan
- `46d5f5a9` kernel/sched: a parent ignoring SIGCHLD keeps no zombie (R-px88-9)
- `1b075adc` docs/SOURCES.md; `14699d9e` kernel/README.md
- `f7d00736` user/elf/usage.c: bounds as Linux reads RSS, a vfork child's exec row; `473c28ed` kernel/sched: a vfork
  child's exec counts its parent's peak
- `642a32c2` user/elf/usage.c: no hang on a kernel that cannot fork; `7de73447` the 64 MiB peak itself
- `e15c5178` docs/CENSUS.md; `8a1fe9b8` docs/BOOT.md; `3f69b4b0` notes/px88: the chains' logs and transcripts
- `961baede` README (a README-only commit); `91f1f7b7` this note, before the plant and the gauntlet
- `bd38c7bf` notes/px88/hasu: the gauntlet (FROM, UNTIL, a step-log directory per run) and the plant's match
- `bcc3580c`, `b28a2702` notes/px88: the gauntlets' logs, the plant's session, the match's proof; after them, this
  note's plant and gauntlet sections
- after the rebase: `notes/px88/rebase-map.txt`, and this note's rebase, hang-check and issue lines

## Prediction, scored

`notes/px88/prediction.txt` (`955b203c`, 2026-11-02T17:55Z, pushed before the first change):

| predicted | measured |
|---|---|
| P1 base: forks red, fork -ENOSYS, the kernel logs 57 once; vfork and posix_spawn rows green at base | **right**: `fork: -38`, K3 `-ENOSYS for 'forks 57'`; every vfork and spawn row byte-identical to Linux's at base (`sessions/r2-red/`) |
| P2 base: usage red, every getrusage -ENOSYS, wait4's rusage zeros | **right**, and **not predicted**: at base the usage probe hung (its parent read a pipe whose write end it still held, waiting for a child fork never made): NOT HALTED within 600 s (r2-B2). Fixed in the probe (`642a32c2`); on the fork-less kernel the fixed probe runs to its end (r4's hang check) |
| P3 the fork fix turns every forks row green, root and user, both tiers and firmwares | **right**: 49 lines byte-identical to Linux's, as root and as 1000:1000, native BIOS and release UEFI (r3-B, r4) |
| P4 every usage row byte-identical but the `~` rows (minflt 0 on PAX); majflt, inblock, oublock 0 on both; the seven unmaintained 0 on both | **right** at r4: 43 lines byte-identical, both users, both legs; K2 `~minflt: self 0`, Linux's 240 (root) and 267 (the user) |
| P5 maxrss: the 64 MiB touch adds 64-65 MiB on both | **wrong for Linux**: Linux reads RSS approximately (64 MiB touched read as +64,700 KiB; a 32 MiB child 32,640; a 48 MiB grandchild 49,120: `notes/px88/linux/r1-explore.log`), so the rows take 4 MiB of slack (`f7d00736`); and a process's peak outlives exec, so on Linux's side the probe starts with tools/linux-tree's Python's peak and its growth from there is under 60 MiB: the rows hold the peak itself (`7de73447`). PAX reads the count exactly |
| P5 the free leaves it unchanged; the children's and wait4's at least the child's; a grandchild's through the middle child | **right** on both kernels |
| P5 across exec Linux keeps the old image's peak | **right** (`before exec: maxrss 40960`, `after exec: maxrss 40960`); **not predicted**: a vfork child's exec carries its parent's peak (`small: maxrss 65440`), which PAX now does too (`473c28ed`, the `vfork:` rows) |
| P6 times: the spin's utime 150-320 ms, stime under 50; the reads' stime at least 100, more than utime | **right** on both (Linux: +299 ms utime; +299 ms stime for the reads) |
| P7 switches: ten sleeps at least 10 voluntary; a shared spin at least 2 involuntary | **right**; **not predicted**: Linux counts a `sched_yield` that switches as involuntary (+20 nivcsw for 20 yields), as PAX does |
| P8 the installer prints `<N> KiB`, above Linux's 11884 KiB, 12-256 MiB | **right on the line, wrong on the size**: `Installer peak RSS through copy verification: 5904 KiB`, `Formatter children peak RSS: 28264 KiB`, below Linux's reference |
| P9 nothing else moves | **right** for the suites run here: mpx2-sched and mpx3-user, all four legs, and every self-test and the census green (the gauntlet, below); CI's `tier pr` runs every suite (kernel/sched is the core) |
| P10 the plant reddens the forks rows by name | **right**, and more than the one row: K1 red at line 2 (`fork: child status 0`), the child never reaching its own rows, and the session hanging (K3-K5; the plant, below) |

Not predicted at all: a parent whose SIGCHLD is ignored keeps no zombie on Linux and does not count the child
(`ignored SIGCHLD: waitpid -1 errno 10`, the children's utime and maxrss unchanged), where PAX kept a zombie; the
usage probe's `ignored:` rows found it and `46d5f5a9` serves it (R-px88-9).

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
- **R-px88-8, times(2) and /proc.** (A) left as they are, owed as pax#270 and pax#271; (B) served here from the same counts. **A**:
  outside the contract's items.
- **R-px88-9, SIGCHLD ignored** (found by the witness). (A) a parent whose SIGCHLD is SIG_IGN, or whose action has
  SA_NOCLDWAIT, keeps no zombie: a wait answers -ECHILD once no child is left and the child is not counted (wait(2),
  getrusage(2), measured); (B) a `~` row and an issue. **A**: small, in the file px88 already changes, and
  RUSAGE_CHILDREN's own rule.

### The change

- **fork** (`373ee5e4`, `9d278ba0`): kernel/user dispatches 57 with clone, clone3 and vfork; kernel/process's `clone`
  sends it to `fork(f, 0, 0, 0, 0)`: the copy of the space, the child's %rax 0, the parent's the child's pid.
- **The accounting** (`bb7bb4c1`, `8d75e8cf`, `5e0b6362`, `473c28ed`): each thread's record gains five words (`cpu`,
  `sys`, `sysin`, `vcs`, `ics`; 464 of the slot's 512 bytes) and each process area ten (words 6084-6093, past
  kernel/vm's last): the process's sums and its reaped children's. `run_next`'s `account` charges the outgoing
  thread's run, closes and reopens a system call's bracket across a switch, and counts the switch (involuntary from a
  thread still ready, voluntary from one that waits). kernel/user's `syscall` brackets each call (`serve` inside).
  The peak is `note_rss`, called by kernel/vm before each lowering, by `exec_current` (the old space; for a vfork
  child, its parent's peak) and by `reap`. A wait's `zombie` folds the child's sums into the waiter's children's
  (times and switches added, the largest set kept). A fork's child starts at zero; exec keeps the process's sums.
- **getrusage** (`239e1d5d`): `who` read as an int (0, -1, 1; else -EINVAL), then 144 writable bytes (else -EFAULT);
  ru_utime and ru_stime, ru_maxrss in KiB, ru_nvcsw, ru_nivcsw; everything else 0.

### The rows (hasu; `notes/px88/hasu-logs/`, `notes/px88/sessions/`)

Each run is named by the commit it ran at, before the rebase (`notes/px88/rebase-map.txt` gives each one's twin).

| run | commit | what it showed |
|---|---|---|
| r1 (block B) | — | the image built; black-box Linux's numbers and musl's system calls (`notes/px88/linux/r1-explore.log`) |
| r2-B2 (block B) | `3df2ae18`, the suite before any fix | **red**: forks K1 and K3 (`-ENOSYS for 'forks 57'`), root and user; usage K1, K2, K3 (`usage 57`, `usage 98`) and NOT HALTED (the probe's hang) |
| r3-B (block B) | `7505f0cc` | forks green on both legs; usage two rows red where Linux's side, not PAX's, said `no` (the inherited peak); I-peak red at `26872978` by name (`AssertionError: FAIL I-peak: … ['unavailable (-38); not zero memory']`) and green at the head |
| r4 (block A) | `efff7957` | **green**: all four sessions on native BIOS and release UEFI (forks 49 lines, usage 43, byte-identical to Linux's, root and 1000:1000); the fixed usage probe runs to its end on the fork-less kernel (a lane-only commit, never pushed: `3df2ae18`'s tree with `efff7957`'s `user/elf/usage.c`); `PASS I-peak: installer 5904 KiB, formatter children 28264 KiB` |

The probes (`probes.txt`): `forks` `e99479d9…` (73,472 bytes), `usage` `4d7f8226…` (68,640), both ET_EXEC, no
PT_INTERP, no `.dynamic`, no glibc; `as` `fb82459…` (glibc-static, the user sessions' `setuid` front).

What PAX answers differently from Linux, by name: ru_minflt (R-px88-4); a page fault's handling counts as user
time on PAX (only system calls are bracketed), where Linux counts it as system time (PAX's eager memory takes few);
a vfork child's exec counts the parent's whole peak, where Linux counts the borrowed space's peak since its last
exec (the same unless the parent's earlier image was larger).

### The plant

`px88-plant-fork` (draft PR #274, base `px88`, never to merge) was `fe780b7f` for the gauntlet: `ce2a07ac` with one
line of `kernel/sched`'s `clone_current` changed, the child's %rax the parent's tgid where fork(2) gives it 0 (its
CI run `41560213359`). After the rebase it was re-cut onto px88's final head with the same one line; the PR's test
targets name its sha.

```
-        ((cf + W_RAX * 8) as *u64).write_volatile(0)
+        ((cf + W_RAX * 8) as *u64).write_volatile(if cr3 != 0 { field(p, offset_of(Thread, tgid)) } else { 0 }) // PLANT …
```

Red by name, native BIOS, the forks session (`notes/px88/sessions/plant-fe780b7f/`, gauntlet3's run): PAX's whole
transcript is two lines, `forks: as root` and `fork: child status 0`, where Linux's lines 2 and 3 are `fork: child`
and `fork: child status 7`. Given a nonzero answer the child takes the parent's branch at the first fork: it never
prints `fork: child`, its waitpid of the pid it was given answers ECHILD (status 0), and both processes then wait as
parents on a pipe nobody writes, so the session never halts. The rows:

```
mpx5-forks: FAIL K1 native bios forks: the output differs from Linux's: 2,49c2|< fork: child|< fork: child status 7|…
mpx5-forks: FAIL K3 native bios forks: 0 killed (0 by SIGTERM), not the one SIGTERM row: ;
mpx5-forks: FAIL K4 native bios forks: frames not all back (''); no tree line ('');
mpx5-forks: FAIL K5 native bios forks: no 'PAX: init … ended with status 0' (); not halted (qemu-halt: NOT HALTED: no line matching /halt|PANIC .*/ within 600s);
```

K3, K4 and K5 follow from K1: a fork's child knows it is the child only by its 0, so the contract's break cannot
spare what the child does next, and the plant was not re-cut. The first form of `plantred.sh` (gauntlet2) looked for
the `what fork answered the child:` row, which the hang means is never reached, and failed the step on a red plant.
The step now holds the red at its first sign (K1 red, the session's line 2 exactly `fork: child status 0`, no
`fork: child` line), and its `--match` mode is its own proof (`notes/px88/hasu-logs/plantred-match-proof.log`):
green (exit 0) on the plant's real session and log, gauntlet2's and gauntlet3's; red (exit 1) on five wrong inputs
(the green session, the green session with the plant's log, a child that printed its line, fork's -ENOSYS, the
plant's session with a green K1).

### The gauntlet at the final head

`notes/px88/hasu/gauntlet.sh` on hasu block A, at `ce2a07ac`, behind both of the block's locks, each step's log its
own (`notes/px88/hasu-logs/gauntlet*-ce2a07ac/`). Everything after `ce2a07ac` on the branch is `notes/` alone (the
scripts, the logs, this note), and the rebase (above) moved only trunk's notes, so the head's kernel, probes, tests
and CI are the gauntlet's.

**gauntlet** (the first): stopped at its first step on its own bug, a step name with `/` used as a file name; no test
ran.

```
2026-11-03T01:32:00Z END tests/ci-plan exit=1
2026-11-03T01:32:00Z px88 gauntlet: released block A; END gauntlet exit=1
```

**gauntlet2**: every step 0 up to the plant, which failed on the check's bug (above).

```
2026-11-03T01:33:25Z END tests/ci-plan exit=0
2026-11-03T01:33:26Z END python3 -I tests/ci-retry.py exit=0
2026-11-03T01:33:26Z END python3 -I tests/mpx2-heap.d/budget.py exit=0
2026-11-03T01:33:27Z END python3 -I tests/ci-budgets.py exit=0
2026-11-03T01:33:27Z END tests/fetch-retry-selftest exit=0
2026-11-03T01:33:28Z END python3 -I tests/usb-session-selftest exit=0
2026-11-03T01:33:28Z END python3 -I tests/pipe-shape-selftest exit=0
2026-11-03T01:33:28Z END tests/expect-serial-selftest exit=0
2026-11-03T01:33:29Z END tests/census exit=0
END g-forks-ce2a07ac-boot-uefi-release-forks+usage+forks-user+usage-user exit=0
2026-11-03T01:40:59Z END tests/mpx5-forks all four legs exit=0
END g-hang-4420a145-boot-bios-native-usage exit=1
2026-11-03T01:41:13Z END g-hang-4420a145-ends exit=0 (the suite's own exit 1: its rows are red at this kernel by design)
2026-11-03T01:41:13Z END mpx5-forks usage ends on a kernel without fork exit=0
END g-plant-fe780b7f-boot-bios-native-forks exit=1
2026-11-03T01:51:23Z END g-plant-fe780b7f-red exit=1 (the suite's own exit 1)
2026-11-03T01:51:23Z END the plant red by name exit=1
2026-11-03T01:51:23Z px88 gauntlet2: released block A; END gauntlet2 exit=1
```

mpx5-forks' four legs (native and release, BIOS and UEFI; the four sessions each): 72 PASS rows, every forks session
49 lines and every usage session 43 byte-identical to Linux's, root and 1000:1000. The hang check (the lane-only
commit above, never pushed: `3df2ae18`'s fork-less tree with `efff7957`'s `user/elf/usage.c`) is red on K1-K3 as it
must be and runs to its end (`PASS K5 … init ended, status 0`, halted). Those two steps' boot logs are kept from
their own build directories (`gauntlet2-ce2a07ac/`); gauntlet2's step logs for the nine fast steps were erased when
gauntlet3 cleared the directory they shared, which is why gauntlet4 ran them again.

**gauntlet3**: from the plant on, every step 0. The steps before the plant print SKIP (they ran 0 in gauntlet2, at
the same head):

```
SKIP tests/ci-plan (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP python3 -I tests/ci-retry.py (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP python3 -I tests/mpx2-heap.d/budget.py (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP python3 -I tests/ci-budgets.py (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP tests/fetch-retry-selftest (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP python3 -I tests/usb-session-selftest (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP python3 -I tests/pipe-shape-selftest (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP tests/expect-serial-selftest (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP tests/census (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP tests/mpx5-forks all four legs (before 'the plant red by name': 0 in the earlier gauntlet)
SKIP mpx5-forks usage ends on a kernel without fork (before 'the plant red by name': 0 in the earlier gauntlet)
2026-11-03T02:08:16Z END g-plant-fe780b7f-red exit=0 (the suite's own exit 1)
2026-11-03T02:08:16Z END the plant red by name exit=0
END g-peak-ce2a07ac-install exit=0
2026-11-03T02:08:49Z END mpx6-install I-peak exit=0
2026-11-03T02:18:23Z END g-mpx2-sched exit=0
2026-11-03T02:18:23Z END tests/mpx2-sched all four legs exit=0
2026-11-03T02:37:51Z END g-mpx3-user exit=0
2026-11-03T02:37:51Z END tests/mpx3-user all four legs exit=0
2026-11-03T02:37:51Z px88 gauntlet3: released block A; END gauntlet3 exit=0
```

I-peak read `PASS I-peak: installer 5872 KiB, formatter children 28264 KiB (getrusage, pax#248)`; r4 read 5904 at
`efff7957`, the same kernel, probes and tests (nothing under `kernel/`, `boot/`, `user/`, `tools/`, `tests/` or
`.github/` differs between the two): eight pages apart run to run, both below Linux's 11884. mpx2-sched: 33 PASS lines, no FAIL, seven rows on each of the four legs. mpx3-user: 39 PASS lines, no FAIL, eight
rows on each leg, the SMAP and SMEP panics by name.

**gauntlet4**: the nine fast steps once more, in a step-log directory of its own (`gauntlet4-ce2a07ac/`), ending at
`tests/census` (`UNTIL`). Each step's log was read, not only its exit: ci-plan's 317 PASS lines, among them px88's
(the musl probes reach mpx5-forks and mpx5-users, their builder mpx5-forks alone, kernel/process every user suite,
P4's mpx5-forks job); census's C1-C6 and R0-R3 PASS, `docs/CENSUS.md matches` (the served section regenerates
byte-identically); expect-serial's 26 `ok` rows; the budgets, retry, USB, pipe-shape and fetch-retry rows all PASS,
no FAIL in any.

```
2026-11-03T02:43:48Z END tests/ci-plan exit=0
2026-11-03T02:43:49Z END python3 -I tests/ci-retry.py exit=0
2026-11-03T02:43:50Z END python3 -I tests/mpx2-heap.d/budget.py exit=0
2026-11-03T02:43:50Z END python3 -I tests/ci-budgets.py exit=0
2026-11-03T02:43:51Z END tests/fetch-retry-selftest exit=0
2026-11-03T02:43:51Z END python3 -I tests/usb-session-selftest exit=0
2026-11-03T02:43:52Z END python3 -I tests/pipe-shape-selftest exit=0
2026-11-03T02:43:53Z END tests/expect-serial-selftest exit=0
2026-11-03T02:43:53Z END tests/census exit=0
2026-11-03T02:43:53Z px88 gauntlet4: released block A; END gauntlet4 exit=0
```

(Each step also prints its container's own `END g-<name> exit=N`; the logs hold both.)

## Done-when

- [x] Item 1: fork served as `clone(SIGCHLD, 0)`; the static musl fork/exec/wait witness suite red first and then
  byte-identical to Linux's, as root and as a user, on native BIOS and release UEFI.
- [x] Item 2: getrusage for RUSAGE_SELF, RUSAGE_CHILDREN and RUSAGE_THREAD; ru_maxrss in KiB from PAX's own count,
  the times from the scheduler, the rest 0 where Linux's are (the seven unmaintained; majflt, inblock and oublock,
  measured) and ru_minflt named; each field measured against Linux by the same witness.
- [x] Item 3: the installer's two peak lines print KiB (I-peak, red first); docs/CENSUS.md's served section and its
  installer paragraph moved; docs/BOOT.md likewise.
- [x] Item 4: the clean room, as above.
- [x] Item 5: this note; the plant `px88-plant-fork` (#274) red by name; the gauntlet at the head (above); the PR
  and the audit are the hand-back's.
- [x] README read against the pass: the Programs row and the suites table moved (`961baede`, a README-only
  commit); nothing else in it moved.

**Issues** (none filed or closed by this lane): pax#175, #185 and #248 are fixed by this PR and are to be closed by
hand at the merge. Owed, filed by the orchestrator:
- pax#270: `times(2)` (100) is -ENOSYS; the same counts would serve it (R-px88-8).
- pax#271: `/proc/<pid>/stat`'s utime, stime, cutime and cstime are 0 and `/proc/<pid>/status`'s VmHWM and VmPeak are the
  current count; both could read px88's counts.
