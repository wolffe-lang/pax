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
