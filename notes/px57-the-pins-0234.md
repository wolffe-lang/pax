# px57 — The pins at 0.2.34, aspen on PAX, and a lupin that runs there

Contract: px57's, `sprints/pax/57-the-pins-0234/px57-the-pins-0234.md`
in wolffe-lang/wolf (planning trunk `e7d7ba5`, read 2026-10-21 from
`origin/trunk`), px53's shape (`notes/px53-the-pins-0233.md`) with every
one of its rules kept, under `sprints/RULES.md`. Branch `px57` in pax,
cut from pax trunk `ebbef86` (px54, px56). Ruling #110 (the
maintainer, decided at launch): lupin in the base image, wolf in a dev
image later; item 3 is lupin. §1 to §3 are committed before the first
change to a pin, the kernel, a tool, a probe or a test, and before the
first measurement.

Four deliverables: (1) the kernel and `user/*` at wolf 0.2.34, every
binary rebuilt and its digest recorded, the kernels' `.text` deltas, the
recordings held, and what 0.2.34 asks of PAX measured by a probe of its
own (`user/edwolf`), with pax#107's rows; (2) aspen (`/bin/aspen`,
aspen `103ba46`) on PAX, its typed session held to Linux and its
syscall census; (3) a static musl lupin (`/bin/lupin`) on PAX with three
programs, a typed session held to Linux and its census; (4) the
playground image with all three.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor any
  libc's (glibc's, musl's), shell's, terminal driver's, container
  runtime's or init system's, nor tree's (aspen's rule 1, ruling #103),
  nor any interpreter's but lupin's own (wolffe-lang/wolf-interp, the
  maintainer's), nor `su`/`login`/util-linux/procps source (ruling #22;
  RULES.md §1). Facts come from the man pages (`fork(2)`, `fsync(2)`,
  `realpath(3)`, `open(2)`'s O_EXCL, `termios(3)`, `poll(2)`,
  `prctl(2)`, `getrlimit(2)`, `fcntl(2)`, `uname(2)`, `proc(5)`,
  `strace(1)` as documentation), POSIX.1-2024, the allowed uapi headers
  and syscall table, pax's own source and notes (px38 to px56), and the
  org's own repositories read as the maintainer's code and records:
  wolf-lang `v0.2.34` (`9da7bdcf`: its CHANGELOG, spec `11-os.md`'s
  `[os.proc.fork]`, `[os.term.mode]`, `[os.term.restore]`,
  `[os.signal.wait.fds]`, `[os.fs.sync]`, `[os.fs.realpath]`,
  `[os.fs.open]`, `[os.clock.ns]`; wolf-lang#847's branch `s253` for
  pax#107's calls, read as documentation of what they ask), wolf-interp
  `fcf2fd0`/`v0.1.55` (`Cargo.toml`, `build.rs`, `rust-toolchain.toml`,
  the release workflow, `src/main.rs`'s commands, its manual and its
  corpus), aspen `103ba46` (`docs/MAP.md`, `tools/mkaspen`,
  `tools/build`, `wolf-toolchain.toml`, `notes/ap00-the-first-light.md`),
  wolf-std `3bacc5f`. `wolf/refs/repos/linux` stays sparse and is not
  opened. Black-box: real root's guest (kasumi's own kernel image under
  QEMU with a static program as pid 1, px48's `vmjob` way,
  `notes/px52/vmjob.c` unchanged), a rootless throwaway container for a
  user's rows and for the aspen and lupin sessions (`tools/linux-tree`),
  `strace -f` of the programs' own runs in `px13-ubuntu`.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals, faults, forks, id changes and core dumps only
  to processes a test started, inside QEMU or a container, never on a
  host's process table; `ulimit -c 0` (`--ulimit core=0:0`) wherever a
  core would reach a host.
- Probe and test binaries static, built in `px13-ubuntu` on kasumi,
  never with kasumi's CachyOS glibc (AVX-512). No build on nomad-1.
  **The musl lupin is built in a throwaway image made FROM
  `localhost/px13-ubuntu`** with rustup, lupin's pinned Rust and the
  `x86_64-unknown-linux-musl` target installed inside it (the recipe in
  `notes/px57/`): `px13-ubuntu` has no `rustup`, `cargo` or `rustc`
  (measured at the start), and nothing is installed on any host. kasumi
  under `bash`, long jobs `setsid -f` with a pid file, ended by that pid
  only (never by name, pattern or process group); work under
  `~/lanes/px57/`, pruned (kasumi `/home` 31 GB free at the start);
  never `/tmp`. Process, signal and terminal tests under
  `taskset -c 0-3`; SigBlk and SigIgn read before a signal row is called
  red. Ports 8080 and 8088 unused. `~/lanes/orch-paxplay/` is touched
  only as item 4 says (its two scripts gain aspen and lupin, the pre-edit
  copies kept); every other lane's directory untouched.
- Toolchains from release archives by digest, each read twice: wolf
  0.2.34 (`v0.2.34` → `9da7bdcf`, release 419552903), lupin 0.1.55
  (`v0.1.55` → `e642f26`, release 418932753, the glibc archive for
  `tests/mkw`), wolf-std `3bacc5f` (for `su`, `sigwolf` and `edwolf`),
  and each program's own pin as its tree names it (pelt's 0.2.32,
  boreutils', lope's and aspen's 0.2.33).
