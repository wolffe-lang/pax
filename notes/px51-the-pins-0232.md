# px51 — The pins at 0.2.32 (pelt's job control and boreutils' groups on PAX)

Contract: px51's, `sprints/pax/51-the-pins-0232/px51-the-pins-0232.md`
in wolffe-lang/wolf (planning commit `0fb714c`, read 2026-10-18),
under px48's "Forbidden / rules" word for word but where px51 changes
them, and the rules of `sprints/crawl-54.md` and `sprints/wave-53.md`
down to `wave-45.md`. Branch `px51` in pax, cut from pax trunk
`b274030` (px50). §1 to §3 are committed before the first change to a
pin, the kernel, a tool, a probe or a test, and before the first
measurement.

One deliverable: pin bumps measured on PAX. **wolf** 0.2.32 / lupin
0.1.54 wherever pax pins it; **pelt** to `2676879` (sh18, job control;
static `76f3fc40…`, rebuilt and read twice); **boreutils** to `43ee185`
(bu27: 47 utilities, `kill`'s groups, the new `timeout`; static release
`kill` `0f4fb3b7…`, `timeout` `de9104db…`, rebuilt and read twice).
Then measured, never assumed: pelt's job control on PAX against Linux,
`kill`'s groups and `timeout` on PAX against Linux, root and user; the
calls bu27's strace names that no utility asked PAX for before; every
session the new binaries move, re-recorded against Linux.

## 1. Forbidden, absolutely

px48's §1, unchanged but for the lane's name and paths, and these:

