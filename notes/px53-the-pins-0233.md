# px53 — The pins at 0.2.33 (wolf 0.2.33, boreutils `cc64f68`, pelt `be1a75d`)

Contract: px53's, `sprints/pax/53-the-pins-0233/px53-the-pins-0233.md`
in wolffe-lang/wolf (planning trunk `d2c84fc`, read 2026-10-20), px51's
shape (`pax/51-the-pins-0232/`) with every one of its rules kept, under
`sprints/RULES.md`. Branch `px53` in pax, cut from pax trunk `d733bf4`
(px52). §1 to §3 are committed before the first change to a pin, the
kernel, a tool, a probe or a test, and before the first measurement.

One deliverable: the kernel built from wolf 0.2.33, with boreutils
`cc64f68` (bu28) and pelt `be1a75d` (sh19, tl28), measured on PAX as
px51 measured its pins: the pins, each its own commit; every suite on
kasumi and the recordings held; what the new boreutils asks of PAX (the
ignore-then-send of a fault or host signal to timeout's own group, the
re-raise, the core bit, the group read from `/proc/PID/stat`) in a typed
session held to Linux as root and as `pax`; what 0.2.33 asks of PAX (the
five new calls and `text(0)`) in a wolf probe built with 0.2.33, held to
Linux; plants; the playground image refreshed for the maintainer.

## 1. Forbidden, absolutely