- No `rm` outside `~/lanes/px57/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or
  the PR. No other lane's run cancelled; pax CI is tiered: a plant by
  dispatch, `-f tier=pr` with its suite (mpx5-jobs with its images,
  `-f jobs_boots=…`); the PR opened without the label, `full-matrix`
  added at the final head. "Seen red" cites a run. No assertion deleted
  or weakened, no timeout or retry as a fix. Nothing says "secure"; no
  word implying filming. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-21)

| input | found |
|---|---|
| pax trunk | `ebbef86` (px54's rebase note, after px56 `f83d627`); its push run 39667476855 in progress at the time of reading, `f83d627`'s 39655947183 green; open PRs none; open issues #55, #56, #62, #67, #90, #100–#104, #106–#109 |
| planning repo | `e7d7ba5` (crawl 54: s254 merged, ruling #110, px57 launched) |
| wolf 0.2.34 | `v0.2.34` (annotated tag `38ab81cb`) → `9da7bdcf2aea9adf48df6570bedc58e16e9ef853`; release 419552903, `wolf-0.2.34-x86_64-unknown-linux-gnu.tar.gz` **`88a9dd3da1c9a0e38c08eb6e2de9c1ef04d1ed93dcf51024d8dbbb76890c1821`, 80,433,878 bytes** (the API, read twice); STD-PIN `e036bec`. CHANGELOG: seven new prelude names (`os_fork`, `os_term_restore_at_exit`, `os_signal_wait_fds`, `fs_sync`, `fs_sync_dir`, `fs_realpath`, `os_clock_ns`) and the mark `busy`; a mode int without bits 5–7 writes the usual setting (`ICRNL`, `OPOST` on, `ISTRIP` off); a program that names `os_signal_wait_fds` makes the hub before `main`; the pairing lupin 0.1.55 |
| lupin 0.1.55 | `v0.1.55` → `e642f2630ad4c7f53740428d5cca705f2e0d295b`; release 418932753, `lupin-0.1.55-x86_64-unknown-linux-gnu.tar.gz` **`1152abc0bef65d334b94bc881a26463fac345919cc2ca07a291796e6048a8a38`, 2,966,156 bytes** (read twice); glibc-linked (the release builds on `ubuntu-22.04`, its glibc floor 2.35) |
| wolf-interp `fcf2fd0` | trunk; `git diff e642f26 fcf2fd0 -- src Cargo.toml Cargo.lock build.rs rust-toolchain.toml vendor` is **empty** (tl29's CI files and notes only). `Cargo.toml` 0.1.55, edition 2024, `rust-version` 1.97.1, `unsafe_code = "forbid"`, dependencies clap 4.5 (derive), rustyline 18.0.1 (no default features, `custom-bindings`), serde, serde_json — no C. `rust-toolchain.toml` channel 1.97.1. `build.rs`: D57's stamp, the bare version only when `v{version}` points at HEAD (`git tag --points-at HEAD`), else `+dev.<commit>`; `LUPIN_HOST_TRIPLE` from cargo's `TARGET`. The release workflow's targets: linux x86-64 and aarch64 (glibc, ubuntu-22.04), macOS aarch64, windows x86-64; no musl |
| wolf-std `3bacc5f` | on wolf-std trunk (sc69's merge; "wolf 0.2.35's STD-PIN is this branch's merge sha"); the contract's std for `su` and the user programs |
| s253 (pax#107) | wolf-lang#847 OPEN, branch `s253` (`b308daf`): `os_name`, `os_arch`, `os_core_limit`, `os_set_core_limit`, `os_core_off`, `fs_adopt` are **0.2.35's**, not in 0.2.34's prelude; its spec reads PAX from source: `uname` sysname `PAX` (so `pax`), machine `x86_64`; `prlimit64` soft 0 hard unlimited, every set -EPERM (`denied`); `prctl(PR_SET_DUMPABLE, 0)` served (`os_core_off` ok); `F_GETFD`/`F_SETFD` served (`fs_adopt`'s two `fcntl`s). PAX's source agrees: `kernel/user/user.lu` `uname` puts `PAX` and `x86_64`; `prlimit` answers -EPERM for any `new` |
| aspen | public; trunk `103ba4670594327acc905b9798f1ee9bde3f06c9`; `git diff 0db8d10 103ba46 -- src wolf-toolchain.toml tools/build tools/mkaspen` empty (ap00's gauntlet head). Its own toolchain: wolf **0.2.33** `4f955e8d…`, lupin 0.1.55, wolf-std **`e036bec`** (staged over the archive's bundled `cceda63`). Its `tools/mkaspen`: `tools/build --static` twice (`wolf build --release --no-cache --deny-warnings src/aspen.lu` through a `cc` that adds `-static`), refused unless the digests agree, ET_EXEC, no PT_INTERP. ap00's static in "an Ubuntu 24.04 container (glibc 2.39, clang 18.1.3)": **`b34106b5bf15252e1024d1bd67839044008b5e5f4f4ae483b75821a329cda384`, 14,497,536 bytes**, twice; CI's runner `9bd08d6d7114…`, 14,257,992. MAP: v1 lists through wolf-std's `fs_read_dir_entries`, `fs_lstat`, `fs_stat`, `fs_read_link` (getdents64, fstatat), path-based, a stat pool on `scope`/`spawn` above C aspen's thresholds; `--du` follows tree (D1: exit 2 on an open error) |
| PAX's ELF loader | `kernel/elf`: a static, non-PIE ET_EXEC only; refuses `ET_DYN` (`a PIE or shared object (PIE is later)`) and `PT_INTERP` by name |
| PAX's clock | `clock_gettime`'s monotonic clocks answer `timer.ticks() * NS_PER_TICK` (10,000,151 ns, the PIT at 99.998 Hz): **10 ms granular**; no vDSO, so every clock read is a call |
| PAX's syscall table | names (a `SYS_` constant each) 0–18, 20–22, 24, 28, 32–35, 39–45, 48–56, 58–63, 72, 74–77, 79–84, 86–96, 102, 104–124, 127, 130–133, 140–141, 144–145, 157–158, 161, 164–166, 169–171, 186, 200–202, 204, 217–218, 227–228, 230–235, 247, 257–269, 275, 280, 285, 288, 290–293, 302, 316, 318, 322, 326, 332, 435, 439, 452; not `mremap` (25), `readv` (19), `select` (23), `clock_getres` (229), `set_robust_list` (273), `rseq` (334) |
| the pins pax holds | `kernel/wolf.pin` 0.2.33 / lupin 0.1.54 (px53; read by `tools/fetch-wolf`, `tools/fetch-lupin`, every kernel build, `tests/mkw`, `tests/tour`; `kernel/pax_tour/pax_tour.lu` prints `wolf 0.2.33`); `user/su/wolf-toolchain.toml` and `user/sigwolf/wolf-toolchain.toml` 0.2.33 / `cceda63`; `user/pelt.pin` `90d7c64` and `user/boreutils.pin` `cc64f68` (the contract's, already); `user/lope.pin` `5ac37df` (not this lane's). No pax wolf source declares one of the seven new names (`git grep -w`: comments and strings only for `busy`) |
| the playground | kasumi `~/lanes/orch-paxplay/`: `build.sh`, `assemble.sh`, its pax tree, `lope/`, `out/` (px56's `c9ce2cda…`) |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, load 10.6 (other lanes), `/home` 31 GB free, `px13-ubuntu` `ad8964505189` (gcc, clang, ld.lld, strace, git; **no rustup, cargo or rustc**) |

## 3. Prediction (committed before the first change and measurement)

**P1. The pins**, each its own commit: `kernel/wolf.pin` to wolf 0.2.34
(`88a9dd3d…`) / lupin 0.1.55 (`1152abc0…`), with `pax_tour.lu`'s
`wolf 0.2.34` line; `user/su/wolf-toolchain.toml` and
`user/sigwolf/wolf-toolchain.toml` each to 0.2.34 / wolf-std `3bacc5f`.
**The kernel builds on 0.2.34 with no source change, and its `.text`
does not move**: 0.2.34 is s247's and s248's hosted runtime, the
prelude's seven names and the std, none of which the freestanding kernel
links or calls; all four kernels (kmain_console and kmain_session,
native and release) keep 0.2.33's `.text`, `.rodata`, `.data` and
`.bss` (weak: within 1 KiB, as px53 allowed). `tests/mkw`'s step 6
(lupin refusing the freestanding target) holds its rows at 0.1.55; su
builds unchanged in source.

**P2. The binaries**, in `px13-ubuntu`, each in two builds: pelt
`5448cb27…` (15,201,640, its own 0.2.32), boreutils bu28's 47 (its own
0.2.33), lope `f9a2f064…` (14,426,728, its own 0.2.33) — none moves; su
and sigwolf move (0.2.34's runtime, std `3bacc5f`) from `388d2434…` and
`fa9f7de6…`; edwolf new.

**P3. The recordings held.** At the first boot at the new pins: every
mpx5-jobs image (the 52 pjobs runs, groups, sigs, execs, xsh, gaps,
fds) byte-identical to the committed recordings of real root's guest,
and every user run to the container; mpx5-lope's sessions to the
container; mpx5-accounts' 109 lines. sigwolf's rows do not move at
0.2.34 (no call it makes changed), so **nothing is re-recorded**;
only the new probe's recordings are made.

**P4. What 0.2.34 asks of PAX: `user/edwolf`**, a wolf probe built by
its own pin (`user/edwolf/wolf-toolchain.toml`: 0.2.34, `3bacc5f`;
`tools/mkedwolf`, mksigwolf's shape), static, booted in a new mpx5-jobs
image `eds` (`/bin/edwolf`, then `/bin/as 1000 1000 /bin/edwolf`,
nothing typed), held to real root's guest (recorded twice, the same
bytes) and the container. Its rows, the same as root and as a user:
- **K, `os_fork`**: from `main` with no task live, the parent `(pid,
  h)` and the child `(0, -1)`, the child's pid new and its ppid the
  parent's, its exit read through the handle; a pipe made before the
  fork carries the child's bytes; one write offset shared; **`busy`**
  inside a scope while a task is live and from a task; `ok` again after
  the scope joined.
- **W, `os_signal_wait_fds`**: deadline 0 over a quiet pipe `(-1, 0)`;
  a ready pipe second in the list `(1, 0)`; two ready, the lowest index;
  a 50 ms deadline passes, never early; a meaning raised to itself wins
  over a ready file `(-1, m)`; deadline -2 `invalid`; an empty set and
  a closed handle `io`.
- **T, the terminal**: the console's mode as found (canonical, echo,
  signals, flow, extended on; bits 5–7 0: `ICRNL` and `OPOST` on,
  `ISTRIP` off); the three bits set and read back; set back by hand;
  `os_term_restore_at_exit` in a child that changes the mode and ends by
  a return from `main`, by `os_exit`, by a trap and by `os_exit_signal`:
  the mode back each time and the restore's bytes written; a mode out of
  shape `invalid`, a pipe `io`.
- **S, `fs_sync`, `fs_sync_dir`, the exclusive create**: a file's sync
  ok, a pipe's `io` (EINVAL, 22), a closed handle's `io`; `/tmp`'s
  directory sync ok, a file's `invalid`, a missing name's `not_found`;
  open mode 4 and `fs_open_perm(…, 4, 0o640)` ok on a new name and
  `exists` on a taken one (the mode 0640); the atomic save (exclusive
  temporary, write, sync, rename, directory sync) leaves the new bytes.
- **R, `fs_realpath`**: `/bin/../etc`, a directory with a trailing
  slash, `..` after a link (the link's target's parent), `.` after a
  `chdir`; a dangling link, a missing name and the empty path
  `not_found`; a loop `io` (40); a name under a file `io` (20).
- **N, `os_clock_ns`**: never backwards over 10,000 reads; never below
  `time_now_ms` read before it (at the same anchor). **Named, not
  equal: twenty rounds of about 100 µs of work** read 0 in none of the
  twenty on Linux and in **at least 19 of 20 on PAX**, whose monotonic
  clock advances in 10 ms ticks (§2): the one row the comparison leaves
  out by name, asserted as PAX's own; to file.
**Byte-identical to real root's guest on PAX at the first boot, but
the named clock row, with no kernel change** (weak: the console's
termios as PAX reports it to `os_term_mode`, and PAX's `fsync` of a
pipe).

**P5. pax#107's rows, by boot**: the s253 calls are 0.2.35's, so they
are confirmed at the system-call level by a small static C probe,
`user/elf/hostq.c` (in the `eds` image, root and `pax`): `uname`
sysname `PAX`, machine `x86_64` (`os_name` `pax`, `os_arch` `x86_64`);
`prlimit64(RLIMIT_CORE)` soft 0, hard unlimited (`os_core_limit` `(0,
-1)`); a set, even to the same values, -EPERM (`denied`); `prctl
(PR_SET_DUMPABLE, 0)` 0 and `PR_GET_DUMPABLE` 0 after (`os_core_off`
ok); an inherited descriptor 5, open and not close-on-exec (`F_GETFD`
0), then `F_SETFD FD_CLOEXEC` 0 and `F_GETFD` 1, `/proc/self/fd/5`
naming its file before and after (`fs_adopt`'s two calls); a closed 9
-EBADF. The guest's answers beside them: `Linux` and a set allowed
(lowering, or to itself), so the sysname row and the set row are named,
PAX's own; every other row the guest's bytes. pax#107 stays open for
the wolf rows at the 0.2.35 pin (its own words).

**P6. aspen on PAX** (item 2): `user/aspen.pin` (aspen `103ba46`) and
`tools/mkaspen` (mklope's twin: aspen's tree at the pin, its own
wolf-toolchain.toml's wolf 0.2.33 by digest and std `e036bec`, the same
build line through a static `cc`, ET_EXEC and no PT_INTERP checked,
`aspen --version`, `aspen <sha256> <bytes>`), its digest **ap00's
`b34106b5…` (14,497,536 bytes)** in `px13-ubuntu`, twice (weak:
whether ap00's container was this image). A new suite
**`tests/mpx5-aspen`**, mpx5-lope's shape: one image (kmain_console;
pelt as `/bin/sh`, `/bin/aspen`, boreutils' `env` and `head`, `as`;
`/etc`, `/home/pax` with a few files, `/usr` with a small fixture tree),
two runs typed the same keys (`user/console/aspen.keys`: `aspen /etc`,
`aspen -a -L 2 /home/pax`, `aspen -J /bin | head`, `aspen --du /usr`,
`exit`), root's (`HOME=/`) and `pax`'s (`as 1000 1000 env
HOME=/home/pax`), **byte-identical to the same binaries in the
container, as root and as `pax`, at the first boot, with no kernel
change** (weak: `--du`'s directory sizes, which PAX gives as tmpfs does,
20 bytes an entry), each row's witness present. **The census**
(`strace -f` of those four runs and `aspen --version` on Linux in
`px13-ubuntu`): glibc's start (`execve`, `brk`, `arch_prctl`,
`set_tid_address`, `set_robust_list`, `rseq`, `prlimit64`, `mprotect`,
`readlinkat`, `getrandom`), `openat`, `getdents64`, `statx` or
`newfstatat`, `readlink`, `close`, `write`, `exit_group`, perhaps
`ioctl` and `getcwd`; no thread on these small trees (weak: the stat
pool's thresholds), no `mmap`. **Every call served by PAX but 273 and
334**; no `refused:` line.

**P7. lupin on PAX** (item 3): built from **the `v0.1.55` tag
(`e642f26`)** — the same source as `fcf2fd0` (§2), and the only commit
at which `build.rs` grants D57's stamp, so the binary says
`lupin 0.1.55 (wolf-interp, reference interpreter at pin 294d626)` as
the glibc archive does, never `+dev.fcf2fd0` — with `cargo build
--release --locked --target x86_64-unknown-linux-musl` in the throwaway
Rust image, `user/lupin.pin` and `tools/mklupin` (refusing a Rust that
is not the tree's channel or a missing musl target; it installs
nothing). **The musl build compiles with no source change** (no C
dependency), and **needs `-C relocation-model=static`**: the musl
target's default output is a static PIE (ET_DYN, no PT_INTERP), which
PAX's loader refuses by name; with it, ET_EXEC with no PT_INTERP and no
dynamic section. Two builds in two fresh containers, the same digest
(paths remapped, so the build directory is no part of the bytes).
**The census** (`strace -f` over `lupin run` of three corpus programs
from lupin's own `vendor/upstream/corpus` and `lupin conform-run
--json` of one, on Linux in `px13-ubuntu`): `execve`, `arch_prctl`,
`set_tid_address`, `poll` (Rust's start reads fds 0–2), `rt_sigaction`
(SIGPIPE ignored; SEGV and BUS for the stack-overflow report),
`sigaltstack`, `mmap`, `munmap`, `mprotect`, `brk`, `openat`, `read`,
`close`, a stat call, `getcwd` or `readlink`, `getrandom`, `ioctl`,
`write`, `exit_group`; perhaps `mremap`, `sched_getaffinity`, `futex`,
`clone` (weak: whether lupin starts a thread). **Every call served by
PAX but `mremap` (25) if it is made**, which the allocator then does
without (weak); no `set_robust_list` or `rseq` (musl's start makes
neither). In a new suite **`tests/mpx5-lupin`**: `/bin/lupin`,
`/usr/share/lupin/hello.lu`, `loop.lu`, `signal.lu` (a signal row:
`os_signal_number` and `os_signal_text` of a meaning, and a send lupin
refuses by name), `host.lu` (the clock, the environment and the tree);
a typed session (`lupin run /usr/share/lupin/hello.lu`; `cat > x.lu`
typed then run; `lupin conform-run --json` of `loop.lu`; `lupin run`
of `signal.lu`; `lupin conform-run --json` of `host.lu`; `exit`) as
root and as `pax`, **byte-identical to the same binary in the
container at the first boot, with no kernel change**. **The checked
machine**: the contract's "what the checked machine answers on PAX"
can only be lupin's machine here — wolf's checked machine is the `wolf`
binary (`conform-run --checked`), which ruling #110 puts in the dev
image, and the glibc-linked `wolf` cannot start on PAX (no dynamic
loader) — so the row is `lupin conform-run --json` of `host.lu`: the
record's verdict and stdout on PAX equal Linux's (the clock as a
duration, never a time; `HOME` per run; the tree's names), and wolf's
checked machine is named as owed to the dev image (pax-dev).

**P8. Existing suites.** Every suite green as root and as a user at the
new pins on kasumi, native BIOS under `taskset -c 0-3` (mpx5-jobs every
image, mpx5-lope, mpx3-shell, mpx3-tree, mpx5-accounts,
mpx3-boreutils, mpx5-users, mpx3-speaker, mpx3-console,
mpx3-screen, mpx3-threads, `mkw`, `tour`, `tests/ci-plan`), and in
CI's run of the pull request (the pin is FULL: every suite, every leg).
No fixed reference moves.

**P9. Plants**, each a branch never merged, one commit, by dispatch on
one leg (`-f tier=pr -f suites=…`): **A** (edwolf, hostq) a kernel
break: `fsync` of a pipe answering 0 — red at edwolf's pipe-sync row
as root and `pax` (J13), every other row green; **B** (aspen) a kernel
break: a directory's `st_size` answered 0 — red at `aspen --du /usr`'s
sizes and its report as root and `pax` (the container keeps tmpfs's),
the other rows green; **C** (lupin) the image without
`/usr/share/lupin/hello.lu` — red at the session's first row and the
witness that names it, root and `pax`, the rest green. Each prediction
by row is added after the first boot and before its plant runs.

**P9, by row** (added after the first boots of the eds image and the
two new suites, before any plant ran; plant C is a kernel break, not
the image change §3 first named, so every plant is a kernel's). **A**,
`kernel/files`' `fsync` answering 0 for what it cannot synchronise
(`fsync(2)`'s -EINVAL for a pipe): J13 red at eds and eds-user (`S:
fs_sync of a pipe: ok`, the recording's `io (22)`), J4 without that
row, J3 for eds-user; hostq and hostq-user green; J6 green. **B**,
`kernel/tree`'s directory size answered 0 (tmpfs's 40 and 20 an entry
gone): A1 red at `aspen --du /usr` as root and as `pax` (every
directory's size and the report's bytes, 125 for 445), A2 and A3 green
(no witness row names a size). **C**, PAX's `stat` (4), the call the
musl lupin makes and glibc's programs do not (they make `newfstatat`
and `statx`), answering -ENOENT for every path: every lupin row red, U1
and U2 (hello, the typed program, loop's record, signal.lu, host.lu) as
root and as `pax`, U3 green (an ENOENT is no ENOSYS); weak: lupin's
words for the program it cannot find.

**P10. Cost.** The kernel's `.text` at 0.2.34 against 0.2.33: 0 bytes,
every kernel (P1).

**P11. The playground** rebuilt by the orchestrator's two scripts,
extended (pre-edit copies kept) with `tools/mkaspen`, the musl lupin,
`/bin/aspen`, `/bin/lupin`, `/usr/share/lupin/`, and a motd naming
wolf 0.2.34, aspen `103ba46` and lupin 0.1.55; a new
`pax-playground.iso` digest, the maintainer's sessions (greet.sh, `g
-`, `aspen /`, `lupin run hello.lu`) typed on it, copied to nomad-1
`~/pax-playground/pax-playground.iso` and hashed there twice.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | one commit a pin; the kernel builds on 0.2.34 with no source change and no section moves; mkw step 6 holds at lupin 0.1.55; su builds unchanged | `kernel/wolf.pin` `bb98155` (with the tour's line), `user/su` `4f7f875`, `user/sigwolf` `099bcbd` (ci.yml's comments `2b3ef1f`); every kernel built with no source change; **not one section moved** on any of the four kernels (§J); `tests/mkw` PASS (step 6's rows as written) and `tests/tour` PASS at the pins alone; su built unchanged in source | right |
| P2 | pelt, boreutils, lope unchanged; su and sigwolf move; edwolf new; each in two builds | pelt `5448cb27…`, the boreutils of every image bu28's, lope `f9a2f064…` (unchanged); su `388d2434…` → **`fbc2035e…`** (14,441,376), sigwolf `fa9f7de6…` → **`dba181aa…`** (14,958,920); edwolf **`1bfd0ca2…`** (15,036,336), hostq **`9eca259e…`** (790,520); each the same in two kasumi builds and in CI (§B) | right |
| P3 | every recording held at the first boot at the pins; nothing re-recorded | the pins alone (`e32ffb3`'s tree): **mpx5-jobs PASS, 225 PASS lines, no FAIL** — the 52 pjobs runs, groups, sigs and sigs-user (sigwolf now built by 0.2.34: 26 lines each, the committed bytes), execs and xsh, gaps, fds; mpx5-lope PASS; mpx5-accounts PASS (its 109 lines held, root, `pax` and the container); nothing re-recorded | right |
| P4 | edwolf's rows byte-identical to real root's guest at PAX's first boot, but the named clock row; no kernel change | real root's guest recorded twice, the same bytes (59 lines root, 59 user; 58 compared, the `~N:` line apart); **PAX byte-identical at its first boot of the eds image**, root and `pax`, and the user's to the container's (J13, J3, J4, J6); `~N:` 19 of 20 and 20 of 20 rounds at 0 ns on PAX, 0 of 20 on the guest; no kernel change. The weak points held: the console's mode reads as the guest's pseudo-terminal's (flow off on both: vmjob and linux-tree clear IXON, PAX has none), and PAX's `fsync` of a pipe is -EINVAL | right |
| P5 | pax#107's rows by a C probe: PAX, x86_64, soft 0 hard unlimited, sets -EPERM, dumpable served, F_GETFD/F_SETFD served; sysname and set rows named | every row as predicted, root and `pax`, at the first boot (§E); the guest: `Linux`, both sets 0 | right |
| P6 | aspen `b34106b5…` twice; its session byte-identical to the container at the first boot; the census glibc's start plus the tree calls, every one served but 273 and 334 | **`b34106b5…` (14,497,536), twice, ap00's digest**, and the same in CI's runner; the session **byte-identical at the first boot**, root (37 lines) and `pax` (38), `--du`'s directory sizes PAX's tmpfs numbers; A2's first text wrong in its own lines (tree counts the root it lists: `1 directory, 3 files`, `5 directories`; a user's home holds pelt's `.sh_history` between `.profile` and `Script`), corrected before any plant (§F); the census **18 calls**, `sched_getaffinity` among them (unpredicted), no `mmap`, no thread; every one served but 273 and 334 | right but A2's text |
| P7 | lupin from the tag, compiling with no source change, ET_EXEC only with `relocation-model=static`; two builds one digest; the census Rust's start and the interpreter's calls, every one served but `mremap` if made; the session byte-identical at the first boot | the musl build compiles at the first try; **without the flag: `DYN (Position-Independent Executable file)` with a `DYNAMIC` segment** (measured, `notes/px57/pie.sh`); with it **`08a7766b…` (7,405,200), ET_EXEC, no PT_INTERP, no dynamic section, twice, and the same bytes in CI's runner**; `--version` the release's line; the census **31 calls**: lupin starts a thread for every run (`clone`, `futex`, `gettid`, `prctl(PR_SET_NAME, "wolf-interp-par")`, 64 MiB stacks reserved `PROT_NONE`), musl makes the legacy `open`, `stat`, `lstat`, no `mremap`, no `set_robust_list`, no `rseq`; **every call served by PAX**; the session **byte-identical at the first boot, root and `pax`**, U3: -ENOSYS only pelt's 273 and 334; host.lu's first text reached `List.insert`, std.list's (the image has no std tree: refused by name on both sides), rewritten without std before any plant (§G) | right but host.lu's first text |
| P8 | every suite green at the pins on kasumi; no fixed reference moves | at the pins alone, every suite **PASS, no FAIL and no SKIP line**: mpx5-jobs (225 PASS), mpx5-lope (8), mpx5-accounts (10), mpx3-shell (70), mpx3-tree (64), mpx3-boreutils (12), mpx5-users (110), mpx3-speaker (27), mpx3-console (26), mpx3-screen (7), mpx3-threads (11), mkw (7), tour (22); the last four twice (beside it on cpus 4-7, the same verdicts); at the head mpx5-jobs every image, eds among them (238 PASS), mpx5-aspen, mpx5-lupin PASS; `tests/ci-plan` 200 PASS; no fixed reference moved | right on kasumi |
| P9 | plants A, B, C red at the rows named | A **39680111521** red at exactly the rows (J13 and J4 at eds and eds-user, J3 for eds-user; hostq green; J6 green); B **39680114939** red at exactly A1's `--du /usr` (445 → 125 bytes), A2 and A3 green; C **39680118584** red at U1 and U2 at every lupin row, root and `pax` (lupin's words: `` `/usr/share/lupin/hello.lu` is not a readable file ``), **and at U3** (init ended with status 2: pelt's `exit` takes the last command's status, lupin's 2) — the one row predicted green (§K) | right but U3 in C |
| P10 | 0 bytes of `.text` | 0 bytes, every section, every kernel (§J) | right |
| P11 | the playground rebuilt with aspen and lupin, the sessions typed, on nomad-1 | build.sh and assemble.sh extended (the pre-edit copies kept), the second assemble rc 0 after the first failed on an apostrophe in the motd (§M); **`pax-playground.iso` `242ecec2…`** (79,415,296 bytes), booted once with the maintainer's sessions typed (`g -`, `aspen /`, `lupin run hello.lu`, `./Script/greet.sh` as `pax`: `hi`), copied to nomad-1 and hashed there twice | right |

## A. The pins (item 1)

Each its own commit: `bb98155` (`kernel/wolf.pin`: wolf 0.2.34
`9da7bdcf`, archive `88a9dd3d…` 80,433,878 bytes; lupin 0.1.55
`e642f263`, archive `1152abc0…` 2,966,156 bytes; with
`kernel/pax_tour/pax_tour.lu`'s `wolf 0.2.34` line, which `tests/tour`
holds to the pin), `4f7f875` (`user/su/wolf-toolchain.toml`: 0.2.34 by
digest, wolf-std `3bacc5f`), `099bcbd` (`user/sigwolf/wolf-toolchain.toml`:
the same), `2b3ef1f` (ci.yml's two comments). The archives read twice
from the release API (§2) and twice by `sha256sum` of the downloads on
kasumi (the same digests; `wolf --version` `wolf 0.2.34 (wolfgang, pin
9da7bdc)`, its bundled std `e036bec`; `lupin --version` `lupin 0.1.55
(wolf-interp, reference interpreter at pin 294d626)`). pelt `90d7c64`
and boreutils `cc64f68` were the contract's already; lope `5ac37df`
stays (not this lane's). No pax wolf source declares one of 0.2.34's
seven names, so nothing meets W0304; **the kernel builds unchanged**:
no file under `kernel/` but the pin and the tour's line moved.

aspen: the coordinator said during the lane that ap01 merged (aspen
trunk `476edee`, a new digest). aspen had been built at `103ba46` by
then (twice, §F), so the lane finished at `103ba46` as told; the next
pins lane moves `user/aspen.pin`.

## B. The binaries (item 1)

Built in `px13-ubuntu` (`ad8964505189`) on kasumi by the suites' own
tools, each in two builds or more, and again on CI's runner:

| program | built by | digest, bytes | where it was the same |
|---|---|---|---|
| pelt (`90d7c64`, its own 0.2.32) | `tools/mkpelt` | `5448cb27d882553bccba66dbde2c4aaba417a7501ae1c6bf3944af0d00a93c5d`, 15,201,640 | sh21's; every suite build (first chain, eds2, s1, s2, the playground), CI's plants |
| boreutils (`cc64f68`, its own 0.2.33) | `tools/mkboreutils` | bu28's: `cat` `930e58ac…`, `cut` `f5735f5b…`, `kill` `b0e45268…`, `sleep` `4d865fb9…`, `timeout` `245f8414…`, `tr` `8e9d4431…`, `wc` `f7596ab4…`, `true` `a3bf0296…`, `env` `88faec90…`, `head` `13eb6f10…`, … | every build; CI |
| lope (`5ac37df`, its own 0.2.33) | `tools/mklope` | `f9a2f064077f6bb33ede9219608b6fe72d4a45a66c84f61f3f9d9e5e94f5066c`, 14,426,728 | lp00's; the first chain, the playground |
| su (0.2.34 / `3bacc5f`) | `tools/mksu` | **`fbc2035e74a57f78d79c89fe395cedd1f95aa9a08613f1baba9f67a4fabc5780`, 14,441,376** (px53's `388d2434…`, 14,025,128) | the first chain (mpx5-accounts), the playground |
| sigwolf (0.2.34 / `3bacc5f`) | `tools/mksigwolf` | **`dba181aac91fbfdef56df62baf0ded0a8517c34ca9e8c5bfb7751de6be5e3ac6`, 14,958,920** (px53's `fa9f7de6…`, 14,529,304) | the first chain, eds2 |
| edwolf (0.2.34 / `3bacc5f`, its own pin) | `tools/mkedwolf` | **`1bfd0ca229b4c70bd6aeba6a93378817c8bc350aac4ad4c26a9a3252d38070cc`, 15,036,336** | eds1, eds2, h1; CI's plant A (39680111521) |
| hostq | `tools/mkhostq` | **`9eca259ed970c48f220b3e10a477b639e63e36c38b92438e58dbe8559da7fa92`, 790,520** | eds1, eds2, h1; CI's plant A |
| aspen (`103ba46`, its own 0.2.33 / `e036bec`) | `tools/mkaspen` | **`b34106b5bf15252e1024d1bd67839044008b5e5f4f4ae483b75821a329cda384`, 14,497,536** (ap00's) | aspen1, aspen2, s1, s2, the playground; **CI's runner the same bytes** (plant B, 39680114939), where ap00's had differed |
| lupin (`v0.1.55`, Rust 1.97.1, musl) | `tools/mklupin` | **`08a7766b21ec00afe780d9d76fb9cee548b1bb22e2a06f9c5cfcb3d167e197f8`, 7,405,200** | lupin1, lupin2 (two fresh containers), s1, s2, the playground; **CI's runner the same bytes** (plant C, 39680118584) |
| as | `tools/mkas` | `fb82459177a298f33df33285da523c677495022e6b37eafd27ab287a06e53270`, 785,416 | every build; CI |

## C. The recordings held (item 1)

The first build was the pins alone (`e32ffb3`'s tree: the four pin
commits and the scripts, nothing else), booted by that tree's own
suites (native BIOS, `taskset -c 0-3`) against the recordings px51 to
px56 committed: **mpx5-jobs PASS, 225 PASS lines, no FAIL** — the 52
pjobs runs (J9), groups and groups-user (J10, 91 lines), sigs and
sigs-user (J11, 26 lines each: sigwolf at 0.2.34 answers every row
0.2.33's did), execs, execs-user, xsh, xsh-user (J12, 107 and 50), gaps
and fds (J7, J8), the busybox probe and shells (J1, J2), the user runs
to the container (J3), J6 on every boot
(`notes/px57/kasumi-first-chain.out`); **mpx5-lope PASS** (L1 to L4,
root and `pax`); **mpx5-accounts** PASS (its 109-line recording held, root, `pax` and the container; su `fbc2035e…`). Nothing was re-recorded:
the only new recordings are the eds image's (§D, §E).

## D. What 0.2.34 asks of PAX: edwolf (item 1)

`user/edwolf/edwolf.lu`, built by its own pin (`user/edwolf/wolf-toolchain.toml`,
`tools/mkedwolf`), compiled at the first try under `--deny-warnings`.
In mpx5-jobs' new `eds` image (kmain_console; `/bin/edwolf`, then
`/bin/as 1000 1000 /bin/edwolf`, then hostq's two runs; nothing typed;
`/tmp` 1777). Real root's guest (kasumi's 7.2.8 `f4c00d5d…`,
`notes/px52/vmjob.c` unchanged as pid 1, `2a3a7f57…`; the suite build's
own eds archive `c36949e3…`), recorded twice, **the same bytes**
(`notes/px57/kasumi-eds-recordings-twice.out`). **On PAX at its first
boot of the image, byte-identical to the guest, as root and as `pax`,
and the user's to the container's** (J13, J3, J4, J6:
`notes/px57/kasumi-first-eds.out`), with no kernel change. Root's 59
lines (the user's the same but the first and `/tmp/ed-1000`; the `~N:` line PAX's own):

```
edwolf: px57's probe of wolf 0.2.34's calls, as root
K: fork from main, no task live: the parent's answer has a pid true and a handle true
K: through a pipe made before the fork: the child's pid new true, its ppid the parent's true, its answer (0, -1)
K: the child exit 7, read through its handle
K: one write offset, the parent's a, the child's b, the parent's c after the wait: abc
K: fork inside a scope while a task is live: busy
K: fork from a task: busy
K: fork after the scopes joined: ok, the child exit 0
W: deadline 0 over two quiet pipes: (-1, 0)
W: the second pipe ready: (1, 0)
W: both ready, the lowest index: (0, 0)
W: a 50 ms deadline over two quiet pipes: (-1, 0), never early: true
W: USER raised to itself, a ready pipe beside it: the meaning wins: (-1, 512)
W: the ready pipe answers the next wait: (0, 0)
W: deadline -2: invalid
W: an empty set: io
W: a closed handle: io
T: the terminal's mode as found: canonical true, echo true, signals true, flow false, extended true; raw_cr false, raw_output false, strip8 false; vmin 1, vtime 0
T: RAW_CR, RAW_OUTPUT and STRIP8 set and read back: true true true; the rest as set: true
T: set back by hand, the mode as found: true
T: the runtime restored the terminal (restore-return)
T: restore-return: the child exit 0; the mode back: true
T: the runtime restored the terminal (restore-exit)
T: restore-exit: the child exit 3; the mode back: true
wolf-trap: bounds
  at ./edwolf.lu:211:9
