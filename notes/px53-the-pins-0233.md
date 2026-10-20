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

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | four pin commits; su builds unchanged; the kernel builds on 0.2.33 with no source change and its sections do not move; `tests/mkw` step 6 holds | `user/su/wolf-toolchain.toml` `75f0fa4` (and ci.yml's comment `79f5f1e`), `kernel/wolf.pin` `5fe44ad` (with `pax_tour.lu`'s line), `user/pelt.pin` `7320369`, `user/boreutils.pin` `ab1f494`; su builds (`388d2434…`, 14,025,128 bytes); every kernel builds with no source change; **not one section moved**: kmain_console native `.text` 943,467 → 943,467, release 807,323 → 807,323; kmain_session native 946,219 → 946,219, release 817,355 → 817,355; `.rodata`, `.data`, `.bss` the same on all four (§J); `tests/mkw` PASS, step 6's four rows as written (`notes/px53/kasumi-mkw-tour.out`), `tests/tour` PASS | right |
| P2 | pelt `7be05ec0…`; every boreutils digest bu28's; su moves; each in two builds and in CI | pelt **`7be05ec0…`** (15,200,336) and `kill` **`b0e45268…`**, `timeout` **`245f8414…`**, `sleep` **`4d865fb9…`**, `cat`, `cut`, `tr`, `wc`, `true` each **bu28's digest**, in both mpx5-jobs builds on kasumi (`first`, `head1`) and in CI's plant runs (39387318671, 39387322394); the playground's build of all 47 utilities equal to bu28's 47 release digests (`diff` empty); su `ca78e313…` → `388d2434…` | right |
| P3 | the 52 pjobs runs byte-identical at the first boot; re-recorded twice, the committed bytes; groups' first 73 lines hold | **at the first PAX boot at the new pins** (the build from `e2906fb`, the pins alone, booted by that tree's own suite): all 52 pjobs runs and both groups runs byte-identical to the committed recordings, and every user run to the container, J3 (`notes/px53/kasumi-first-mpx5-jobs.out`: mpx5-jobs PASS, 207 PASS lines, no FAIL); real root's guest at the new binaries, twice: 112 of 112 files the same bytes, and **every pjobs `.tty` and `.rc` the committed bytes** (106 of 106; `notes/px53/kasumi-recordings-twice.out`), so nothing of px51's was re-recorded; the groups recording's first 72 lines (to px51's `exit`) the same bytes | right |
| P4 | groups with bu28's rows byte-identical to the guest as root and `pax`, at the first boot, no kernel change; no core line on PAX or the guest (pid 1's `RLIMIT_CORE` soft 0, `core`); the container's core line the host's, left out by name; `--ulimit core=0:0` stores nothing | the guest: `RLIMIT_CORE` **soft 0, hard unlimited**, `core_pattern` **`core`**, as root and as 1000:1000 (`notes/px53/linux-limits.txt`), measured before the recording; groups (91 lines, root and `pax`) **byte-identical to real root's guest at PAX's first boot of the image** (`notes/px53/kasumi-first-new.out`), st=124 for `-s SEGV`, `-s RTMIN`, `-s 16` and the group row, `pelt: ended by signal 11 (SEGV)` and st=139, `pelt: ended by signal 34` and st=162, ` 0 EXIT Unknown signal 0`, no core line; the container: `timeout: the monitored command dumped core` at exactly the two SEGV rows (kasumi's pattern pipes to `systemd-coredump`), left out by name, the rest identical (J0, J3); 18 container ends by SEGV this lane, each listed by `coredumpctl` with COREFILE `none`, the host store 196 files before and after (`notes/px53/kasumi-corestore.txt`). pelt's words for the job: `pelt: ended by signal N (NAME)` (the weak point: the same pelt on both sides) | right |
| P5 | sigwolf built by its own 0.2.33 pin; its rows the same as root and a user, identical on PAX, the guest and the container (the `C:` rows left out there on a piping host), at the first boot | `sigwolf` **`fa9f7de6…`** (14,529,304 bytes), compiled at the first try under `--deny-warnings`, the same digest in CI; every predicted row on the guest, root and 1000:1000 (24 lines each), and on PAX **byte-identical at its first boot of the image**; the container the same but its two SEGV `C:` rows (`signal 11 core`), left out by name; SigIgn `0000000000000400` exactly | right |
| P6 | no new call number; no -ENOSYS but 273 and 334, no `refused:` line; every use served as Linux; no kernel change; `RLIMIT_CORE` named | so, in every boot of every image (J6, kasumi and CI); the calls and how each is served: §F; no kernel change; PAX has no `/proc/self/limits` and no `/proc/sys/kernel/core_pattern` either (ENOENT, `notes/px53/linux-limits.txt`): named with `prlimit64`'s answer, to file | right |
| P7 | every suite green as root and a user on kasumi; no fixed reference moves | kasumi, native BIOS, `taskset -c 0-3`, builds in `px13-ubuntu`: mpx5-jobs (every image, 212 PASS, no FAIL), mpx3-shell, mpx3-tree, mpx5-accounts, mpx3-boreutils, mpx5-users, mpx3-speaker, mpx3-console, mpx3-screen, mpx3-threads, `mkw`, `tour`: **every one PASS, no FAIL line**; `tests/ci-plan` 153 PASS (two new cases); no fixed reference moved (`shell-sigs.expect` still `dd691f0e…`, the accounts' 109 lines, the speaker's); CI's `tier full`: the pull request (§H) | right on kasumi |
| P8 | plant A (the kernel at 0.2.32) green at every new row; plant B (an ignored real-time signal taken as its default) red at groups' `-s RTMIN` row and sigwolf's host-34 rows, root and `pax`, pjobs green | A: run **39387318671** green (mpx5-jobs job 118510340503, `groups sigs pjobs pjobs-user` on native BIOS: every J PASS, the kernel built by 0.2.32, sigwolf by 0.2.33); B: run **39387322394** red (job 118510287557): J10 at both RTMIN rows (`pelt: ended by signal 34`, st=162, not 124) as root and `pax` and J3 for `pax`, J11 at `G: the leader signal 34` and `E: ignored-rt: signal 34` as root and `pax`, J3 and J4 with them; the 52 pjobs runs green (§I) | right |
| P9 | 0 bytes of `.text` | 0 bytes on every kernel and tier (§J) | right |
| P10 | the playground rebuilt at the new pins, a new digest, copied to nomad-1 | the orchestrator's `build.sh` and `assemble.sh` at the branch's `eabe780` (the code as at the head) with the motd's line moved, both rc 0; `pax-playground.iso` **`2336718e41b7b06aed22e4cc186c6839e28d1574a425ad56a51c2cc98b0c6001`** (70,213,632 bytes; was `70875a375c0e1356cb6e80f8e1126d814b044848159f549d4277b87e51feaaf6`), smoke-booted with the orchestrator's own keys (the same session as the 0.2.32 image's), copied to nomad-1 `~/pax-playground/pax-playground.iso` and hashed there twice; `lope` not in it (§K) | right |

## A. The pins (item 1)

Four commits, each its own: `75f0fa4` (`user/su/wolf-toolchain.toml`:
wolf 0.2.33 `4f955e8d…`, wolf-std `cceda63`; ci.yml's comment `79f5f1e`),
`5fe44ad` (`kernel/wolf.pin`: wolf 0.2.33 `85dab5d7`, lupin 0.1.54 as
it was; `pax_tour.lu`'s `wolf 0.2.33` line, which `tests/tour` holds to
the pin), `7320369` (`user/pelt.pin`: `be1a75d`), `ab1f494`
(`user/boreutils.pin`: `cc64f68`). The archives read twice from the
release API and twice by `sha256sum` of the download on kasumi
(`4f955e8d…` 80,128,936 bytes; lupin `175df238…`). No pax wolf source
declares one of the five new names, so nothing meets W0304. **The
kernel builds unchanged** at 0.2.33: no file under `kernel/` but the
pin and the tour's line moved, and every kernel of every suite built
(§G); its sections: §J.

## B. The binaries (item 1)

| program | built by | digest | as predicted |
|---|---|---|---|
| pelt (`be1a75d`, its own 0.2.32) | `tools/mkpelt` | `7be05ec0478f624dc296d7b5c2a27f2b5b9348563f1ea47ed15b745eb402d0ca`, 15,200,336 | sh19's, in every build (mpx5-jobs twice, mpx3-shell, mpx3-tree, mpx5-accounts, the playground) |
| boreutils (`cc64f68`, its own 0.2.33) | `tools/mkboreutils` | all 47 release binaries **bu28's** (`notes/bu28/ev/static-digests.txt`, `diff` empty over the playground's 47); `kill` `b0e452687aec…` 13,999,664, `timeout` `245f84148aa7…` 14,579,232, `sleep` `4d865fb95224…` | yes; the same in CI's plant runs |
| su (0.2.33 / `cceda63`) | `tools/mksu` | `388d24348578bb6b32bdb54488d7205b4c8889c65ac4efb656f04103b4f95899`, 14,025,128 (from px51's `ca78e313…`, 13,972,544) | moved, as predicted |
| sigwolf (0.2.33 / `cceda63`, its own pin) | `tools/mksigwolf` | `fa9f7de6a5e7358605484fe46bb8f33c1a55b6f459a683114d6d205745151fc8`, 14,529,304 | new; the same digest in `px13-ubuntu` and on CI's runner |

`px13-ubuntu` and `px12-ubuntu` (bu28's) are one image on kasumi
(`ad8964505189`), and `tools/mkboreutils` is the file bu28 used, so the
47 were bound to agree; they do.

## C. The recordings held (item 2)

The first build was the pins alone (`e2906fb`'s tree), booted by that
tree's own `tests/mpx5-jobs` (native BIOS, `taskset -c 0-3`) against the
recordings px51 committed: **mpx5-jobs PASS, every image** — the 52
pjobs runs (J9) and groups and groups-user (J10, 73 lines) byte-identical
to real root's guest, the 27 user runs to the container (J3), the probe,
the shells, gaps and fds as before, J6 on every boot
(`notes/px53/kasumi-first-mpx5-jobs.out`). Then real root's guest at
the new binaries (kasumi's 7.2.8 `f4c00d5d…`, `notes/px50/vmjob.c`
unchanged, `591414317f1b…`; the head build's archives), twice: **112
files of 112 the same bytes across the two**, and the 52 pjobs `.tty`
and every `.rc` **the committed bytes** (`notes/px53/kasumi-recordings-twice.out`).
sh19's leak is memory, its `cd` join is from a base that ends in `/`,
which no session types from `/`; bu28's `kill` and `timeout` answer
every old row as bu27's did. Nothing of px51's was re-recorded; the
groups recordings were replaced only because their keys grew (§D), and
their first 72 lines are px51's bytes.

## D. What the new boreutils asks of PAX: the groups session (item 3)

`user/console/groups.keys` gains, before `exit`: `timeout -s SEGV 1
sleep 5`, `timeout -s RTMIN 1 sleep 5`, `timeout -s 16 1 sleep 5` (a
host number), `timeout -s RTMIN 1 sh -c 'sh -c "sleep 2; echo
survived" & wait'` and `sleep 2.5; echo checked` (the group, a host
signal: nothing survives), `timeout 5 sh -c 'exec /bin/kill -s SEGV
$$'` and the same with RTMIN (a command dead of the signal: timeout
reads its end and dies of it again), and `/bin/kill -L 0 | tr -s ' '`.
91 lines. On real root's guest, as root and as 1000:1000: st=124 four
times, `pelt: ended by signal 11 (SEGV)` and st=139, `pelt: ended by
signal 34` and st=162, ` 0 EXIT Unknown signal 0`, and **no `dumped
core` line**: the guest's processes run under pid 1's `RLIMIT_CORE`,
soft 0, hard unlimited, with `core_pattern` `core`, measured before any
core row was recorded (`notes/px53/linux-limits.txt`). **On PAX at its
first boot of the image, byte-identical to the guest, as root and as
`pax`** (`notes/px53/kasumi-first-new.out`), with no kernel change.

In the container (rootless podman on kasumi, CI's Docker) the same 91
lines but one more at each SEGV row: `timeout: the monitored command
dumped core`. The host's `core_pattern` pipes cores to
`systemd-coredump`, and `core(5)` says `RLIMIT_CORE` "will be ignored if
the system is configured to pipe core dumps to a program": the
command's end carries the core bit there whatever the container's limit.
That line is the host's: `tests/mpx5-jobs` leaves it out of the
container's comparisons where `/proc/sys/kernel/core_pattern` starts
with `|`, and says so in the verdict; J4 requires it absent on PAX.
`tools/linux-tree` now runs its container with `--ulimit core=0:0`
(an engine's default is unlimited), and kasumi's `systemd-coredump`
lists each of this lane's 18 container ends by SEGV with COREFILE
`none`; the host store held 196 files before and after
(`notes/px53/kasumi-corestore.txt`).

## E. What 0.2.33 asks of PAX: sigwolf (item 4)

`user/sigwolf/sigwolf.lu`, built by its own pin
(`user/sigwolf/wolf-toolchain.toml`: wolf 0.2.33 by digest, wolf-std
`cceda63`; `tools/mksigwolf`, mksu's shape), so a kernel at another pin
is held to the same probe (plant A). In mpx5-jobs' new `sigs` image
(kmain_console, nothing typed): `/bin/sigwolf`, then `/bin/as 1000 1000
/bin/sigwolf`. Its 24 lines, on the guest, on PAX at its first boot and
at every boot since, as root and as a user:

```
T: text(0): Unknown signal 0                      (#787)
T: text(host 34): Real-time signal 0
T: text(SEGMENT_FAULT): Segmentation fault
G: the leader leads its group: true               (#783: a child leads)
G: SEGMENT_FAULT to its own group, ignored by the leader: the job signal 11; the leader lives
G: host 34 to its own group, ignored by the leader: the job signal 34; the leader lives
G: SEGMENT_FAULT and host 34 back to the default
G: the leader exit 0
E: exit-segv: signal 11                           (#784: os_exit_signal)
E: exit-rt: signal 34
E: exit-child: exit 145
E: exit-term-listened: signal 15
E: sent-segv: signal 11                           (a SENT SEGV under the default)
E: ignored-sent-segv: exit 0
E: ignored-rt: exit 0
E: defaulted-rt: signal 34
C: exit-segv, wait_status_core: signal 11         (#785: no core written)
C: sent-segv, wait_poll_core: signal 11
C: exit-rt, wait_status_core: signal 34
X: a child started under the fault ignore: SigIgn: 0000000000000400
X: the child exit 0
wolf-rt: stack overflow in task 'child.task0.entry'
F: overflow-ignored: exit 134                     (a REAL fault stays the runtime's)
```

(and the first line, `sigwolf: … as root` or `as a user`). The group
rows are a child's: the probe as root is PAX's pid 1, and group 1 is no
group the sending calls take, so a child leads one. The container's
are the same but `C: exit-segv … signal 11 core` and `C: sent-segv …
signal 11 core` (the host's pipe, §D), left out there by name.

## F. The calls, and how each is served (item 3 and 4)

No new system-call number (bu28's traces name bu27's calls); **every
boot of every image printed only `set_robust_list` (273) and `rseq`
(334) -ENOSYS and no `refused:` line** (J6, kasumi and CI). The rows are
the calls' answers:

| call | who asks | on PAX |
|---|---|---|
| `rt_sigaction(34, SIG_IGN)`, `rt_sigaction(N, SIG_DFL)` | `timeout -s RTMIN`, `-s 16`; `os_signal_ignore_one(-34)`, `os_signal_default_one` | served since px26 (signals 1–64 have actions; a real-time one pending once, named); groups' RTMIN and 16 rows, sigwolf's `ignored-rt`, `defaulted-rt`, the leader's host-34 row; plant B breaks it (§I) |
| no call for SEGV's ignore (the guard's handler stays); `kill(-PGID, SEGV)` | `timeout -s SEGV`; `os_signal_send_group` | the group send since px48; a `kill`'s siginfo `SI_USER` with the sender's pid (px26, px45), so wolf's guard (`si_code` ≤ 0: sent) leaves the ignoring leader alone and passes a job's to its default |
| the guard's `sigaction(SIG_DFL)` and `raise` inside its handler | a 0.2.33 program sent SEGV under the default (`sent-segv`) | the raised SEGV is held blocked in the handler (its own signal in the handler's mask) and taken at `rt_sigreturn`, ending the process: `signal 11`, as on Linux |
| `rt_sigaction(SIG_DFL)`, `rt_sigprocmask(SIG_UNBLOCK)`, `tgkill(self, self, N)` | timeout's end by its command's signal; `os_exit_signal` | served since px26; a default that ends a process ends every thread of it, status N: st=139, 162; `exit-segv`, `exit-rt`; `CHILD`'s default does nothing, so the call exits 145 |
| `wait4`'s core bit (`WCOREDUMP`) | timeout's `dumped core` line; `os_wait_status_core`, `os_wait_poll_core` | never set: PAX writes no core, and Linux at its boot's `RLIMIT_CORE` of 0 writes none either (§D); the C rows |
| the group read, `/proc/<pid>/stat` field 5 | timeout's single send (bu28's `stat_group`) | served since px25 (px51's `-proc` sessions read fields 5 and 8); inferred, not traced (PAX has no tracer) |
| `os_signal_listen`'s hub (pipes, a thread) | `exit-term-listened` | served (px24, px26) |
| a task's guard page, SEGV with the fault's address | `overflow-ignored` | served (px26): the runtime's report and exit 134 |
| `strsignal(0)` | `kill -L 0`, `text(0)` | no call (the C library's words) |

**No kernel change.** Named, not changed, to file: `prlimit64` answers
`RLIMIT_CORE` unlimited (as every limit but the stack's and the
descriptors') while PAX writes no core and sets no core bit; Linux's
boot answers soft 0 there (§D), under which it too writes none. PAX has
no `/proc/self/limits` and no `/proc/sys/kernel/core_pattern`
(-ENOENT where Linux has both). Nothing in these programs reads them.

## G. Existing suites on kasumi (item 2)

Native, BIOS, TCG, every boot under `taskset -c 0-3`, every build in
`px13-ubuntu` (cpus 4-15), at `319f2ee` (the code as at the head; the
head adds notes and words): `mpx5-jobs` (every image: the probe over
COM1 and PS/2, the shells, gaps, fds, pjobs, pjobs-user, groups, sigs;
212 PASS), `mpx3-shell`, `mpx3-tree`, `mpx5-accounts`,
`mpx3-boreutils`, `mpx5-users`, `mpx3-speaker`, `mpx3-console`,
`mpx3-screen`, `mpx3-threads`, `mkw`, `tour`: **every one PASS, no FAIL
line** (`notes/px53/kasumi-*.out`). The user runs as root's and as
`pax`'s in each; the fixed references stood (S6's five `.expect`, the
accounts' recording, the speaker's). `mpx4-session`, `mpx4-lobo`,
`mpx4-unix` and the network suites: CI's runs only, as at px51 (their
Linux sides need an engine on the host). `tests/ci-plan`: 153 PASS
(151 and two new P2 cases for the probe and its recordings).

## H. CI

- The tiers: the branch changes `kernel/wolf.pin` (FULL in
  `tools/ci-tiers.map`), so the pull request's own run is the full tier
  (every suite, every leg); no run was pushed before the final head (a
  branch push runs nothing; the pull request is opened at the final
  head). `full-matrix` is added at that head after the pull request's
  own run is green; the runs are named in the pull request and the
  hand-back (a commit naming them would move the head).
- The plants' runs: §I.

## I. Plants (item 5)

Each a branch never to be merged, cut from `64e6543` (the code and the
tests as at the head), one commit, run by dispatch on one leg (ruling
#92): `gh workflow run ci -r <branch> -f tier=pr -f suites=mpx5-jobs
-f jobs_boots='groups:serial sigs:serial pjobs:serial pjobs-user:serial'`.

| plant | branch, commit | change | CI |
|---|---|---|---|
| A | `px53-plant-a` `5249792` | the kernel at the old pin: `kernel/wolf.pin` and the tour's line as `d733bf4`'s (wolf 0.2.32); sigwolf still by its own 0.2.33, boreutils and pelt by theirs | run **39387318671**, mpx5-jobs job 118510340503: **green**, every J of the four images (groups 91 lines, sigs 24, the 52 pjobs runs; the container's too), `fetch-wolf: wolf 0.2.32` for the kernel and `mksigwolf: wolf 0.2.33` (`notes/px53/ci-39387318671-plant-a.txt`). As predicted: no kernel change was needed, so 0.2.32's build of the same source answers every new row as 0.2.33's does; this plant is no gate and is not one |
| B | `px53-plant-b` `7b55d7e` | a kernel break: an ignored real-time signal (32 and up) taken as its default (`kernel/signal`'s `act` and `kernel/sched`'s `inert`) | run **39387322394**, mpx5-jobs job 118510287557: **red** at J10 groups and groups-user, the two RTMIN rows (`pelt: ended by signal 34`, st=162 where Linux's is 124: timeout ended by its own group send), J3 for `pax`; J11 sigs and sigs-user at `G: the leader signal 34` (the leader died of the host-34 send it ignores; the rows after it gone) and `E: ignored-rt: signal 34`, J3 and J4 with them; the 52 pjobs runs green, J6 green on every boot (`notes/px53/ci-39387322394-plant-b.txt`) |

## J. The kernel's cost (P9)

Built in `px13-ubuntu` from trunk `d733bf4` (wolf 0.2.32) and the
branch (0.2.33), the same kernel source but `pax_tour.lu`'s one line
(`notes/px53/kasumi-kernel-cost.txt`, `size -A`):

| kernel | tier | `.text` 0.2.32 → 0.2.33 | `.rodata` | `.data` | `.bss` |
|---|---|---|---|---|---|
| kmain_console | native | 943,467 → 943,467 | 61,840 → 61,840 | 16,552 | 4,399,224 |
| kmain_console | release | 807,323 → 807,323 | 67,040 → 67,040 | 1,376 | 4,399,224 |
| kmain_session | native | 946,219 → 946,219 | 62,104 → 62,104 | 16,856 | 4,399,224 |
| kmain_session | release | 817,355 → 817,355 | 66,432 → 66,432 | 1,376 | 4,399,224 |

0.2.33 moved no code generation the freestanding kernel reaches.

## K. The playground (item 6)

The orchestrator's `~/lanes/orch-paxplay/build.sh` and `assemble.sh`
on kasumi, re-run at the new pins: its pax clone moved to this branch's
`eabe780`, and `assemble.sh`'s one motd line to `PAX playground: pax
px53 eabe780, wolf 0.2.33, pelt be1a75d, boreutils cc64f68.` (the steps:
`notes/px53/playground.sh`; nothing else of the scripts changed).
Both rc 0; pelt `7be05ec0…`, the 47 boreutils bu28's, su `388d2434…`,
kmain_console native. **`pax-playground.iso`
`2336718e41b7b06aed22e4cc186c6839e28d1574a425ad56a51c2cc98b0c6001`**
(70,213,632 bytes), `pax-smoke.iso` `6be18c4f…`; the 0.2.32 one was
`70875a375c0e1356cb6e80f8e1126d814b044848159f549d4277b87e51feaaf6`
(70,187,008). Booted once with the orchestrator's own keys of
2026-10-19 (pelt as pid 1, a job stopped and continued, `kill %1 %2`,
`su pax`, `play`): the same session as the 0.2.32 image's, halted.
Copied to nomad-1 `~/pax-playground/pax-playground.iso` over the old
one, hashed there twice (`notes/px53/kasumi-playground.txt`). `lope` is
not in it (px54's).

## 4. Evidence index

Shas are this branch's (`px53`). kasumi paths are under `~/lanes/px53/`.

### What was written

- The prediction: `d7656ce` (§1 to §3, before any change or measurement).
- The pins: `75f0fa4` (`user/su`), `79f5f1e` (ci.yml's comment),
  `5fe44ad` (`kernel/wolf.pin`, `pax_tour.lu`'s line), `7320369`
  (`user/pelt.pin`), `ab1f494` (`user/boreutils.pin`).
- The probe: `e409b2b` (its toolchain), `546d9aa`
  (`user/sigwolf/sigwolf.lu`), `46d9a8e` (`tools/mksigwolf`), `338980b`
  and `99932e2` (su named in words, not as paths the planner follows).
- The sessions and the suite: `543eb1f` (`tools/linux-tree`: the
  container's `RLIMIT_CORE` 0), `83d8972` (`groups.keys`), `d86c385`
  (`tests/mpx5-jobs`: sigs, J11, the host's core rows), `dfe3ad7`
  (groups' recordings), `aaef033` (sigs' recordings), `a1b3c8a`
  (ci.yml: sigwolf's sums), `0c5c037` (`tools/ci-tiers.map`), `8106bff`
  (`tests/ci-plan`).
- The words: `f62d3ea` (`kernel/README.md`), `057759f`
  (`docs/SOURCES.md`), `0017bd7` (README), `eabe780` (CHANGELOG), and
  `kernel/README.md`'s cost clause after this note.
- The scripts: `e2906fb`, `a1fe28d`, `4350bf4`, `82e5982`, `64e6543`,
  `c1d28be`, `319f2ee`, `941f1d7`, `57cdb8d` (`notes/px53/*.sh`).

### What was measured, and where it is

- **The archives**: wolf 0.2.33 `4f955e8d…` and lupin 0.1.54
  `175df238…` from the release API twice and by `sha256sum` of the
  download on kasumi twice (§2, §A).
- **The binaries**: `notes/px53/kasumi-first-mpx5-jobs.build.out`,
  `kasumi-mpx5-jobs.build.out`, each suite's `kasumi-*.out`,
  `kasumi-playground.txt`; CI's in the plants' extracts.
- **The first boot at the pins**: `notes/px53/kasumi-first-mpx5-jobs.out`.
- **The core limit and pattern**: `notes/px53/linux-limits.txt` (the
  guest as root and 1000:1000; PAX).
- **Real root's recordings** (kasumi's 7.2.8 `f4c00d5d…` under QEMU
  11.1.1, `notes/px50/vmjob.c` unchanged as pid 1, `591414317f1b…`; the
  head build's pjobs archive `d1e506c8…` and sigs archive `f392c90c…`):
  `tests/mpx5-jobs.d/linux/groups*.tty`, `sigs*.tty` and their `.rc`
  and `vm-*.meta`; made twice (`vm/rec1`, `vm/rec2`), all 112 the same
  bytes, the pjobs ones the committed bytes
  (`notes/px53/kasumi-recordings-twice.out`).
- **PAX's first boot of the new images**: `notes/px53/kasumi-first-new.out`
  (`notes/px53/pax-first-new.sh`, `first-compare.sh`).
- **The container's new rows and the host's core store**:
  `notes/px53/linux-container-new-rows.txt`, `kasumi-corestore.txt`.
- **PAX at the head**: `notes/px53/kasumi-mpx5-jobs.out` and every
  `kasumi-*.out`; `kasumi-ci-plan.out`.
- **The kernel's cost**: `notes/px53/kasumi-kernel-cost.txt`.
- **The plants**: `notes/px53/ci-39387318671-plant-a.txt`,
  `ci-39387322394-plant-b.txt`.
- **The playground**: `notes/px53/kasumi-playground.txt`.

### Measured, inferred, not verified

**Measured**: everything in §A to §K but what follows.

**Inferred**:
- That timeout on PAX sends its command the signal once, by the group
  send (bu28's `stat_group` read of `/proc/<pid>/stat`): PAX has no
  tracer; the field it reads is served and right (px51's `-proc`
  sessions), and no row here could tell one send from two (a standard
  signal is pending once, on PAX and on Linux).
- That a guest or PAX with a core limit above 0 would part: PAX has no
  way to raise it (`prlimit64` refuses every set, -EPERM) and writes no
  core; the guest was measured at its boot's limit only.

**Not verified**:
- Real root was one kernel build (kasumi's 7.2.8) and one terminal kind
  (a pseudo-terminal; PAX's console is a serial line); the sessions over
  the PS/2 keyboard were not typed but the probe's.
- UEFI, the release tier and more than one CPU: CI's full tier only; no
  hasu (KVM) run in this lane.
- A core dump on a host whose pattern is a file and whose limit allows
  one (the guest's limit is 0; kasumi's and CI's patterns pipe).

### Issues

- **To close at merge**: none (the contract names no pax issue).
- **Would file (none filed)**:
  1. pax: `prlimit64` answers `RLIMIT_CORE` unlimited (soft and hard)
     while PAX writes no core and never sets `wait4`'s core bit; Linux's
     boot answers soft 0 (hard unlimited), under which it writes none
     either, so PAX's answer and its behaviour disagree
     (`notes/px53/linux-limits.txt`). Small: answer soft 0, measured.
  2. pax: no `/proc/self/limits` and no `/proc/sys/kernel/core_pattern`
     (-ENOENT; Linux has both).
- Nothing to file for the calls (§F), pelt, boreutils or wolf.

## 5. Done-when

- Branch `px53` on origin; the pax pull request (number in the
  hand-back), open, unmerged; `full-matrix` added at the final head.
- The five sections §1 to §5; the items §A to §K.
- The test checklist:
  - [x] the pins, each its own commit; the archives read twice each way
  - [x] the binaries' digests as predicted, in two builds and in CI
  - [x] the first boot at the pins: the 52 pjobs runs and groups as
        recorded
  - [x] real root's recordings twice, the same bytes; pjobs as committed
  - [x] groups with bu28's rows and sigs byte-identical to real root at
        PAX's first boot, root and `pax`; the container's but the
        host's core rows
  - [x] `tests/mpx5-jobs` on kasumi, native BIOS, every image
  - [x] `tests/mpx3-shell`, `mpx3-tree`, `mpx5-accounts`,
        `mpx3-boreutils`, `mpx5-users`, `mpx3-speaker`, `mpx3-console`,
        `mpx3-screen`, `mpx3-threads`, `mkw`, `tour` on kasumi, native
        BIOS
  - [x] `tests/ci-plan`, every case, two new
  - [x] the kernel's cost: 0 on every section
  - [x] plant A green (39387318671), plant B red at the new rows
        (39387322394)
  - [x] the playground rebuilt, smoke-booted, on nomad-1
  - [ ] the pull request's run (`tier full`, the pin) green at the final
        head; `full-matrix` added there; the full run held by the
        orchestrator (ruling #92)
- `wolf/tools/lane-audit.sh pax px53 <PR>` exit status: named in the
  hand-back.
- Trees: kasumi `~/lanes/px53/` keeps `out/`, `keep/`, `ev/`, `vm/rec1`,
  `vm/rec2`, `bin/`, `cache/`; build directories removed at the end.
  Plant branches stay on origin, never to be merged.
