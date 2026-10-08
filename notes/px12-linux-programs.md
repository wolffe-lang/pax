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