- No kernel's, libc's, shell's or terminal driver's source is read, nor
  `su`/`login`/util-linux/procps source, nor any `kill`'s or
  `timeout`'s (GNU coreutils', procps', util-linux's, busybox's, any
  shell's) (ruling #22). Facts come from the man pages (`kill(1)`,
  `kill(2)`, `timeout(1)` as documentation, `setpgid(2)`, `credentials(7)`,
  `signal(7)`, `socketpair(2)`, `unix(7)`, `vfork(2)`, `clone(2)`,
  `proc_pid_stat(5)`, `termios(3)`, `ioctl_tty(2)`), POSIX.1-2024 (XCU
  2.11 Job Control, `kill`, `jobs`, `fg`, `bg`, `wait`; XBD 11), the
  allowed uapi headers, pax's own source, px38's to px50's notes, and the
  org's own notes and recordings: pelt `cc2fdc9`'s
  `notes/sh18-job-control.md` and its session keys (pelt's own tests,
  read as the org's code), boreutils `43ee185`'s `notes/bu27-the-groups.md`,
  `ev/straces.log` and its strace transcripts on kasumi (shipped binaries
  traced, read as recorded runs).
- A Linux answer nobody recorded is measured black-box: real root is
  kasumi's own kernel image under QEMU with a static program as pid 1
  (px48's `vmjob` way, the shell on a pseudo-terminal as its session
  leader); a rootless container only for a user's rows.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals go only to processes the test started inside
  PAX, the guest or the container; `kill -1` only with signal 0, and
  only inside them.
- Probe and test binaries static, built in `px13-ubuntu`, never with
  kasumi's CachyOS glibc. No build on nomad-1. kasumi and hasu under
  `bash` (hasu `env bash`), long jobs `setsid` with a pid file, ended by
  that pid only; work under `~/lanes/px51/`, pruned; never `/tmp`.
  Process, signal and terminal tests also under `taskset -c 0-3`; SigBlk
  and SigIgn read before a signal row is called red. Ports 8080 and 8088
  unused; nothing installed; hasu's maintainer data and :9308 untouched.
- Toolchains from release archives by digest, each read twice: wolf
  0.2.32 (`v0.2.32` at `72de141f`), lupin 0.1.54 (`v0.1.54` at
  `0e536e8`), the bundled std wolf-std `d37c911`.
- No `rm` outside `~/lanes/px51/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No
  other lane's run cancelled; the CI share is with every other running
  lane; plants by dispatch for one suite. A pin bump is a full-tier
  change: `full-matrix` only once the head is final. "Seen red" cites a
  run. Nothing says "secure"; no word implying filming. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-18)

| input | found |
|---|---|
| pax trunk | `b274030` (px50, PR #81 merged), the contract's; no pax PR open. Trunk's push run 39086412018 red on one job (`mpx4-udp` native UEFI: the boot printed nothing, U1–U5), its nightly 39121425434 at the same head green |
| planning repo | `0fb714c` (the contract; crawl 54's batch 8) |
| wolf 0.2.32 | `v0.2.32^{commit}` `72de141f6246…`; release 416327027, the linux x86-64 archive `4c37f9c5dc3d8830c06810948027d38bdbc375dc5524ab23127b0ada0907d851`, 80,092,071 bytes (the API, read twice); its CHANGELOG's downstream line: "**pax:** the pin (it builds from the archive)" |
| lupin 0.1.54 | `v0.1.54^{commit}` `0e536e8fb451…`; release 415937354, linux x86-64 `175df23880cd5bb993b778e5c8fdd7d0d96c176696802e640f6fc87d3dab40dd`, 2,971,403 bytes (read twice) |
| wolf-std | `d37c911` (sc63), the archive's bundled std; `a0d0c87` (su's, sc62) is its ancestor |
| where pax pins wolf | (1) `kernel/wolf.pin`: wolf **0.2.28** / lupin **0.1.51** (px36), read by `tools/fetch-wolf`, `tools/fetch-lupin`, the kernel's every build, `tools/mkplay`, `tests/mkw`, `tests/tour`; `kernel/pax_tour/pax_tour.lu` prints `wolf 0.2.28` as text. (2) `user/su/wolf-toolchain.toml`: wolf **0.2.30** / wolf-std `a0d0c87` (px46), read by `tools/mksu`; no lupin. (3) Not pax's own: `user/lobo.pin` (lobo's tree and the archive digest lobo's toolchain names), `tools/census/inside/pins.sh` (0.2.22, the frozen census of px04's time), pelt's and boreutils' own `wolf-toolchain.toml` (read by `tools/mkpelt`, `tools/mkboreutils`) |
| pelt | `2676879` (sh18's last code commit; trunk `cc2fdc9` adds notes only: `git diff 2676879 cc2fdc9 -- src wolf-toolchain.toml` empty); pins wolf 0.2.32 / lupin 0.1.54 / std `d37c911`. sh18: job control on by default when interactive (`set -m`), the shell leads a group and takes the terminal, each top-level pipeline a job in a group of its own, `jobs`/`fg`/`bg`/`%` ids, `kill` to a job's group, notices; new calls `setpgid` and `getpgrp`; its static build at pax `b274030`'s `tools/mkpelt` with `ld.lld`: `76f3fc40702af01b6381d01a7f81de2ebe701787ee29ef61484dc7ad1ec29849`, 15,198,832 bytes; 25 job-control sessions (`tests/session/c_jc_*`), one pending on fork (`c_jc_mixed_pipeline`) |
| boreutils | `43ee185` (bu27; trunk is it); pins wolf 0.2.32 / lupin 0.1.54 / std `d37c911`; from `8f0bbb1`: `src/kill.lu`, `src/bore/signals.lu`, `src/sleep.lu` (its duration parsing moved to the new `src/bore/duration.lu`), the new `src/timeout.lu`; 47 utilities. Static (bu27, `cc -static`): release `kill` `0f4fb3b72a41fcbd75a7a087e766be21680a12708655990f3c1f308fd7134b5e` (13,949,544), release `timeout` `de9104db3b5a8e578a2895a8b006e31ebe533eb55fedc818c0cd23baa710c899` (14,525,248); not booted on PAX |
| bu27's strace (`ev/straces.log`, kasumi `~/lanes/bu27/ev/strace/`) | `kill`: `kill(-PGID)`, `getpgrp` then `kill(-PGRP)` for `0`, `kill(-1)`, `statx` on fd 1. `timeout`: `setpgid(0, 0)`, `socketpair(AF_UNIX, SOCK_SEQPACKET\|SOCK_CLOEXEC)` and `recvfrom` (the spawn's exec-error channel), `clone` (a fork), `vfork` (in one trace), 37 `clone3` threads at 16 cpus (`sched_getaffinity`), `prctl(PR_SET_NAME, "wolf-signal")`, `poll`, `rt_sigsuspend`, `tgkill(SIGALRM)`, `wait4(…, WNOHANG\|WSTOPPED)`, `kill(-pgrp, TERM/KILL/CONT)`, `madvise(MADV_FREE, MADV_NOHUGEPAGE)` |
| those calls on PAX today (`kernel/user` dispatch, its comment) | `vfork` (58) and `clone3` with CLONE_VM\|CLONE_VFORK (px17), `clone3` threads (px26), `socketpair` with SOCK_SEQPACKET (px34), `recvfrom` (px17/px22), `poll` (px24), `sched_getaffinity` (one CPU), `madvise` (px24), `prctl` (PR_GET_NAME and others), `rt_sigsuspend` (px49), `tgkill` (px26), `setpgid`/`getpgrp`/`kill(-g)`/`wait4` with WUNTRACED (px48): none is -ENOSYS by the table; whether each answers as Linux for these arguments is this lane's measurement |
| suites that build pelt or boreutils | `tools/mkpelt`: mpx3-shell, mpx3-console, mpx3-screen, mpx3-speaker, mpx3-tree, mpx4-session, mpx4-lobo, mpx5-accounts; `tools/mkboreutils`: those but console and screen, and mpx3-boreutils, mpx5-users. None ships `kill` or `timeout`. Fixed references a new binary could move: `user/console/*.expect` (Linux's transcripts, mpx3-shell S6, mpx3-speaker, mpx4-session E2), `tests/mpx3-speaker.d/linux/`, `tests/mpx5-accounts.d/linux/` |
| px48's witness | `tests/mpx5-jobs` J2/J3: BusyBox ash typed `sh -i`, held to real root's guest and the container; pelt made no groups then (px48 §I "pelt's own job control (it makes no groups yet)") |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, `/home` 33 GB free, `px13-ubuntu` `ad8964505189`, load 0.7 |
| open issues | pax#55, #56, #62, #67, #82, #83 (#82, #83 stay open: not this lane) |

## 3. Prediction (committed before the first change and measurement)

**P1. The wolf pins.** Both of pax's own pins move, each its own
commit: `user/su/wolf-toolchain.toml` to wolf 0.2.32 (`4c37f9c5…`) /
wolf-std `d37c911`, and `kernel/wolf.pin` to wolf 0.2.32 / lupin 0.1.54
(`175df238…`), with `pax_tour.lu`'s line. su builds unchanged (no
prelude name it declares came in 0.2.31 or 0.2.32). The kernel builds
on 0.2.32 with no source change (0.2.29–0.2.32's new builtins are
hosted and the kernel calls none); every kernel's text moves by under
1 KiB (the runtime archive and codegen, as px36's +224 bytes), and
`tests/mkw`'s step 6 (the checked machine and lupin refusing the
freestanding kernel) holds its rows as written. lobo's pin, the census
pins and pelt's and boreutils' own tomls are not pax's to move (named).

**P2. The rebuilt binaries.** In `px13-ubuntu` on kasumi with the
suites' own tools: `tools/mkpelt` at `2676879` builds
**`76f3fc40…`** (15,198,832 bytes); `tools/mkboreutils` builds `kill`
**`0f4fb3b7…`** (13,949,544) and `timeout` **`de9104db…`**
(14,525,248), each read in two builds (two suites' builds on kasumi)
and again in CI. Every other boreutils utility's digest moves (the
0.2.32 runtime; bu27: 92 of 92 binaries differ).

**P3. pelt's job control on PAX.** sh18's job-control sessions run on
PAX's console as root (pelt pid 1, the kernel's session leader that
owns the console) and as `pax` (through `as 1000 1000`), typed by
`tools/qemu-halt`, each held byte-identical to the same pelt binary on
real root's guest (on a pseudo-terminal as its session leader) and, the
user's, in the container. Which sessions: every `c_jc_*` case whose
programs PAX has (pelt as `sh`, boreutils' `sleep`, `cat`, `wc`, `tr`);
the four that ask `ps` (absent from PAX) and the one that asks `sed`
run as variants that read `/proc/<pid>/stat` with `cut` and squeeze
with `tr` instead, named as variants. **Every session identical on all
three, at the first boot**: PAX answers each call pelt's job control
makes as Linux does (px48 measured them all for BusyBox's ash:
`setpgid` in child and parent, TIOCSPGRP, `kill(-pgid)`, `wait4` with
WUNTRACED, the stop and continue, ^C and ^Z to the foreground group,
TTIN for a background reader). Weak: the notice of a job that ends
while the shell sits at its prompt (sh18's host race: pelt now reads
the table only after the line has run) and a `sleep 0.3` wait under
TCG on PAX may place a `Done` line a prompt late; if so the session is
reshaped as px48 did (a command on the same line), never the
comparison loosened.

**P4. kill's groups and timeout on PAX.** A new typed session at pelt
(`groups`, root and `pax`): `/bin/kill -- -PGID` of a job's group
(every member ends), `-s KILL`, a group nobody is in (`No such
process`, 1), `/bin/kill 0` from a job of its own (the job's group ends,
143), `kill -0 0`, `kill -s 0 -- -1` (0), `-l`/`-t` of a real-time
number; `timeout`'s 124 at expiry (its command's own child ended with
it: the group), `-s KILL` (137, timeout ended too), `-k` (137),
`--foreground` (124, the command's child outlives it), `-p` (143), a
command that ends first (its status), a stopped command continued
(124), 125/126/127, `-v`'s line. **Identical to real root's guest and
the container, at the first boot, with no kernel change**: every call
bu27 traced is served (P5).

**P5. The new calls.** `socketpair(AF_UNIX, SOCK_SEQPACKET|
SOCK_CLOEXEC)` with `recvfrom` (the spawn's error channel): served as
Linux (px34's SEQPACKET pair: the exec's success is the end of the
peer, 0 bytes); `vfork`: served (px17); `clone3` threads: served, and
on PAX's one CPU the runtime starts fewer of them (`sched_getaffinity`
answers one CPU) — no table limit reached (64 threads a machine);
`prctl(PR_SET_NAME)`: served; `madvise(MADV_FREE)` and
`MADV_NOHUGEPAGE`: served as no-ops; `restart_syscall` appears in
strace only after a stop and is never asked of PAX. So **no -ENOSYS
but 273 and 334, and no `refused:` line**, in any new session. Weak:
`prctl` or `madvise` with an argument nothing asked before; if one is
refused by name, it is served if small or refused with Linux's answer
and listed to file.

**P6. What moves.** No compared session's text moves on PAX against its
live Linux side, since both sides run the same new binaries. The fixed
references: **`user/console/shell-sigs.expect` may move** (a `sleep 30`
ended by ^C is now a job pelt answers as an interrupt it heard; the
text after it may gain or lose a newline) — weak; the speaker's, the
accounts' and the session suite's references do not (no ^C or ^Z at a
running program there). Anything that moves is re-recorded from the
Linux side by the suite's own recording path, never hand-edited, and
named with its reason. The BusyBox sessions (J2/J3) and the probes
(J1, J7, J8) do not move.

**P7. Existing suites.** Every suite green as root and as a user at the
new pins, on kasumi (the ones with a kasumi path) and in CI's `tier
full`.

**P8. Plants**, each a branch never merged, one commit, one suite by
dispatch: A, the console's TIOCSPGRP answers 0 and changes nothing
(the foreground group stays the shell's): `mpx5-jobs` red at the pelt
sessions' first ^C or ^Z to a job (the shell hears it, or the job's
read stops it), the BusyBox shells red too; B, `kill` with a negative
pid sends to the caller's group, not the named one (or: the group send
skips every member but the leader): `mpx5-jobs` red at `groups`' row
for the job's group and timeout's surviving child, root and user.

**P9. Cost.** The kernel text at 0.2.32 against 0.2.28 under 1 KiB a
kernel (P1); nothing else in the kernel changes unless P5 is wrong.
</content>
</invoke>
