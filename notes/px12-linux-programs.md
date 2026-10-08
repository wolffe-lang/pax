# px12 — Linux programs (M-PX3: boreutils, unmodified, on PAX)

Contract: `sprints/pax/12-linux-programs/px12-linux-programs.md` in
wolffe-lang/wolf (planning trunk `f2f6e5d`, the contract's only commit,
2026-10-07). Branch `px12` in pax, cut from pax trunk `9cf59c0` (px10).
§1–§3 are committed before the first change to the kernel and before
the first strace of a boreutils binary; §4 and §5 fill in as the
evidence lands.

## 1. Forbidden, absolutely

- No Linux kernel, glibc, musl or any other kernel's or libc's source is
  read (ruling #22). Allowed and used: the uapi headers and
  `arch/x86/entry/syscalls/syscall_64.tbl` in the refs clone's sparse
  checkout (never widened), the ELF gABI and x86-64 psABI, the Intel
  and AMD manuals, man-pages sections 2, 4 and 7, and black-box runs of
  Linux (strace of the binaries under test). Disassembling a libc
  binary only to identify a faulting instruction, disclosed in §4.
- No `region` held open across a yield, a switch or a return to user
  mode (wolf-lang#611): this lane allocates nothing from wolf's heap;
  every process structure is frames or `.bss` words.
- Test binaries are built in an Ubuntu 24.04 container (the CI
  runner's distribution, its baseline x86-64 glibc 2.39) on kasumi and
  on the CI runner, **never with kasumi's CachyOS glibc**.
- No `rm` outside `~/lanes/px12/` and this lane's worktrees; no `git
  add -A`; nothing under `~/.claude`; no merge; no attribution
  trailers; no "seen red" without a run id, sha, path or digest.
- The tour (`kernel/pax_tour`, `kmain_tour*`, `tools/tour`,
  `tests/tour`) keeps passing; if its ISOs change,
  `~/scratch/wolf/pax-demo/` is refreshed and its preflight run to GO.
  No word implying filming anywhere in pax.

## 2. Inputs, verified (2026-10-07/08, from origin)

| input | found |
|---|---|
| pax trunk | `9cf59c0` (px10 merged, PR #13), as the contract says |
| px10's census (`notes/px10-the-loader.md` §4) | a glibc-static wolf program needs `brk` or anonymous `mmap`, `arch_prctl(ARCH_SET_FS)` with FS per thread, `mprotect`; the boreutils suite then `read`, `openat`, `close`, `fstat`, `getcwd`, `getdents64`, `getrandom`, `clock_nanosleep`. As the contract says |
| px04's census for the static boreutils suite (`tools/census/out/boreutils-static.csv`, `paths.csv`) | **26** distinct calls over 27 utilities, including **`statx`** (1,868 calls; on `/dev/stdout` and `/proc/self/fd`), `munmap`, `lseek`, `unlink`, `sched_getaffinity`; and the paths a static boreutils binary opens: **`/dev/stdout` (2,604 opens), `/dev/stdin`, `/dev/stderr`**, `/dev/null`, `/proc/self/exe` (readlinkat, every start) |
| boreutils trunk | **`2f15585`**, at wolf **0.2.23** / lupin 0.1.46 / wolf-std `6a0df5e` (`wolf-toolchain.toml`). **Drift:** the 0.2.25 pin is bu17's PR boreutils#22 (head `88a0bed`, green, OPEN, unmerged). This lane builds trunk with trunk's own pinned toolchain (wolf 0.2.23 by digest `6f505eb5…`) and says so; pax's kernel stays on its own pin (0.2.25) |
| boreutils' utilities | 29 entries in `src/`: basename, cat, cut, dirname, echo, expand, false, fold, head, nl, nproc, paste, printenv, printf, pwd, seq, sleep, sort, tac, tail, tee, tr, true, unexpand, uniq, wc, yes. **Drift: there is no `ls`** (none on bu17's branch either). The contract's fifth utility, "`ls` of an initramfs directory", cannot be a boreutils binary; see §3 for what this lane runs instead |
| boreutils' standard streams | its CLAUDE.md: no wolf builtin writes descriptor 1 or reads 0 as bytes, so every utility **reopens `/dev/stdout`** (and `/dev/stdin`) (wolf-lang#405). PAX therefore needs those paths, not only fds 0/1/2 |
| a fully static wolf binary | `wolf build --help` (0.2.25) has **no `--static`** flag; wolf links through the `cc` it finds first on `PATH` (px04's `tools/census/inside/stage.sh`, px10's `tools/mkwolf-hello`): a `cc` wrapper adding `-static` makes an ET_EXEC static glibc binary. Re-proved on Linux in §4 before any PAX boot |
| kasumi | QEMU 11.1.1, strace, podman; `/home` 95% (56 GB free); `docker.io/library/ubuntu:24.04` pulled by digest `sha256:f610ab94…`, built into `px12-ubuntu` (gcc 13.2, libc6 2.39-0ubuntu8.9, strace 6.8, busybox-static 1.36.1) |
| QEMU's machine | `tools/qemu-run`: q35, `-cpu max`, `-m 256M`: about 64,900 free frames after boot (px10's transcript: 64,984) |

## 3. Prediction (committed before the first change and the first strace)

### P1. The system calls the utilities make on Linux (strace, black-box)

The milestone set, each run in a directory that mirrors the initramfs,
with the arguments the test gives PAX: `echo hello from boreutils`, `cat
etc/motd`, `head -n 3 etc/words`, `wc etc/words`, and as stand-ins
beside them `tail -n 2 etc/words` and `pwd`.

- Every one makes glibc's static start-up first: `execve`, `brk` ×2,
  `arch_prctl(ARCH_SET_FS)`, `set_tid_address`, `set_robust_list`,
  `rseq`, `prlimit64`, `readlinkat("/proc/self/exe")`, `getrandom`,
  `mprotect` (RELRO): **11**.
- Then wolf's runtime and `bore`: `openat("/dev/stdout")`, `statx` or
  `fstat` on it, `write`, `close`, `exit_group`; a reader adds
  `openat(file)`, `read` to EOF, and `mmap`/`munmap` for a buffer of
  128 KiB or more; `tail` adds `lseek`; `pwd` adds `getcwd`.
- **The union over the six: 20 ± 3 distinct calls** (falsified outside
  17..23), every one inside px04's 26. `echo` the smallest (~15), `tail`
  or `cat` the largest (~19). No `getdents64`, no `clock_*`, no `ioctl`
  in any of them (falsified by one).

### P2. What fails first on PAX

- Today (px10's kernel): `brk(NULL)` → `-ENOSYS`, then `mmap` →
  `-ENOSYS`, glibc's `Fatal glibc error: Cannot allocate TLS block`,
  exit 127, as px10 measured with wolf-hello.
- With memory and TLS in and no files yet, start-up completes (the
  tolerated calls answer `-ENOSYS`: `set_tid_address`, `set_robust_list`,
  `rseq`, `prlimit64`, `readlinkat`) and **the first thing that fails is
  `openat("/dev/stdout")`**: PAX has no `/dev`. The utility then exits
  non-zero with nothing on stdout (a runtime or `bore` diagnostic on
  stderr, which is the console too).
- Once `/dev/stdout` opens, the next failure is `statx` (or `fstat`) on
  it, if the runtime refuses a stream it cannot stat; then the readers'
  `openat` of a relative path (`etc/motd`) needs the cwd `/`.
- The first boot that runs `echo` end to end prints the line
  byte-identical to Linux; the first boot of the whole set fails on at
  least one reader for a reason not in this list (a guess, named so it
  can be wrong).

### P3. The per-process memory model

- **brk**: the break starts at the page above the highest `PT_LOAD`
  end (Linux's static non-PIE placement; ASLR's random offset not
  modelled); `brk(addr)` grows it page by page with zeroed frames
  (read-write, no-execute, user) or shrinks it, freeing the frames;
  growth refused (the old break returned, as Linux does) past a 64 MiB
  cap or on reaching an existing mapping.
- **mmap**: anonymous private only, placed top-down from 0x7f0000000000
  (the ELF loader keeps everything above for the stack), never reusing
  an address in a process's life (the user half is 128 TiB); frames
  allocated and zeroed eagerly at the call (no demand paging);
  `MAP_FIXED` replaces what is there; `munmap` frees pages and frames
  (any page-aligned range, holes allowed); `mprotect` rewrites the leaf
  flags of pages present (`PROT_EXEC` drops NX, `PROT_WRITE` adds RW,
  `PROT_NONE` clears present-to-user: the frame kept, the page not
  user-accessible). Refused by name: a file-backed mapping (`-ENODEV`,
  mmap(2)'s "the underlying file system does not support memory
  mapping"), `MAP_SHARED` (`-EINVAL`), anything past the user half
  (`-ENOMEM`).
- **Freed at exit**: everything in the user half goes back with the
  space (px09's `paging.free_user`), so every batch's frames line reads
  `A / B / A`.
- **TLS**: `arch_prctl(ARCH_SET_FS)` writes IA32_FS_BASE (MSR
  0xC0000100) and the thread record keeps it; every switch loads the
  incoming thread's (WRMSR, not WRFSBASE: CR4.FSGSBASE stays clear, so
  user code cannot change FS behind the kernel). `ARCH_GET_FS` reads
  the record.
- Per utility, peak frames well under 1,000 (a static wolf binary is
  about 3 MiB of segments, ~760 frames, plus heap and stack): every
  utility fits PAX's 256 MiB many times over.

### P4. The fifth utility

boreutils has no `ls` (§2). This lane runs **two** stand-ins and says
which proves what: boreutils `tail` and `pwd` (a reader that seeks, and
`getcwd`), and, for "`ls` of an initramfs directory", **busybox-static's
`ls`** from Ubuntu 24.04 (`busybox-static` 1.36.1-6ubuntu3.1), an
unmodified static Linux x86-64 binary that is not boreutils: its
listing of a directory the initramfs holds compared byte for byte with
the same binary's listing of the same tree on Linux. Prediction for it:
`getdents64`, `statx` or `newfstatat`/`lstat` per entry, `ioctl` on
stdout (`TCGETS`/`TIOCGWINSZ` → `-ENOTTY`, so one name per line), and
about 15 distinct calls. Whether that counts as M-PX3's fifth is the
orchestrator's call; the report says exactly what ran.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: the six boreutils utilities' union is 20 ± 3 distinct calls (17..23) | **right: 21** (`notes/px12/linux-strace-*.txt`, Ubuntu 24.04 container on kasumi, and CI's own trace in run 37717393136's log): execve, brk, arch_prctl, set_tid_address, set_robust_list, rseq, prlimit64, readlinkat, getrandom, mprotect, openat, write, exit_group, close, mmap, munmap, read, statx, lseek, pread64, getcwd |
| P1: every one inside px04's 26 | **wrong by one: `pread64`** (tail's `fs_read_at`, adopted by bu15 after px04's census tree `010f314`) |
| P1: echo the smallest (~15), tail or cat the largest (~19) | **half right**: echo is the smallest at **13**; the largest is **head, 19** (it seeks and maps a buffer); cat 18, wc 18, tail 17, pwd 14 |
| P1: no getdents64, clock_*, ioctl in any of the six | right (sleep, not one of the six, adds clock_nanosleep) |
| P1: mmap/munmap for a buffer of 128 KiB or more | right: `mmap(NULL, 266240, …)` (cat, head, wc), and B3's frames show it: plant C lost exactly 65 frames per such call |
| P2: today's kernel dies at `brk` with "Cannot allocate TLS block", exit 127 | right (px10's measurement, not re-run) |
| P2: with memory and TLS in, the first failure is `openat("/dev/stdout")` | **not measured**: the three pieces landed together before the first boot, so no boot had memory without files |
| P2: the first boot of the whole set fails on at least one reader for a reason not in this list | **wrong**: the first boot (eight commands: the five, tail, pwd, an ENOENT) ran byte-identical to Linux (`notes/px12/kasumi-tcg-first-boot-native-bios.serial.log` `c9ba0848…`). The first unforeseen failure came with the second list: a **relative** path (`cat etc/words`) answered "Input/output error", because glibc passes `AT_FDCWD` as `0x00000000ffffff9c` (the upper half zero) and PAX compared all 64 bits, so the descriptor was "closed", -EBADF, which wolf's runtime words as EIO (`kasumi-c1-relative-path-red.boot.log`); `int` arguments are now read as 32 bits |
| — (not predicted) | busybox calls `time` (201) on PAX and not on Linux: Linux answers it in the vDSO, PAX has none (no AT_SYSINFO_EHDR), so glibc makes the system call; implemented |
| P3: the memory model (brk above the image, anonymous mmap top-down from 0x7f0000000000, eager zeroed frames, everything back at exit) | held: B3 holds on every leg of every run (frames back per command); plant C reds it |
| P3: peak frames per utility well under 1,000 (~760 for a 3 MiB image) | **right on the bound, wrong on the reason**: 321–334 frames per boreutils process, 570 for busybox, 893 for the two at once; a boreutils binary is 11.8 MB on disk but loads only ~1.1 MB (four PT_LOAD), the rest is debug info |
| P3: FS by WRMSR of IA32_FS_BASE at every switch in, CR4.FSGSBASE clear | as built; plant A (no restore at the switch) kills the sleeper woken after busybox with a page fault at busybox's TLS address (`cr2 0x000000000060e3e8`) |
| P4: busybox `ls`: getdents64, statx or newfstatat per entry, ioctl -ENOTTY, ~15 distinct | **calls right, count wrong: 20** (it also asks `fstat`, `getuid`, `prctl(PR_GET_NAME)`); newfstatat per entry, `ioctl(0, TIOCGWINSZ)` and `ioctl(1, TCGETS)` -ENOTTY |

## 4. Evidence index

### The programs and the Linux side

- boreutils `2f15585` (its pin wolf 0.2.23 `6f505eb5…`, wolf-std `6a0df5e`), built by `tools/mkboreutils` (`2b3655d`) with `-static`; **byte-identical on CI and in the kasumi container**: echo `4ced726c…`, cat `f90b0bb0…`, head `d4e6c46d…`, wc `5afcc80c…`, tail `4f705483…`, pwd `3a636563…`, sleep `a26cb399…` (`notes/px12/boreutils-sums-2f15585.txt`; CI run 37717393136's log); busybox-static 1.36.1-6ubuntu3.1 `dbac288c…`. px10's census subject rebuilt in the container is `a3ada54b…`, px10's CI hash: the builds are reproducible across the runner and the container.
- The strace sets: `notes/px12/linux-strace-{echo,cat,head,wc,tail,pwd,ls}.txt` (container, `-f`), and per command in every CI run (`tools/linux-run --strace`, the `linux:` lines; `notes/px12/ci-green-641ebef.txt`).
- The Linux side of B2: `tools/linux-run`, chrooted in the initramfs's tree, stdin `/dev/null`, stdout and stderr one pipe, the same argv and environment; CI runner Ubuntu, glibc 2.39-0ubuntu8.9, kernel 6.17.0-1022-azure; kasumi container Ubuntu 24.04 on kasumi's 7.2.8.

### The Linux-vs-PAX diff

**Empty** for all 17 lines of `user/mpx3-boreutils.run` (the five: `echo hello from boreutils`, `cat /etc/motd`, `busybox ls /bin /etc`, `wc /etc/words`, `head -n 3 /etc/words`; then tail, pwd, wc of two files, a relative path, head, cat of standard input, sleep, sleep and busybox at once, `ls -a`, and ENOENT, EISDIR, ENOTDIR as each utility words them), statuses `0 ×13, 0 0, 1, 1, 1` identical, on every leg: CI run **37717393136** (head `641ebef`, job 113116914556, B2 on four legs) and **37718863327** (`769d1d6`), and the final head's run (PR body); kasumi TCG at `641ebef` (`notes/px12/kasumi-mpx3-boreutils-641ebef.txt`: 20 PASS, 0 FAIL); hasu KVM (below). The transcript: `notes/px12/kasumi-tcg-native-bios-kmain_boreutils.serial.log` (`5f49cb3a…`).

### Planted breaks (each its own push and CI run, reverted by the next commit; `notes/px12/ci-planted-breaks.txt`)

- **A** `787d2ad` (the FS base not restored at a switch): run **37717282743**, job 113116563341, only mpx3-boreutils red: B2 on all four legs, line 13 only: `user: sleep pid 14 killed: page fault … cr2 0x000000000060e3e8 after 2 runs`. Reverted `03e7f8b` (run 37717318677 green).
- **B** `a170471` (getdents64 skips a directory's first child): run **37717328877**, job 113116713402: B2 red on lines 3, 13, 14 (busybox's listings lose `busybox` and `motd`), four legs. Reverted `1245ad1` (run 37717354882 green).
- **C** `b0521e8` (munmap and brk's shrink keep the frames): run **37717367799**, job 113116834202: B2 green, **B3 red** (65 frames lost per command that maps its 266240-byte buffer: lines 2, 4, 5, 8, 9, 10, 11), four legs. Reverted `641ebef` (run 37717393136 green on all 14 jobs).
- Two harness reds found on the way (not plants): `--images` on a fresh tree had no `build/` (hasu, `notes/px12/hasu-fresh-tree-no-build-dir-red.txt`; fixed `769d1d6`), and B5 required ticks in ring 3 > 0, which a KVM boot can miss (hasu round 8 of `769d1d6`, release uefi `ticks in ring 3 '0'`, `notes/px12/hasu-round8-B5-ticks-red.txt`; fixed `b039e76`: reported, not asserted).

### Boot counts

- **hasu, KVM** (i7-12700KF, QEMU 11.1.0 via nix-shell, OVMF from nixpkgs, strict `PAX_REQUIRE_UEFI=1`), kasumi-built images: at `769d1d6` **148 boots, all accel=kvm** (`notes/px12/hasu-kvm-769d1d6.log`): mpx3-boreutils 8 rounds × 4 = 32 (31 rounds' worth of assertions green; one release-uefi boot counted 0 ring-3 ticks, the harness defect above), mpx3-loader 2 × 4 = 8 (with wolf-hello, 32 PASS each), mpx3-user 12, mkw 12, mpx1 12, mpx2-frames 16, mpx2-paging 4, mpx2-interrupts 20, mpx2-sched 8, mpx2-heap 24; then at `b039e76` mpx3-boreutils 8 × 4 = **32 more, all 20 PASS each round, all accel=kvm** (`notes/px12/hasu-kvm-b039e76.log`; two of the 32 boots counted 0 ring-3 ticks, which is why B5 no longer asserts them): **180 KVM boots** in all.
- **kasumi, TCG** (QEMU 11.1.1): the gauntlet on `git archive` of `79df225` (`notes/px12/kasumi-gauntlet-79df225.summary`): proof 2, census 3, mkw 16, mpx1 26, mpx2-frames 44, mpx2-paging 26, mpx2-interrupts 34, mpx2-sched 32, mpx2-heap 56, mpx3-user 38, tour 44, mpx3-loader 34 (with wolf-hello: L8 now `exit_group 0` after printing, -ENOSYS only 273 and 334; `kasumi-mpx3-loader-79df225-L2-L8.txt`), 0 FAIL, 0 SKIP; no kernel code but kmain_boreutils's changed after it. mpx3-boreutils 4 boots at `79df225` and 4 at `641ebef`, all PASS; tour at `641ebef` 44 PASS.
- **CI**: 4 boots of kmain_boreutils per run; every job green at `79df225` (37716659137), `641ebef` (37717393136), `769d1d6` (37718863327).

### The tour

The tour's kernels link the scheduler, so its ISOs changed: rebuilt by `tests/tour` on kasumi at `641ebef` (44 PASS; `notes/px12/kasumi-tour-641ebef.txt`): `pax-tour.iso` `a7c3a6df…`, `pax-tour-b.iso` `3bae5d83…` (px10's `2ade3864…`, `8e804bd4…`). The image grew 156 → 252 KiB (every kernel now carries `pax_procs`, `pax_kbuf`, `pax_execbuf`), frame counts −41 (65030 usable, 64981 free, 64963 at the join), ending b's `rip` `0xffffffff80018273`. `~/scratch/wolf/pax-demo/` refreshed: the ISOs, SHA256SUMS, `src/` (pax's `kernel/`, `boot/`, `user/` at `769d1d6`, identical to the tree; nothing removed), the SHOTLIST's numbers and the README's build lines; `preflight.sh` **GO** (QEMU 11.1.1, `a7c3a6dffe79 3bae5d830c59`, 11659 lines of wolf, the PANIC line in about 29 s; `logs/preflight.serial.log` `09ed1bd3…`).

### Drift from the contract, reported

1. boreutils has no `ls` (§2): the directory listing is busybox-static's (P4, §5).
2. boreutils trunk is at 0.2.23, not 0.2.25 (bu17, boreutils#22, still open at the end): the binaries are trunk's, built with trunk's toolchain; `user/boreutils.pin` moves in its own commit when bu17 lands.
3. A file-backed `mmap` answers **-ENODEV** (mmap(2)'s answer for a file that cannot be mapped), not the contract's -ENOMEM/-EINVAL; `MAP_SHARED` is -EINVAL as the contract says. Both are `refused:` lines by name.
4. "`ioctl(TCGETS)` → -ENOTTY": PAX answers -ENOTTY to every ioctl on an open descriptor (TIOCGWINSZ too, which busybox asks), as Linux does for a descriptor that is not a terminal; the console becomes a terminal in px13.
5. "Every unknown syscall logged once by number": once per process and number (a bitmap in the process area), so px10's census lines (`tests/mpx3-loader` L8) now list each missing call once.
6. Not in the contract: `time` (201) and `gettimeofday` (96), because PAX has no vDSO (P4's row); `prctl(PR_GET_NAME)`, `getuid` and the other ids, `prlimit64`, `set_tid_address`/`gettid`, `uname`, `nanosleep`, `stat`/`lstat`/`open` (the old numbers), and the `int`-argument rule (§3).

### Filed

Nothing upstream. wolf's runtime words EBADF and ENOTDIR as "Input/output error" (seen on PAX and on Linux alike: `head -n 2 /etc/motd/x` says it on both), which is wolf-lang#407 (no strerror text behind a row), already filed. wolf has no `--static`; a `cc` wrapper is the documented way (px04, px10), so no issue.

## 5. Done-when

- Branch `px12` on origin; PR wolffe-lang/pax#15, open, unmerged; CI green at the head (run id in the PR body).
- **M-PX3: met, with one substitution the orchestrator should rule on.** boreutils' `echo`, `cat` of an initramfs file, `wc` and `head` (and `tail`, `pwd`, `sleep`), unmodified static Linux binaries built from boreutils' own tree, run on PAX with output and exit status byte-identical to the same binaries on Linux, both tiers, BIOS and UEFI, KVM on hasu. **The fifth, `ls` of an initramfs directory, is busybox-static's `ls`, not boreutils'**: boreutils has no `ls` (§2). If M-PX3 requires boreutils' own `ls`, what is missing is boreutils' `ls` itself; PAX's side (`getdents64`, `newfstatat`, `fstat`, `ioctl` -ENOTTY) is proven by busybox.
- Close nothing. To close: none (no pax issue names this work).
- Worktrees: the local worktree `pax-px12` removed at the end; kasumi `~/lanes/px12/` and hasu `~/lanes/px12/` keep the trees and evidence with `build/` directories pruned; the container image `px12-ubuntu` on kasumi is the lane's (podman, not installed on the host).