T: the runtime restored the terminal (restore-trap)
T: restore-trap: the child exit 134; the mode back: true
T: the runtime restored the terminal (restore-signal)
T: restore-signal: the child signal 15; the mode back: true
T: restore_at_exit of mode -1: invalid
T: restore_at_exit of bit 24: invalid
T: restore_at_exit of a pipe: io
S: fs_sync of a file: ok
S: fs_sync of a pipe: io (22)
S: fs_sync of a closed handle: io (0)
S: fs_sync_dir of /tmp: ok
S: fs_sync_dir of a file: invalid
S: fs_sync_dir of a missing name: not_found
X: open mode 4, a new name: ok
X: open mode 4, the name taken: exists
X: open_perm mode 4 0o640, a new name: ok, kind 0, mode 640
X: open_perm mode 4 0o640, the name taken: exists
S: the atomic save (an exclusive temporary, its write and sync, the rename, the directory's sync): the new bytes
R: /bin/../etc: /etc
R: a directory with a trailing slash: /tmp/ed-0/d
R: .. after a link to /etc: /
R: a link to /etc: /etc
R: a dangling link: not_found
R: a missing name: not_found
R: the empty path: not_found
R: a loop of links: io (40)
R: a name under a file: io (20)
R: . after a chdir: /tmp/ed-0/d
R: a relative name through a link: /etc
N: os_clock_ns over 10000 reads, backwards: 0
N: os_clock_ns / 1000000 read after time_now_ms, never smaller: true
~N: twenty rounds of work read 0 ns in 0 of 20 (the work's sum 13349440)
edwolf: done
```

The one line PAX answers otherwise, by name: **`~N:` read 0 ns in 19 of
20 rounds (root) and 20 of 20 (`pax`) on PAX**, 0 of 20 on the guest:
PAX's `clock_gettime` answers the monotonic clocks from the PIT's ticks
(`kernel/user`'s `now_ns`, 10,000,151 ns a tick), so `os_clock_ns` is
10 ms granular there and yew's G8 (a keypress's latency in nanoseconds)
reads 0 on PAX. J13 holds that line to PAX's answer (10 or more of 20)
and to Linux's in the recording (none), apart from the comparison. To
file (§N). A restore child is started with the parent's descriptor 0
(`os_spawn_fds(exe, [how], [0, 0])`): a plain spawn's 0 is the null
device (`[os.proc.spawn]`), which `os_term_mode` answers `io` (measured
in the probe's first text, in the container, before any commit).

How PAX serves each (inferred from its source and the rows; PAX has no
tracer):

| call (wolf) | host calls (s247, s248's spec) | on PAX |
|---|---|---|
| `os_fork` | `rt_sigprocmask` around `fork` (glibc's: `clone` with SIGCHLD), the child's hub `pipe2` ×3 and `fcntl`s | served since px14 (fork), px17 (pipe2, fcntl); the child's pid, ppid, shared offsets and pipe: rows K |
| `busy` | none: decided before the host is asked | — |
| `os_signal_wait_fds` | `dup` of each handle, `poll` over them and the wake pipe | served (px24's `poll`); W |
| `os_term_mode`, `os_term_set_mode` (bits 5-7: ICRNL, OPOST, ISTRIP) | `ioctl(TCGETS)`, `ioctl(TCSETSW)` with SIGTTOU blocked | served by `kernel/console` (px13, px48); the three flags read back as set |
| `os_term_restore_at_exit` | `dup` (≥ 3, close-on-exec), at each exit `tcsetattr` and `write` | served; the mode back after a return, `os_exit`, a trap and `os_exit_signal` |
| `fs_sync`, `fs_sync_dir` | `fsync`; `open(O_DIRECTORY)` and `fsync` | served (px27): 0 for a file or a directory, -EINVAL for a pipe (plant A breaks it) |
| open mode 4, `fs_open_perm(…, 4, …)` | `openat(O_CREAT|O_EXCL)` | served: EEXIST for a taken name, the mode as given under umask 022 |
| `fs_realpath` | glibc's `realpath(3)`: `readlink`s, `getcwd` | served: every row Linux's, ELOOP 40 and ENOTDIR 20 included |
| `os_clock_ns` | `clock_gettime(CLOCK_MONOTONIC)` (no vDSO on PAX: a call) | served, 10 ms granular (named above) |

## E. pax#107's rows, by boot (item 1)

s253's calls (`os_name`, `os_arch`, `os_core_limit`,
`os_set_core_limit`, `os_core_off`, `fs_adopt`) are wolf-lang#847's, for
0.2.35, open at the time of this lane: no 0.2.34 program can name them.
So `user/elf/hostq.c` asks the kernel the calls s253's spec says each
makes, in the eds image after edwolf, root and `pax`, held to the same
guest (recorded twice, the same bytes) and the container:

| s253's call | system call | PAX (first boot) | Linux 7.2.8 (the guest) |
|---|---|---|---|
| `os_name` | `uname`: sysname | **`PAX`** (so `pax`) | `Linux` |
| `os_arch` | `uname`: machine | **`x86_64`** | `x86_64` |
| `os_core_limit` | `prlimit64(RLIMIT_CORE)` read | **soft 0, hard unlimited** (`(0, -1)`) | soft 0, hard unlimited |
| `os_set_core_limit` | `prlimit64` set, to its own values / to (0, 0) | **-1 (EPERM) and -1** (`denied`: pax#93's table) | 0 and 0 |
| `os_core_off` | `prctl(PR_SET_DUMPABLE, 0)`; `PR_GET_DUMPABLE` before and after | **0; 1 then 0** | 0; 1 then 0 |
| `fs_adopt` | an inherited descriptor 5: `F_GETFD`, `F_SETFD FD_CLOEXEC`, `F_GETFD`; `/proc/self/fd/5` before and after; a closed 9 | **0 (open, not close-on-exec), 0, 1; the file's path both times; -9 (EBADF)** | the same |

Every PAX answer s253's spec read from PAX's source, confirmed by boot.
The sysname and the two sets are the `~H:` rows, PAX's own by name (J13
holds them to PAX's words on PAX and to Linux's in the recording). Byte
for byte the rest, root and `pax`; the container's hard limit is
tools/linux-tree's `--ulimit core=0:0`, so that one row is left out of
the container's comparison (named, as sigwolf's). pax#107 asks for a
sigwolf-style row of each wolf call at the 0.2.35 pin: those wait for
0.2.35 (§N).

## F. aspen on PAX (item 2)

`user/aspen.pin` (`d196374`, reworded `6c401cd`) and `tools/mkaspen`
(`6f87a88`, `3872b23`): aspen's tree at `103ba46`, its own
wolf-toolchain.toml (wolf 0.2.33 by digest, wolf-std `e036bec` as
`WOLF_STD`), aspen's own build line (`wolf build --release --no-cache
--deny-warnings src/aspen.lu -o target/static/aspen`, through a `cc`
that adds `-static`), ET_EXEC and no PT_INTERP checked, `aspen
--version` (`aspen v0.1.0`). **`b34106b5…`, 14,497,536 bytes, in two
builds (`notes/px57/aspen-twice.sh`), ap00's digest**, and the same on
CI's runner.

`tests/mpx5-aspen` (`5d1f966`, corrected `2ac53b8`), mpx5-lope's
shape: one image (pelt as `/bin/sh`, `/bin/aspen`, boreutils' `env` and
`head`, `as`; `/etc`, `/home/pax` 1000:1000 with `.profile`,
`notes.txt` and `Script/greet.sh`, a small `/usr`), two runs typed
`user/console/aspen.keys` (`aspen /etc`, `aspen -a -L 2 /home/pax`,
`aspen -J /bin | head`, `aspen --du /usr`, `exit`): root's (`HOME=/`)
and `pax`'s (`as 1000 1000 env HOME=/home/pax`). **At the first boot,
byte-identical to the same binaries in the container, root (37 lines)
and `pax` (38)** (A1, A3), with no kernel change; `--du`'s directory
sizes are tmpfs's on both sides (40 and 20 an entry, `kernel/tree`):

```
$ aspen --du /usr
[        445]  /usr
|-- [         40]  lib
`-- [        325]  share
    `-- [        265]  pax
        |-- [         48]  README
        `-- [        137]  keys
            `-- [         77]  aspen.keys

         445 bytes used in 5 directories, 2 files
```

A2's first text was wrong in its own lines (`0 directories, 3 files`
and `4 directories`: tree counts the root it lists; a user's home holds
pelt's `.sh_history` between `.profile` and `Script`), corrected in
`2ac53b8` after the first boot and before any plant, A1 having held
there; at the head every A row PASS (`notes/px57/kasumi-new-suites.out`).

**aspen's census** (`notes/px57/census.sh`; `notes/px57/census/aspen-*`):
`strace -f -n` of `aspen --version` and the session's four commands,
chrooted in the same tree, PAX's environment, on Linux 7.2.8 in
`px13-ubuntu`. **18 calls**: §H.

## G. lupin on PAX (item 3)

**Built from the `v0.1.55` tag** (`e642f26`): wolf-interp's source at
`fcf2fd0` is the tag's (`git diff e642f26 fcf2fd0 -- src Cargo.toml
Cargo.lock build.rs rust-toolchain.toml vendor` empty), and the tag is
the one commit at which `build.rs` grants D57's stamp, so the binary's
`--version` is the release's line, the glibc archive's. The throwaway
image `localhost/px57-rust` (`e93022a6…`, FROM `px13-ubuntu`: rustup-init
`5be191e8…` checked, Rust 1.97.1 minimal, the musl target;
`notes/px57/rust/Containerfile`), since `px13-ubuntu` has no Rust.
`tools/mklupin` (`5eaa000`, `03f9a0f`) and `user/lupin.pin` (`8744fa9`,
`3d3d6ac`): the tag fetched with itself, the commit checked, D57's tag
at HEAD checked, the tree's channel the pin's, the target installed
(the tool installs nothing), `cargo build --release --locked --target
x86_64-unknown-linux-musl` with `+crt-static`, `relocation-model=static`
and the build and registry paths remapped.

- **The musl build compiled at the first try, with no source change.**
- **The target's default output is a static PIE**: the same build
  without `relocation-model=static` is `DYN (Position-Independent
  Executable file)` with a `DYNAMIC` segment (`notes/px57/pie.sh`,
  `c12b8005…`), which `kernel/elf` refuses by name; with it,
  **ET_EXEC, no PT_INTERP, no dynamic section**: `08a7766b…`,
  7,405,200 bytes, in two fresh containers the same bytes
  (`notes/px57/lupin-twice.sh`), and on CI's runner the same bytes
  (plant C's run: `rustup` installed 1.97.1 and the target there).
- **The census** (`notes/px57/census/lupin-*`): `lupin --version`;
  `lupin run` of three programs of lupin's own corpus, each alone in a
  directory (a directory is a module, D32): `hello.lu`,
  `fs/roundtrip.lu` (in a tree with its `target/`), `procs.lu`; `lupin
  conform-run --json` of `os/args_cwd.lu`; and the session's programs
  as the session runs them. **31 calls**: §H.

The image: `/bin/lupin`, `/usr/share/lupin/` with `hello.lu`, `loop.lu`,
`signal.lu` (INTERRUPT's number, then its words: lupin refuses
`os_signal_text` by name, `unsupported`, exit 4) and `host.lu` (the
clock, the environment, the tree), each `//! member: false` (four
programs in one directory are one module otherwise, E0302: measured).
`tests/mpx5-lupin` (`9e17fb0`), mpx5-aspen's shape, the session
`user/console/lupin.keys`: `cd`; `lupin run /usr/share/lupin/hello.lu`;
a program typed into `cat > x.lu` line by line and ^D; `lupin run x.lu`;
`lupin conform-run --json` of `loop.lu`; `lupin run` of `signal.lu`;
`lupin conform-run --json` of `host.lu`; `exit`. **At the first boot,
byte-identical to the container's, root and `pax`** (U1), U3 green
(-ENOSYS only pelt's 273 and 334: the musl lupin makes neither); root's
first host.lu reached `List.insert`, std.list's, and the image carries
no std tree, so lupin refused it by name on both sides (the same bytes);
`host.lu` sorts by selection since `5249880`, before any plant, and at
the head every U row PASS. Root's session:

```
$ cd
$ lupin run /usr/share/lupin/hello.lu
hello, wolf
$ cat > x.lu
//! member: false
fn main() -> !int {
    print("typed at PAX's console, run by lupin")
    0
}
$ lupin run x.lu; echo st=$?
typed at PAX's console, run by lupin
st=0
$ lupin conform-run --json /usr/share/lupin/loop.lu
{"protocol":1,"impl":"lupin","impl_version":"0.1.55","commit":"e642f26","file":"//usr/share/lupin/loop.lu","phase_reached":"run","seeded":false,"diagnostics":[],"warnings":[],"verdict":"exit(0)","stdout_sha256":"0803e1c5…","stdout_inline":"1 squared is 1\n…the sum of the squares: 385\n"}
$ lupin run /usr/share/lupin/signal.lu; echo st=$?
INTERRUPT is signal 2 here
//usr/share/lupin/signal.lu: unsupported: `os_signal_text` reads the C library's words for a signal: std has no `strsignal`, and this machine admits no `unsafe` ([os.signal.text], [os.signal.group.note] R8)
st=4
$ lupin conform-run --json /usr/share/lupin/host.lu
{"protocol":1,…,"verdict":"exit(0)",…,"stdout_inline":"clock: a 20 ms sleep, at least 20 ms passed: true\nenv: HOME before the program sets it: missing\nenv: HOME after env_set: /home/wolf\ntree: x.lu in the working directory: kind 0, 96 bytes\ntree: /usr/share/lupin/hello.lu\ntree: /usr/share/lupin/host.lu\ntree: /usr/share/lupin/loop.lu\ntree: /usr/share/lupin/signal.lu\n"}
$ exit
```

**What the machine answers on PAX for a program that reads the clock,
the environment and the tree** — lupin's machine, as `conform-run
--json` records it (wolf's checked machine is the `wolf` binary,
glibc-linked and dynamic, which cannot start on PAX and which ruling
#110 puts in the dev image: it is owed to pax-dev, §N): **the same
record on PAX as on Linux**, root's and `pax`'s. The clock: a 20 ms
sleep measured as at least 20 ms (PAX's 10 ms ticks round a sleep up,
never down). The environment: lupin's machine never reads the host's
(`src/eval/builtin.rs`: `env_get` reads the machine's own overlay, the
checked machine's posture), so `HOME` is `missing` on every host until
the program sets it, and then the program's value. The tree: the host's
files, served inside the working directory and refused by name outside
it (`[os.fs.path.domain]`): from `/` (root) `/usr/share/lupin`'s four
names; from `/home/pax` the record's verdict `unsupported`, with
`x-unsupported`: `` `fs_read_dir("/usr/share/lupin")` resolves outside
the working directory … declines the rest by name rather than observing
it `` — on PAX and on Linux alike. **The verdict: lupin ships**:
`/bin/lupin` runs on PAX unmodified, every call it makes is one PAX
serves, and every session row is Linux's.

## H. The calls, by program (items 2 and 3)

The unions of every traced run (`notes/px57/census/*.union`, per run
`*.calls`, failures `*.fails`), and how PAX answers each:

| nr | call | aspen | lupin | on PAX |
|---|---|---|---|---|
| 0 | read | | yes | served |
| 1 | write | yes | yes | served |
| 2 | open | | yes (musl's) | served |
| 3 | close | yes | yes | served |
| 4 | stat | | yes (musl's; ENOENT for its std and corpus probes) | served (plant C breaks it) |
| 5 | fstat | yes | yes | served |
| 6 | lstat | | yes (musl's) | served |
| 7 | poll | | yes (Rust's start: fds 0-2) | served (px24) |
| 9, 10, 11 | mmap, mprotect, munmap | mprotect | yes (thread stacks: 64 MiB `PROT_NONE` then `mprotect`; the allocator) | served |
| 12 | brk | yes | yes | served |
| 13, 14 | rt_sigaction, rt_sigprocmask | | yes (SIGPIPE ignored; SEGV and BUS for the overflow report) | served (px26) |
| 16 | ioctl | | yes (`--version`: ENOTTY, not a terminal) | served |
| 56 | clone | | yes (a thread every run, `wolf-interp-par`) | served (threads: mpx3-threads) |
| 59 | execve | yes | yes | served |
| 60 | exit | | yes (a thread's end) | served |
| 72 | fcntl | | yes | served |
| 79 | getcwd | | yes | served |
| 87 | unlink | | yes (roundtrip) | served |
| 89 | readlink | | yes (EINVAL for a non-link) | served |
| 131 | sigaltstack | | yes | served |
| 157 | prctl | | yes (PR_SET_NAME) | served |
| 158 | arch_prctl | yes | yes | served |
| 186 | gettid | | yes | served |
| 202 | futex | | yes (EAGAIN) | served |
| 204 | sched_getaffinity | yes (`--du`: the stat pool's size) | | served |
| 217 | getdents64 | yes | yes | served |
| 218 | set_tid_address | yes | yes | served |
| 230 | clock_nanosleep | | yes (host.lu's sleep) | served |
| 231 | exit_group | yes | yes | served |
| 257 | openat | yes (ENOENT probes) | | served |
| 267 | readlinkat | yes (`/proc/self/exe`) | | served |
| 273, 334 | set_robust_list, rseq | yes (glibc's start) | **no** | -ENOSYS (glibc copes) |
| 302 | prlimit64 | yes (RLIMIT_STACK) | | served |
| 318 | getrandom | yes | | served |
| 332 | statx | yes (EFAULT: glibc's probe; ENOENT) | | served |

Not seen on Linux and made on PAX (inferred, no tracer): `clock_gettime`
for both (Linux answers it from the vDSO; PAX gives none). **aspen: 18
calls, every one served but 273 and 334; lupin: 31, every one served.
Refused: none.** No `mremap` (the prediction's weak point never arose).
A3 and U3 on every boot: -ENOSYS only 273 and 334, no `refused:` line.

## I. Existing suites on kasumi (P8)

Native, BIOS, TCG, every boot under `taskset -c 0-3` (the first chain)
or `4-7` (the head's), every build in `px13-ubuntu` (the lupin suite's
in the Rust image): **the pins alone** (`e32ffb3`,
`notes/px57/kasumi-first-chain.out`): mkw (7 PASS) and tour (22) PASS; mpx5-jobs every image (225 PASS), mpx5-lope (8), mpx5-accounts (10), mpx3-shell (70), mpx3-tree (64), mpx3-boreutils (12), mpx5-users (110), mpx3-speaker (27), mpx3-console (26), mpx3-screen (7), mpx3-threads (11): **every one PASS, no FAIL and no SKIP line**; the last four run twice (a second chain on cpus 4-7 beside the first), the same verdicts. **The head**
(`e677afa`, the code as at the final head; `notes/px57/kasumi-head.out`):
mpx5-jobs every image, the eds image among them, **PASS, 238 PASS lines, no FAIL**; mpx5-aspen
and mpx5-lupin PASS (`notes/px57/kasumi-new-suites.out`); `tests/ci-plan`
**200 PASS** (eight new cases, two widened). No fixed
reference moved (the console's `.expect` files, the accounts' 109
lines, the speaker's, every recording under `tests/mpx5-jobs.d/linux/`
but the twelve new eds files). `mpx4-session`, `mpx4-lobo`,
`mpx4-unix` and the network suites: CI's runs only, as at px53 (their
Linux sides need an engine on the host).

## J. The kernel's cost (P10)

Built in `px13-ubuntu` from trunk `ebbef86` (wolf 0.2.33) and the
branch (0.2.34), the same kernel source but the tour's one line
(`notes/px57/cost.sh`, `size -A`):

| kernel | tier | `.text` 0.2.33 → 0.2.34 | `.rodata` | `.data` | `.bss` |
|---|---|---|---|---|---|
| kmain_console | native | 965,899 → 965,899 | 62,192 → 62,192 | 16,928 | 4,399,224 |
| kmain_console | release | 814,075 → 814,075 | 67,728 → 67,728 | 1,376 | 4,399,224 |
| kmain_session | native | 968,651 → 968,651 | 62,448 → 62,448 | 17,232 | 4,399,224 |
| kmain_session | release | 823,643 → 823,643 | 67,104 → 67,104 | 1,376 | 4,399,224 |

0.2.34 moved no code generation the freestanding kernel reaches (the
ELFs' digests differ by the tour's string alone).

## K. Plants (P9)

Branches never to be merged, cut from `7df19b2` (the code, the suites
and the CI as at the head), one commit each, run by dispatch on one leg
(ruling #92), each prediction by row committed (`7df19b2`) before any
of them ran:

| plant | branch, commit | change | CI |
|---|---|---|---|
| A | `px57-plant-a` `0ecadfc` | `kernel/files`' `fsync` answers 0 for what it cannot synchronise (a pipe), not -EINVAL | `-f tier=pr -f suites=mpx5-jobs -f jobs_boots=eds:serial`: run **39680111521**, mpx5-jobs job 119500291136 **red** at J13 eds and eds-user (`S: fs_sync of a pipe: ok` where the recording says `io (22)`), J4 at both, J3 for eds-user; hostq and hostq-user green; J6 green (`notes/px57/ci-39680111521-plant-a.txt`) |
| B | `px57-plant-b` `7459be6` | `kernel/tree`'s directory size answered 0 | `-f tier=pr -f suites=mpx5-aspen`: run **39680114939**, job 119500350857 **red** at A1, root and `pax` (`[ 125] /usr`, `[ 0] lib` where the container's are 445 and 40); A2 and A3 green (`ci-39680114939-plant-b.txt`) |
| C | `px57-plant-c` `60d3253` | PAX's `stat` (4), which the musl lupin makes and glibc's programs do not, answers -ENOENT for every path | `-f tier=pr -f suites=mpx5-lupin`: run **39680118584**, job 119500324113 **red** at U1 and U2, root and `pax`, every lupin row (`` lupin: `/usr/share/lupin/hello.lu` is not a readable file ``, st=2), **and U3** (`PAX: init /bin/sh ended with status 2`: pelt's `exit` takes the last command's status, lupin's 2 — the prediction's one wrong row) (`ci-39680118584-plant-c.txt`) |

Each plant's own run also measured CI's binaries: edwolf `1bfd0ca2…`,
hostq `9eca259e…`, aspen `b34106b5…`, lupin `08a7766b…` — the bytes
kasumi's `px13-ubuntu` (and the Rust image) built.

## L. CI

- The tiers: the branch changes `kernel/wolf.pin` (FULL in
  `tools/ci-tiers.map`), so the pull request's own run is the all tier
  (every suite, every leg). No run was pushed before the final head (a
  branch push runs nothing; the pull request is opened at the final
  head). `full-matrix` is added at that head once the pull request's own
  run is green; the runs are named in the pull request and the
  hand-back (a commit naming them would move the head).
- Two new jobs (`720819d`): `mpx5-aspen` and `mpx5-lupin`, mpx5-lope's
  shape without the token (aspen and wolf-interp are public); lupin's
  job installs `user/lupin.pin`'s channel and the musl target with the
  runner's `rustup` before the build (`tools/mklupin` refuses another
  channel and installs nothing). Both in the `tier` job's needs;
  mpx5-jobs keeps edwolf's sums. `tools/ci-tiers.map` (`0dd32a4`):
  edwolf, hostq and their tools mpx5-jobs'; aspen's pin, tool and keys
  mpx5-aspen's; lupin's pin, tool, programs and keys mpx5-lupin's; `as`
  reaches both new suites. `tests/ci-plan` (`ea4cf0f`): the cases for
  each.
- The plants' runs: §K.

## M. The playground (item 4)

The orchestrator's `~/lanes/orch-paxplay/build.sh` and `assemble.sh`
on kasumi, extended by `notes/px57/playground.sh` the way px54 and
px56 extended them (the pre-edit copies kept at kasumi
`~/lanes/px57/ev/orch-build.sh.before`, `755f098e…`, and
`orch-assemble.sh.before`, `41aead58…`; after: `e8c6ca5f…` and the
motd-fixed assemble.sh): its pax clone moved to this branch's
`120e36b` (the code as at the head); build.sh gains `tools/mkaspen`
and, after its container, `tools/mklupin` in the Rust image (made from
`notes/px57/rust/Containerfile` when absent); assemble.sh gains stripped
`/bin/aspen` and `/bin/lupin`, the four programs at `/usr/share/lupin`,
and a motd naming wolf 0.2.34, pelt, boreutils, lope, aspen `103ba46`
and lupin 0.1.55 (static musl). Its first assemble failed on an
apostrophe in the motd (the script is single-quoted; `lope's`), so the
motd has none and `playground.sh` refuses one; the second run
assembled (build rc 0, aspen `b34106b5…`, lupin `08a7766b…`, pelt
`5448cb27…`, lope `f9a2f064…`, su `fbc2035e…`). **`pax-playground.iso`
`242ecec2109485c322df7fb9fa520b6a8ae765f2e31aa5235d7515c159727fdf`**
(79,415,296 bytes; px56's was `c9ce2cda…`, 71,782,400), `pax-smoke.iso`
`0a2187c1…`. Booted once on kasumi (native BIOS, TCG,
`notes/px57/playground-boot.sh`) with `notes/px57/playground.keys`
typed at the console's pelt — the maintainer's sessions: `cd /etc`,
`cd /bin`, **`g -`** (`/etc`), **`aspen /`** (the whole tree, `12
directories, 83 files`), `cd /usr/share/lupin`, **`lupin run hello.lu`**
(`hello, wolf`), `su pax`, `cd /home/pax`, `mkdir Script`, then
**`./Script/greet.sh`** (`hi`, st=0), `aspen -a /home/pax` (lope's
store and pelt's history among the names), a program typed into `cat >
x.lu` and run by `lupin run x.lu` (`written and run on PAX by pax`);
halted (`notes/px57/kasumi-playground-session.txt`). Copied to nomad-1
`~/pax-playground/pax-playground.iso` over px56's, hashed there twice,
the same digest. Seen there and not measured against Linux: PAX's `/`
lists `bin dev etc home tmp usr`, no `proc` (a root with /proc mounted
on Linux lists it; to compare, §N).

## N. Issues, rulings, and what is owed

- **To close at merge**: none. pax#107 asks for a sigwolf-style row of
  each s253 call at the 0.2.35 pin; the kernel's answers are confirmed
  by boot here at the system-call level (§E), the wolf rows wait for
  0.2.35 (a comment on pax#107 with §E's table, it stays open).
- **Would file (none filed)**:
  1. pax: the monotonic clocks advance in 10 ms ticks
     (`clock_gettime` answers `timer.ticks() * NS_PER_TICK`), so
     `os_clock_ns` reads 0 across work shorter than a tick (edwolf's
     `~N:`, 19 and 20 of 20 rounds) where Linux reads nanoseconds;
     yew's latency gates (G8) cannot be measured on PAX until a finer
     clock (the TSC, calibrated against the PIT) answers them.
  2. pax: `/`'s listing on PAX is `bin dev etc home tmp usr` with no
     `proc` (seen in the playground's `aspen /`; Linux lists a mount
     point), not measured against Linux here.
  3. wolf-interp: no static musl release archive; pax builds one from
     the tag (`tools/mklupin`, with `relocation-model=static`, the
     target's default being a static PIE). An `x86_64-unknown-linux-musl`
     archive in lupin's release matrix, built so, would let pax pin
     lupin by digest as it pins wolf (the bytes reproduce across hosts:
     kasumi's Rust image and CI's runner gave one digest).
  4. pax (or pax-dev): lupin on PAX has no std tree, so a program that
     reaches a std module (`List.insert`, std.list's, in host.lu's first
     text) is refused by name; lupin reads `LUPIN_STD`, `--std-root` or a
     `std/` beside its binary.
- **Rulings asked**: **R-px57-1**, the std tree in the base image beside
  lupin: (a) wolf-std at the next STD-PIN under `/usr/share/wolf/std`
  with `LUPIN_STD` set in the console's environment (`/etc/shrc`), (b)
  `/bin/std` beside the binary (no variable), (c) none until pax-dev.
  Recommended (a): an interpreter in base that cannot run `use std.…`
  is half of one, and a variable keeps `/bin` holding programs only.
  Not implemented (no lane change rides on it).
- **Owed to pax-dev** (ruling #110): wolf's checked machine on PAX
  (`wolf conform-run --json --checked`): the `wolf` binary is glibc's
  and dynamic; the dev image's.
- aspen at `476edee` (ap01, the coordinator's word during the lane):
  the next pins lane (§A).

## 4. Evidence index

Shas are this branch's (`px57`). kasumi paths are under `~/lanes/px57/`.

### What was written

- The prediction: `6176df1` (§1 to §3, before any change or
  measurement); the plants' rows `7df19b2`, before any plant ran.
- The pins: `bb98155` (`kernel/wolf.pin`, the tour's line), `4f7f875`
  (`user/su`), `099bcbd` (`user/sigwolf`), `2b3ef1f` (ci.yml's comments).
- The probes: `db18770` (edwolf's toolchain), `5eed9fd`
  (`user/edwolf/edwolf.lu`), `38d4296` (`tools/mkedwolf`), `f157c52`
  (`user/elf/hostq.c`), `2ae1e49` (`tools/mkhostq`).
- aspen: `6f87a88`, `3872b23` (`tools/mkaspen`), `d196374`, `6c401cd`
  (`user/aspen.pin`), `65b4f79` (`user/console/aspen.keys`), `5d1f966`,
  `2ac53b8` (`tests/mpx5-aspen`).
- lupin: `5eaa000`, `03f9a0f` (`tools/mklupin`), `8744fa9`, `3d3d6ac`
  (`user/lupin.pin`), `57f53ec`, `6a09f79`, `ae40b8f`, `182943d`,
  `5249880` (`user/lupin/*.lu`), `68f0fb2` (`user/console/lupin.keys`),
  `9e17fb0` (`tests/mpx5-lupin`).
- The eds image and its recordings: `c3e8bdf` (`tests/mpx5-jobs`: eds,
  J13, the `~` rows), `f1befa0` (`tests/mpx5-jobs.d/linux/eds*`,
  `hostq*`, their metas).
- CI: `720819d` (ci.yml: the two jobs, edwolf's sums), `0dd32a4`
  (`tools/ci-tiers.map`), `ea4cf0f` (`tests/ci-plan`).
- The words: `376a05c` (`docs/SOURCES.md`), `1e6bbff` (CHANGELOG),
  `36b0cab` (README), `12802ca` (`kernel/README.md`), and this note.
- The scripts (`notes/px57/*.sh`, the Rust image's Containerfile, the
  playground's keys): `e32ffb3`, `af26b21`, `10f5c28`, `1c72690`,
  `1d97202`, `2e6d713`, `a156012`, `903a608`, `7c595b6`, `8a3c642`,
  `579a2e9`, `38483cb`, `e677afa`, and the playground's fix after its
  first assemble.
- The plants: `px57-plant-a` `0ecadfc`, `px57-plant-b` `7459be6`,
  `px57-plant-c` `60d3253` (on origin, never to be merged).

### What was measured, and where it is

- **The archives**: the release API twice (§2); `sha256sum` of the
  downloads on kasumi twice (`88a9dd3d…`, `1152abc0…`).
- **The kernel's cost**: `notes/px57/kasumi-first-chain.out` (`cost.sh`).
- **The binaries**: the suites' build logs (`program:` lines), the
  `sums.txt` of each tool, `notes/px57/aspen-twice.sh` and
  `lupin-twice.sh` (two builds each), `pie.sh` (the static PIE), CI's
  plant runs.
- **The first boot at the pins**: `notes/px57/kasumi-first-chain.out`
  (mkw, tour, every suite).
- **Real root's eds recordings**: `tests/mpx5-jobs.d/linux/eds*.tty`,
  `hostq*.tty`, their `.rc` and `vm-*.meta` (kasumi's 7.2.8
  `f4c00d5d…`, vmjob `2a3a7f57…`, the eds archive `c36949e3…`), made
  twice, the same bytes (`notes/px57/kasumi-eds-recordings-twice.out`).
- **PAX's first boot of the eds image**: `notes/px57/kasumi-first-eds.out`.
- **The new suites' first boots and the head's**:
  `notes/px57/kasumi-new-suites.out`.
- **The census**: `notes/px57/census/` (`census.sh`; each run's `.calls`,
  `.fails`, `.out`, `.rc`; the unions).
- **The head on kasumi**: `notes/px57/kasumi-head.out`.
- **The plants**: `notes/px57/ci-39680111521-plant-a.txt`,
  `ci-39680114939-plant-b.txt`, `ci-39680118584-plant-c.txt`.
- **The playground**: `notes/px57/kasumi-playground-1.out` (the build,
  the first assemble's failure), `kasumi-playground-2.out` (the
  assemble), `kasumi-playground-session.txt` (the maintainer's
  sessions).

### Measured, inferred, not verified

**Measured**: everything in §A to §M but what follows.

**Inferred**:
- How PAX serves each of edwolf's and the census's calls (§D, §H): PAX
  has no tracer; the rows are the calls' answers, and PAX's source
  names the handler.
- That `clock_gettime` is a call on PAX for aspen and lupin (Linux
  answers it from the vDSO; PAX gives none).

**Not verified**:
- Real root was one kernel build (kasumi's 7.2.8) and one terminal kind
  (a pseudo-terminal; PAX's console is a serial line).
- UEFI, the release tier and more than one CPU: CI's all tier only (the
  pull request's run); no hasu (KVM) run in this lane.
- wolf's checked machine on PAX (§N: pax-dev's).
- PAX's `/` listing against Linux's (§N).

## 5. Done-when

- Branch `px57` on origin; the pax pull request (number in the
  hand-back), open, unmerged; `full-matrix` added at the final head
  once its own run is green.
- The five sections §1 to §5; the items §A to §N.
- The test checklist:
  - [x] the pins, each its own commit; the archives read twice each way
  - [x] the kernel's sections at 0.2.34: 0 bytes on every kernel and tier
  - [x] the binaries' digests in two builds and in CI
  - [x] the first boot at the pins: every recording held
  - [x] edwolf and hostq: real root's recordings twice, the same bytes;
        PAX byte-identical at its first boot, root and `pax`, but the
        rows named PAX's own
  - [x] aspen `b34106b5…` twice; its session byte-identical to the
        container at the first boot, root and `pax`; its census
  - [x] lupin `08a7766b…` twice (and in CI), ET_EXEC; its session
        byte-identical to the container at the first boot, root and
        `pax`; its census; the machine's answer for the clock, the
        environment and the tree
  - [x] `tests/mpx5-jobs` on kasumi, every image, at the pins and at the head
  - [x] the other suites on kasumi at the pins (§I)
  - [x] `tests/ci-plan`, every case, 200 PASS
  - [x] plants A, B and C red in CI (39680111521, 39680114939,
        39680118584)
  - [x] the playground rebuilt (`242ecec2…`), the maintainer's
        sessions typed on it, on nomad-1, hashed twice
  - [ ] the pull request's own run (the all tier: the pin is FULL) green
        at the final head; `full-matrix` added there; its run held by
        the orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px57 <PR>` exit status: named in the
  hand-back.
- Trees: kasumi `~/lanes/px57/` keeps `out/`, `ev/`, `vm/`, `cache/`,
  `bin/` and the two lupin and aspen builds; the build directories and
  the worktrees removed at the end; the throwaway Rust image
  `localhost/px57-rust` kept for the playground's build.sh (listed for
  the orchestrator: `podman rmi localhost/px57-rust` frees 1.6 GB).
  Plant branches stay on origin, never to be merged.