- No kernel's source is read or searched for, Linux's above all, nor any
  libc's, shell's, terminal driver's, container runtime's or init
  system's, nor `su`/`login`/util-linux/procps source, nor any `kill`'s
  or `timeout`'s (GNU coreutils', procps', util-linux's, busybox's, any
  shell's), nor `systemd-coredump`'s (ruling #22; RULES.md §1). Facts
  come from the man pages (`signal(7)`, `sigaction(2)`, `kill(2)`,
  `tgkill(2)`, `sigprocmask(2)`, `wait4(2)`, `core(5)`,
  `getrlimit(2)`, `proc_pid_stat(5)`, `proc_pid_status(5)`,
  `timeout(1)` and `kill(1)` as documentation), POSIX.1-2024, the
  allowed uapi headers, pax's own source, px38's to px52's notes, and
  the org's own repositories read as the maintainer's code and records:
  wolf-lang at `v0.2.33` (its CHANGELOG, spec `11-os.md`'s
  `[os.signal.disp.one]`, `[os.signal.exit]`, `[os.proc.status]`,
  `[os.signal.gaps.note]`, the runtime's stack guard
  `crates/wolf_rt/src/task/stack.rs`, s246's fixtures
  `crates/wolf_driver/tests/fixtures/signal_gaps/`), boreutils
  `cc64f68`'s `notes/bu28-the-retired-refusals.md`, `notes/bu28/ev/`
  (`static-digests.txt`, `straces.log`) and probes, pelt `be1a75d`'s
  `notes/sh19-the-leak-and-the-ci.md`. `wolf/refs/repos/linux` stays
  sparse and is not opened.
- A Linux answer nobody recorded is measured black-box: real root is
  kasumi's own kernel image under QEMU with a static program as pid 1
  (px48's `vmjob` way, `notes/px50/vmjob.c` unchanged, the shell on a
  pseudo-terminal as its session leader); a rootless container only for
  a user's rows.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals, faults and core dumps only to processes a test
  started, inside QEMU or a container, never on a host's process table;
  `ulimit -c 0` (the container's `--ulimit core=0:0`) wherever a core
  would be handed to the host (kasumi's and CI's `core_pattern` pipe
  cores to a program on the host).
- Probe and test binaries static, built in `px13-ubuntu`, never with
  kasumi's CachyOS glibc (AVX-512). No build on nomad-1. kasumi and hasu
  under `bash` (hasu `env bash`), long jobs `setsid` with a pid file,
  ended by that pid only (never by name, pattern or process group); work
  under `~/lanes/px53/`, pruned (kasumi `/home` 32 GB free;
  container-owned files by `podman unshare rm -rf`); never `/tmp`.
  Process, signal and terminal tests also under `taskset -c 0-3`; SigBlk
  and SigIgn read before a signal row is called red. Ports 8080 and 8088
  unused; nothing installed; `~/lanes/bu28/` read only;
  `~/lanes/orch-paxplay/` touched only by its own two scripts, re-run at
  the new pins as the contract says.
- Toolchains from release archives by digest, each read twice: wolf
  0.2.33 (`v0.2.33` at `85dab5d7`, release 417610226), lupin 0.1.54
  (`v0.1.54` at `0e536e8`), the bundled std wolf-std `cceda63`.
- No `rm` outside `~/lanes/px53/` and this worktree; no `git add -A`;
  nothing under `~/.claude`; no merge, no tag; no issue filed or closed
  (listed); no `2>/dev/null` on a checkout; no trailer on a commit or the
  PR. No other lane's run cancelled; pax CI is tiered: a plant by
  dispatch, `-f tier=pr` with its suite and, for mpx5-jobs, its images
  (`-f jobs_boots=…`); the PR opened without the label, `full-matrix`
  added at the final head. "Seen red" cites a run. No assertion deleted
  or weakened, no timeout or retry as a fix. Nothing says "secure"; no
  word implying filming. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-20)

| input | found |
|---|---|
| pax trunk | `d733bf4` (px52, PR #87 merged), the contract's; its push run 39363381486 green; PR runs 39338784206 (`tier full`) and 39318853869 green; no nightly at it yet (the last, 39257426343, at `d6fbcdc`, green); no pax PR open |
| planning repo | `d2c84fc` (crawl 54: s248 and bu28 merged; the px53 contract) |
| wolf 0.2.33 | `v0.2.33` (annotated tag `56110e4f`) → `85dab5d7e597680d6fd7034f1d7ed2acb9a92f97`; release 417610226, the linux x86-64 archive `4f955e8dfe6eaafa441903eeba43c009c4ec2b45a8da09fe13431e8b12340af8`, 80,128,936 bytes (the API, read twice); `crates/wolf_driver/STD-PIN` `cceda63151430eac07df895fdfffddfa4a0b92c1`. CHANGELOG: five new prelude names (`os_signal_ignore_one`, `os_signal_default_one`, `os_exit_signal`, `os_wait_status_core`, `os_wait_poll_core`), `os_signal_text(0)` answers `Unknown signal 0`, a SEGV or BUS another process sends ends the program under the default, a program that names `os_signal_wait_fd` starts with two more descriptors; its downstream line "**lobo, muzzle, pax:** the pin" |
| lupin 0.1.54 | `v0.1.54` → `0e536e8fb4518eaa798ac426901ab81275db5c9f`; release 415937354, linux x86-64 `175df23880cd5bb993b778e5c8fdd7d0d96c176696802e640f6fc87d3dab40dd`, 2,971,403 bytes (read twice); unchanged (0.2.33's pairing) |
| where pax pins wolf | `kernel/wolf.pin` 0.2.32 / lupin 0.1.54 (px51; read by `tools/fetch-wolf`, `tools/fetch-lupin`, every kernel build, `tools/mkplay`, `tests/mkw`, `tests/tour`, the wolf programs of `tools/mknet` and `tools/mkwolf-hello`; `kernel/pax_tour/pax_tour.lu` prints `wolf 0.2.32`); `user/su/wolf-toolchain.toml` 0.2.32 / wolf-std `d37c911` (read by `tools/mksu`). Not pax's: `user/lobo.pin`, `tools/census/inside/pins.sh`, pelt's and boreutils' own `wolf-toolchain.toml`. No pax wolf source declares one of the five new names (`git grep`) |
| boreutils | `cc64f68` (bu28; trunk is it); pins wolf **0.2.33** `4f955e8d…` / lupin 0.1.54 / std `cceda63`; `git diff 18a6490 cc64f68 -- src wolf-toolchain.toml` empty (notes only). bu28's statics (`notes/bu28/ev/static-digests.txt`): pax `d6fbcdc`'s `tools/mkboreutils` at `18a6490`, in `px12-ubuntu`, all 47 read twice: release `kill` `b0e452687aec…` 13,999,664, `timeout` `245f84148aa7…` 14,579,232, `sleep` `4d865fb95224…` 14,310,496, `cat` `930e58ac87bf…`, `cut` `f5735f5b1b6c…`, `tr` `8e9d44316f7f…`, `wc` `f7596ab4efbc…`, `true` `a3bf0296cb96…`; not booted on PAX. `tools/mkboreutils` and `tools/mkpelt` are unchanged from `d6fbcdc` to `d733bf4`; kasumi's `px12-ubuntu` and `px13-ubuntu` are one image (`ad8964505189`) |
| bu28's calls (`notes/bu28/ev/straces.log`, static release and dev `timeout`, `kill`) | the same call NAMES as bu27's traces; new uses: `rt_sigaction(SIGRT_2, SIG_IGN)` (34) and none for SEGV (the stack guard's handler stays and tells a sent one by `si_code` ≤ 0, `crates/wolf_rt/src/task/stack.rs`), `kill(-PGID, SIGSEGV)` / `kill(-PGID, SIGRT_2)` then `kill(-PGID, SIGCONT)`; the end by the command's signal `rt_sigaction(SIG_DFL)`, `rt_sigprocmask(SIG_UNBLOCK, [SEGV])`, `tgkill(pid, pid, SEGV)`; `WCOREDUMP` read from `wait4`'s status; the group read from `/proc/PID/stat` (`bore.stat_group`, field 5); `kill -t 0` `statx` and `write` only (` 0 EXIT     Unknown signal 0`) |
| pelt | `be1a75d` (trunk; tl28's CI on sh19's `110ba56`); `git diff cd05c3b be1a75d -- src wolf-toolchain.toml` empty; pins wolf **0.2.32** / lupin 0.1.54 / std `d37c911` (its own toml: pelt's 0.2.33 pin folds into sh20). sh19: #33's leak (the ordinary path's scratch), #35, #37 (`cd`'s relative join adds a `/` only when the base does not end in one: `cd bin` from `/` is `/bin`, not `//bin`); its static pelt at `cd05c3b` with pax `d6fbcdc`'s `tools/mkpelt`: `7be05ec0478f624dc296d7b5c2a27f2b5b9348563f1ea47ed15b745eb402d0ca`, 15,200,336 bytes; the same 50 calls by name as sh18's |
| what PAX serves today (`kernel/signal`, `kernel/sched`, `kernel/user`, `kernel/procfs`) | `rt_sigaction` for 1–64 (px26; real-time signals one instance pending, named); `kill` of a group (px48); siginfo `SI_USER` with the sender's pid and real id for a `kill`, `SI_TKILL` for `tgkill`, `SI_KERNEL` for the terminal (px26, px45); a handler's mask holds its own signal; `rt_sigprocmask`, `tgkill` (px26); a default that ends a process ends every thread, its wait status the signal's number and **bit 7 never set** ("no core is written"); a default for pid 1 does nothing (`kill(2)`); `prlimit64` answers `RLIMIT_CORE` **unlimited** (every limit but the stack's and the descriptors'; a set is -EPERM); `/proc/<pid>/stat` (px25, px51's `-proc` sessions read fields 5 and 8); `/proc/self/status` SigIgn and SigCgt the process's actions |
| suites that build pelt or boreutils | as px51 (`tools/mkpelt`: mpx3-shell, mpx3-console, mpx3-screen, mpx3-speaker, mpx3-tree, mpx4-session, mpx4-lobo, mpx5-accounts, mpx5-jobs; `tools/mkboreutils`: those but console and screen, and mpx3-boreutils, mpx5-users); `tools/mksu`: mpx3-shell, mpx3-speaker, mpx3-tree, mpx4-lobo, mpx5-accounts. Fixed references a new binary could move: `user/console/*.expect`, `tests/mpx3-speaker.d/linux/`, `tests/mpx5-accounts.d/linux/`, `tests/mpx5-jobs.d/linux/` (real root's recordings: 52 pjobs runs, groups 73 lines and groups-user, made at pelt `2676879` and boreutils `43ee185`) |
| the playground | kasumi `~/lanes/orch-paxplay/`: `build.sh` (pelt, 47 boreutils, `as`, su, play, the zone, `kmain_console` native, in `px13-ubuntu`) and `assemble.sh` (stripped copies, `/etc/motd` naming "pax trunk d6fbcdc, wolf 0.2.32, pelt 2676879, boreutils 43ee185", `pax-playground.iso` and `pax-smoke.iso`); `out/pax-playground.iso` 70,187,008 bytes of 2026-10-19 |
| kasumi | Linux 7.2.8-1-cachyos (the guest's image, `f4c00d5d…` in the recordings' meta), 16 cpus, load 0.1, `/home` 32 GB free, `px13-ubuntu` `ad8964505189` |
| open pax issues | #55, #56, #62, #67, #88, #89, #90, #91 (none this lane's) |

## 3. Prediction (committed before the first change and measurement)

**P1. The pins**, four commits: `user/su/wolf-toolchain.toml` to wolf
0.2.33 (`4f955e8d…`) / wolf-std `cceda63`; `kernel/wolf.pin` to wolf
0.2.33 / lupin 0.1.54 (unchanged), with `pax_tour.lu`'s line;
`user/pelt.pin` to `be1a75d`; `user/boreutils.pin` to `cc64f68`. su
builds unchanged (no name it declares is one of the five). **The kernel
builds on 0.2.33 with no source change, and its `.text` does not move**:
0.2.33 is s246's lane alone (the hosted runtime, the prelude's five
names, the std), and the freestanding kernel links no runtime and calls
none of them, so every kernel (kmain_console and kmain_session, native
and release) has 0.2.32's `.text`, `.rodata`, `.data` and `.bss` sizes
(weak: within 1 KiB, if the five names' lowering moved shared code
generation; px51's four-release step was +10,416 / −37,296).
`tests/mkw`'s step 6 (the checked machine and lupin 0.1.54 refusing the
freestanding kernel) holds its rows as written.

**P2. The rebuilt binaries**, in `px13-ubuntu` on kasumi with the
suites' own tools, each read in two builds and again in CI: pelt
**`7be05ec0…`** (15,200,336 bytes: `cd05c3b`'s `src/`, pelt's own
0.2.32 toolchain, the same `tools/mkpelt`); boreutils at `cc64f68`
**every one of bu28's 47 release digests** (`18a6490`'s `src/`, the same
0.2.33 toolchain and tool, one container image): `kill` `b0e45268…`,
`timeout` `245f8414…`, `sleep` `4d865fb9…`, and the rest; su moves
(0.2.33's runtime) from `ca78e313…`.

**P3. The recordings held.** At the first PAX boot at the new pins, all
52 pjobs runs (26 cases, root and `pax`) byte-identical to the committed
recordings of real root's guest, and the 26 user runs to the container:
sh19's changes are a leak (memory, never a line) and `cd`'s join from a
base that ends in `/`, which no pjobs or groups session types; bu28's
`kill` and `timeout` answer every row those sessions type as bu27's did.
Recorded again on the guest at the new binaries, twice: **the same bytes
as the committed `pjobs-*.tty`**, so nothing there is re-recorded. The
groups session's first 73 lines (the rows px51 recorded) hold as well;
only the rows appended (P4) are new.

**P4. What the new boreutils asks of PAX: the groups session
extended.** `user/console/groups.keys` gains, before `exit`: `timeout -s
SEGV 1 sleep 5` (st=124), `timeout -s RTMIN 1 sleep 5` (124), `timeout
-s 16 1 sleep 5` (a host number, 124), a command dead of SEGV, `timeout
5 sh -c 'exec /bin/kill -s SEGV $$'` (timeout reads the end, re-raises
SEGV on itself and dies of it: st=139), the same with RTMIN (st=162),
and `kill -L`'s row 0 (`/bin/kill -L 0 | tr -s ' '`: ` 0 EXIT Unknown
signal 0`). **Byte-identical on PAX to real root's guest as root and as
`pax`, at the first boot, with no kernel change**, and to the container's
but for one line named as the host's: **on PAX and on the guest no core
is written** (the guest's processes inherit pid 1's `RLIMIT_CORE`, soft
0, hard unlimited, with `core_pattern` `core`: measured before the
recording), so timeout prints no "dumped core" line; in the container on
kasumi (and CI's runner) the host's `core_pattern` pipes cores to a
program, which `core(5)` and s246 (measured) say dumps whatever
`RLIMIT_CORE` says, so there timeout's command carries the core bit and
`timeout: the monitored command dumped core` is printed at the SEGV rows:
that line is left out of the container's comparisons by name where the
host's pattern starts with `|` (as px49 left out the host's TIOCSTI
rows). The container runs with `--ulimit core=0:0`, so no core is stored
on the host (bu28's measured rule). Weak: pelt's own words for a
foreground job dead of a signal (the same pelt on both sides).

**P5. What 0.2.33 asks of PAX: a wolf probe.** `user/sigwolf/sigwolf.lu`,
built with 0.2.33 by digest from its own `wolf-toolchain.toml` (as su
is; so the kernel's pin and the probe's are separate, and a kernel at an
older pin can be held to the same probe), static, booted in a new
mpx5-jobs image `sigs` (kmain_console, `/bin/sigwolf` then `/bin/as 1000
1000 /bin/sigwolf`, nothing typed), held to real root's guest and the
container. Its rows, the same as root and as a user: `text(0)` `Unknown
signal 0`; a group leader (a child: the probe as root is PAX's pid 1,
whose group 1 the shape refuses) that ignores `SEGMENT_FAULT`, then host
34, and sends each to its own group: the job ends by 11, then by 34, the
leader lives; children through `os_exit_signal` (SEGV: signal 11; host
34: signal 34; `CHILD`: exit 145; a listened `TERMINATE`: signal 15); a
SEGV a child sends itself under the default (signal 11: the guard
passes a sent one on, which needs PAX's `SI_USER`) and under the ignore
(lives, exit 0); host 34 ignored then sent (lives), ignored then
defaulted then sent (signal 34); the fault ignore crossing `exec` (the
child's SigIgn holds SEGV's bit, `0000000000000400`; weak: the exact
word); a task's stack
overflow under the ignore (the runtime's report, exit 134); and the `_core`
siblings (`wait_status_core`, `wait_poll_core`) answering `-11` (no core)
on PAX and the guest, `-267` in the container on a piping host (left out
there by name, as P4's line). **Identical at the first boot, no kernel
change.**

**P6. The new calls.** No new system-call number (bu28's names are
bu27's); so **no -ENOSYS but 273 and 334, and no `refused:` line**, in
any boot. Served as Linux serves them, by what PAX already has:
`rt_sigaction(34, SIG_IGN)` and `SIG_DFL`; `kill(-PGID, SEGV/34/16)` to
a group the sender is in; a `kill`'s siginfo `SI_USER`, so wolf's guard
passes a sent SEGV to the program's choice; the guard's raise held
blocked in its handler and delivered at `rt_sigreturn`; the re-raise
(`rt_sigaction(SIG_DFL)`, `rt_sigprocmask(SIG_UNBLOCK)`, `tgkill(self)`)
ending every thread; the core bit, which PAX never sets and Linux at the
boot's limit sets nowhere either; the group from `/proc/PID/stat`'s
field 5. **No kernel change.** Named, not changed: PAX's `prlimit64`
answers `RLIMIT_CORE` unlimited while it writes no core (Linux's boot
default is soft 0, P4), to file; nothing in these programs reads it.

**P7. Existing suites.** Every suite green as root and as a user at the
new pins on kasumi, native BIOS under `taskset -c 0-3` (mpx5-jobs every
image, mpx3-shell, mpx3-tree, mpx5-accounts, mpx3-boreutils,
mpx5-users, mpx3-speaker, mpx3-console, mpx3-screen, mpx3-threads,
`mkw`, `tour`, `tests/ci-plan`), and in CI's full tier. No fixed
reference moves (`user/console/*.expect`, the speaker's, the accounts',
the session suite's): nothing is re-recorded but groups (P4) and the new
sigs recordings (P5).

**P8. Plants**, each a branch never merged, one commit, by dispatch
`-f tier=pr -f suites=mpx5-jobs -f jobs_boots=…`: **A**, the kernel at
the old pin (`kernel/wolf.pin` and `pax_tour.lu`'s line back at 0.2.32,
everything else the branch's) against the new sessions (groups, sigs,
pjobs, pjobs-user): **green at every new row** — no kernel change was
needed, so 0.2.32's build of the same kernel source answers the new
calls as 0.2.33's does; it is no gate, and it is reported as measured.
**B**, a kernel break: an ignored real-time signal (32 and up) taken as
its default: red at groups' `-s RTMIN` row (timeout ended by its own
group send, 162, not 124) as root and as `pax`, at the probe's host-34
rows (the leader ends; the ignored self-send ends the child), and green
at the pjobs sessions (weak: nothing else on PAX ignores a real-time
signal).

**P9. Cost.** The kernel's `.text` at 0.2.33 against 0.2.32: 0 bytes,
every kernel (P1).

**P10. The playground** rebuilt by the orchestrator's two scripts at the
branch's head and the new pins (its motd naming them), `lope` not in
it: a new `pax-playground.iso` digest, copied to nomad-1
`~/pax-playground/` over the 0.2.32 one.
