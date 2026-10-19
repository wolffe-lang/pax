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

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | both pax pins move, each its own commit; su builds; the kernel builds on 0.2.32 with no source change; text moves under 1 KiB; `tests/mkw` step 6 holds | `user/su` `7a7cae8`, `kernel/wolf.pin` `eea2d5d` (with `pax_tour.lu`'s line); su builds (`ca78e313…`, 13,972,544 bytes, in mpx3-shell's, mpx3-tree's and mpx5-accounts' builds); every kernel builds with no source change; `tests/mkw` PASS (step 6's four rows as written: the checked machine and lupin 0.1.54 still refuse the freestanding kernel by name) and `tests/tour` PASS on kasumi. **The text moved by more than predicted**: kmain_console native `.text` 932,907 → **943,323** (+10,416), release 827,627 → **790,331** (−37,296); kmain_session native +10,416, release −8,944; `.rodata` within 808 bytes, `.data` and `.bss` the same (§G) | right but the size |
| P2 | `76f3fc40…`, `0f4fb3b7…`, `de9104db…`, each in two builds and in CI; every other utility moves | pelt **`76f3fc40…`** (15,198,832) in five builds on kasumi (mpx3-shell, mpx3-tree, mpx5-jobs twice, mpx5-accounts); `kill` **`0f4fb3b7…`** (13,949,544) and `timeout` **`de9104db…`** (14,525,248) in both mpx5-jobs builds; the same as sh18's and bu27's own; every boreutils binary PAX ships moved (`cat` `1f00ef21…` → `3e37ada0…`, `sleep` `9c7282f5…` → `bb0ccafa…`); CI's in §F | right |
| P3 | every pjobs session identical on PAX, the guest and the container, at the first boot; weak: a notice a prompt late, reshaped if so | **at the first PAX boot all 52 runs (26 cases, root and `pax`) byte-identical to real root's guest, and the 26 user runs to the container** (`notes/px51/kasumi-first-mpx5-jobs.out`: 22 PASS, the other 30 flagged only by the suite's line-count floor, which was the BusyBox session's and is 2 lines for these; one witness word written wrong, `^trapped` for `^Ctrapped`, fixed in the test, not the session). No case reshaped. Variants: five (§A) | right |
| P4 | groups identical at the first boot, no kernel change | one line apart at the first boot, **a Linux-side race**: `[2] + Killed` came one prompt later on the guest than on PAX (the guest's group members died after `/bin/kill` had been reaped and the prompt drawn; on PAX before). Reshaped as px48 did: each group send and its `sleep 0.5` on one line, so the notice always comes before the next prompt; recorded again. Two of my own mistakes in the session, not PAX's: `timeout 5 true` with no `true` in the archive (127; `true` added), and `/etc/pax-run`, which the container's tree lacks (now `/g/text`, in both). After that, identical on all three, root and `pax` | right, one race reshaped |
| P5 | every new call served; no -ENOSYS but 273 and 334, no `refused:` line | so, in every pjobs and groups boot (J6 on kasumi and in CI). How each is served: §C | right |
| P6 | no compared session moves; `shell-sigs.expect` may move (weak) | **nothing moved**: `user/console/shell-sigs.expect` still Linux's transcript at the new pelt (mpx3-shell S6 PASS, `dd691f0e…`), as are `shell-howl`, `shell-plumb`, `shell-long`, the speaker's and session suite's references, `tests/mpx5-accounts.d/linux/accounts.tty` and `tests/mpx3-speaker.d/linux/beep-user.tty`; nothing re-recorded (§D) | right (the weak guess wrong) |
| P7 | every suite green as root and as a user at the new pins | kasumi, native BIOS under `taskset -c 0-3`: the 14 suites with a kasumi path PASS (§E); CI's `tier full` at the final head: the pull request (§F) | right on kasumi |
| P8 | plant A red at the pelt sessions' first key to a job and BusyBox's; plant B red at groups' group send and timeout's child | both red in CI on all four legs, but **first at px48's probe**, whose hung boot then stops every later typed boot (qemu-halt's fail-fast); on kasumi with the new images alone: A red in 21 of 26 pelt sessions, B red at groups' timeout row and in the pelt sessions (§H) | partly right |
| P9 | kernel text under 1 KiB | +10,416 bytes native, −37,296 release (kmain_console) | wrong |

## A. The sessions (items 2 and 3)

`user/console/pjobs/`: sh18's 26 `c_jc_*` sessions (pelt `2676879`'s
`tests/session/*.keys`), in `tools/qemu-halt`'s notation: a `^Z` or
`^C` line is `^~^Z^.` (typed at the running program, after the
harness's pause), and five more changes, each named here:

- **Timing**: the pause before a key typed at a running program is 2 s
  on PAX's harness and 1.5 s in the guest's `vmjob`, so a `sleep 1` the
  key must catch is `sleep 5` (`c_jc_bg`, `c_jc_mixed_pipeline`), and a
  `sleep 1 &` the next line must still find running is `sleep 3 &`
  (`c_jc_fg_number`, `c_jc_wait_stopped`). `c_jc_fg`'s `typed after fg`
  is typed at the continued `read` (`^~`); `c_jc_shell_ignores_tstp`'s
  `^Z` at the prompt is a step of its own and `echo alive` follows it
  at the running shell.
- **Variants** (PAX has no `ps` and no `sed`): `c_jc_background_group-proc`,
  `c_jc_foreground_group-proc`, `c_jc_shell_is_leader-proc`,
  `c_jc_kill_group-proc` read the group, the foreground group and the
  parent's group from `/proc/<pid>/stat`'s fields 5 and 8 with `cut`
  (the background job writes `/g/out`: `/` is root's 0755 on PAX and in
  the guest); `c_jc_jobs_l_pipeline-tr` squeezes digits and blanks with
  `tr` instead of `sed`.

Each case is one run of `/bin/sh -i -m` (pelt as `sh`) in the pjobs
image, and through `/bin/as 1000 1000` in pjobs-user. **On PAX, as root
and as `pax`, every session is byte-identical to the same pelt on real
root's guest** (279 lines over the 26 cases), and the user's to the
container's: `jobs` and its marks and columns, `Stopped`, `Stopped
(signal)`, `Stopped (tty input)` for a background `cat`, `Running`,
`Done(3)`, `Terminated`, `Killed`, a stopped foreground job's `$?` as
`128 + N` (`st=TSTP`, `st=STOP`), Ctrl-C reaching the job alone (`$?`
130, a loop abandoned, a trap run), Ctrl-Z ignored by the shell, `fg`
continuing a stopped `read`, `exit`'s `there are stopped jobs`, job ids
`%?31`, `%-`, `%+`, `%sleep`, numbering by the lowest free slot, and the
`/proc` variants' `leader`, `foreground`, `own-group`, `group-is-pid`.
The guest's recordings were made twice, the same bytes (§4).

## B. kill's groups and timeout (item 3)

`user/console/groups.keys`, typed at pelt (root, then `pax`): two
background `sleep`s and `/bin/kill -- -$!` (the second job's group ends,
`Terminated`); a job of `sh -c 'sleep 30 & sleep 31; wait'` and
`/bin/kill -s KILL -- -$!` (the whole group, `Killed`); a group nobody
is in (`kill: '-32000': No such process`, 1); `/bin/kill 0` from a job
of its own (its group ends, `ended by signal 15 (TERM)`, 143); `kill -0
0` and `kill -s 0 -- -1` (0); `-l 64` (`RTMAX`), `-t 34`
(`34 RTMIN Real-time signal 0`); then `timeout`: 124 at expiry, 137 with
`-s KILL` and with `-k` (timeout ended by its own group's KILL: `ended by
signal 9 (KILL)`), `--foreground` 124, a command that ends first (0, 3),
`-p` 143, **the group**: `timeout 1 sh -c 'sh -c "sleep 2; echo
survived" & wait'` prints nothing after the expiry while the same with
`--foreground` prints `survived` a second later; a stopped command
continued at the expiry (124); `timeout 0.5 cat` (timeout's own group is
a background group of the terminal, so `cat`'s read is stopped by
SIGTTIN, and the expiry's TERM and CONT end it: 124); `-v`'s line;
125, 127, 126 with timeout's own messages. 73 lines, **byte-identical
to real root's guest as root and as `pax`, and to the container's**.

## C. The calls, and how each is served (item 3)

PAX writes nothing for a call it serves; it writes `-ENOSYS` or
`refused:` for one it does not. Every pjobs and groups boot printed only
glibc's `set_robust_list` (273) and `rseq` (334) -ENOSYS and no
`refused:` line (J6), and the sessions' rows are the calls' answers:

| call (bu27's and sh18's traces) | who asks | on PAX |
|---|---|---|
| `setpgid` (in the child and the parent), `getpgrp` | pelt (sh18: new), `timeout` (`setpgid(0, 0)`), `kill 0` (`getpgrp`) | served since px48; `group-is-pid`, `own-group` and timeout's group rows |
| TIOCSPGRP/TIOCGPGRP | pelt | served since px48; every foreground job |
| `kill(-pgid)`, `kill(-1, 0)` | pelt's and boreutils' `kill`, `timeout` at expiry | served since px48 / px45; the group rows |
| `wait4(…, WNOHANG\|WSTOPPED)` | pelt, `timeout` | served since px48; the stops |
| `socketpair(AF_UNIX, SOCK_SEQPACKET\|SOCK_CLOEXEC)`, `recvfrom` | `timeout`'s spawn (its exec-error channel) | served since px34 / px17: the 127 and 126 rows carry `execve`'s ENOENT and EACCES through it, as on Linux |
| `clone` (a fork) and `execve` | `timeout`'s spawn | served since px17 |
| `vfork` | **not boreutils'**: in bu27's trace it is the container's dash (`sh -c`) starting `sleep`; on PAX `sh` is pelt | not asked by these binaries |
| `clone3` threads, `sched_getaffinity` | wolf's runtime in `timeout` (37 at kasumi's 16 cpus) | served since px26 / px24; on PAX's one CPU `timeout` runs **5 threads, as on the one-CPU guest** (`notes/px51/kasumi-threads.out`) |
| `prctl(PR_SET_NAME)`, `madvise(MADV_FREE, MADV_NOHUGEPAGE)`, `poll`, `rt_sigsuspend`, `tgkill(SIGALRM)` | the runtime | served (px24, px26, px49) |
| `restart_syscall` | strace shows it after a stop; no program asks it | — |

So nothing was refused, nothing was added, and nothing is to file for
the calls.

## D. What moved (item 4)

Nothing the new pelt or boreutils changes moved a session PAX holds to
a recording: `user/console/*.expect` (mpx3-shell's S6, mpx3-speaker,
mpx4-session's E2), `tests/mpx3-speaker.d/linux/`,
`tests/mpx5-accounts.d/linux/` and mpx5-jobs' BusyBox and probe
recordings each stood (§E, §F). pelt's job control is on in every typed
pelt session now (each typed program a group of its own, given the
terminal), but none of those sessions starts a background job, so no
notice is due, and a foreground program ended by Ctrl-C answers as
before (`shell-sigs`' `sleep 30`: `$?` 130, the same bytes). So nothing
was re-recorded. The new recordings are the pjobs and groups sessions'
(§A, §B), each made on real root's guest, never written by hand.

## E. Existing suites on kasumi

Native, BIOS, TCG, under `taskset -c 0-3` (the builds in `px13-ubuntu`
on cpus 4-15): `mpx5-jobs` (every J, the new J9 and J10 among them),
`mpx3-shell`, `mpx3-tree`, `mpx5-accounts`, `mpx3-boreutils`,
`mpx5-users`, `mpx3-speaker`, `mpx3-console`, `mpx3-screen`,
`mpx3-threads`, `mkw`, `tour`: every one PASS, no FAIL line
(`notes/px51/kasumi-*.out`). `mpx4-session`, `mpx4-lobo`, `mpx4-unix`
and the network suites: CI's runs only (their Linux sides need an
engine on the host that this lane's wrapper runs inside one).
`tests/ci-plan`: 151 PASS (148 and three new P2 cases;
`notes/px51/kasumi-ci-plan.out`).

## F. CI

- The tiers: the branch changes `kernel/wolf.pin` (FULL in
  `tools/ci-tiers.map`), so every pull-request push of this branch runs
  every suite on every leg; `full-matrix` is added once the head is
  final, and the `tier full` run at that head is named in the pull
  request (a commit naming it would move the head).
- Earlier heads' runs were cancelled by the next push (the pull
  request's own concurrency group): 39178393077 (`f58a928`), 39180425379
  (`81f5401`), and the run at `e98598e`.

## G. The kernel's cost (P9)

Built in `px13-ubuntu` from trunk `b274030` (wolf 0.2.28) and the
branch (0.2.32), the same kernel source but `pax_tour.lu`'s one line
(`notes/px51/kasumi-kernel-cost.txt`):

| kernel | tier | `.text` 0.2.28 → 0.2.32 | `.rodata` | `.data`, `.bss` |
|---|---|---|---|---|
| kmain_console | native | 932,907 → 943,323 (+10,416) | 61,832 → 61,832 | same |
| kmain_console | release | 827,627 → 790,331 (−37,296) | 66,616 → 67,424 | same |
| kmain_session | native | 935,659 → 946,075 (+10,416) | 62,096 → 62,096 | same |
| kmain_session | release | 823,915 → 814,971 (−8,944) | 66,432 → 66,440 | same |

The compiler's code generation moved between 0.2.28 and 0.2.32 (no
kernel source did); px36's +224 bytes was one release's step.

## H. Plants (P8)

Each a branch never to be merged, cut from `87b5ce3` (the code and the
tests as at the head but the words), one commit, run in CI by dispatch
with `mpx5-jobs` the only suite (`gh workflow run ci -r <branch> -f
suites=mpx5-jobs`), all four legs; and on kasumi with the three new
images alone (`PAX_JOBS_BOOTS`, `notes/px51/plant-run.sh`), because in
CI the probe's boot is first and stops the rest.

| plant | branch, commit | break | CI | kasumi, the new images |
|---|---|---|---|---|
| A | `px51-plant-a` `0e22d80` | TIOCSPGRP answers 0 and changes nothing | run **39178241978**, job 117825396101: red on all four legs, first at the probe's J1 (`T: tcgetpgrp(0) is the job's group: no`), then its first prompt never came, so qemu-halt's fail-fast refused every later typed boot of the run (`notes/px51/ci-39178241978-plant-a.txt`) | pjobs **21 of 26 cases red as root and as `pax`** (e.g. `c_jc_ctrl_z`: ^Z reaches nobody, `kill: 0: no signal has that number`); the five that pass ask nothing of the foreground (a background job, a `bg`, a background `cat`'s TTIN, Ctrl-C's `$?`); **groups green** (it asks nothing of the foreground: timeout's own group is a background group either way) (`notes/px51/kasumi-plant-a.out`) |
| B | `px51-plant-b` `a138973` | a group send reaches its leader alone | run **39178243818**, job 117825385232: red on all four legs, first at the probe's J1 (`K: kill(-A) from outside A: 0, heard A:USR1`), then the same fail-fast (`notes/px51/ci-39178243818-plant-b.txt`) | **groups red as root and as `pax` at exactly timeout's group row**: `survived` printed after the expiry without `--foreground` (timeout's TERM to its group reached timeout alone); pjobs red from `c_jc_fg_pipeline` on (`fg`'s SIGCONT to the job's group continued `sleep` and left `cat` stopped, so the shell waited for good) (`notes/px51/kasumi-plant-b.out`) |

P8 predicted the CI reds at the new rows; they came first at px48's
probe, which the plants break too, and the fail-fast hid the rest. The
new rows are seen red on kasumi: plant A by the pelt sessions (not by
groups, which P8 did not claim), plant B by groups' timeout row (as
predicted) and by the pelt sessions.

## 4. Evidence index

Shas are this branch's (`px51`). kasumi paths are under `~/lanes/px51/`.

### What was written

- The prediction: `f5c2026` (§1 to §3, before any change or
  measurement).
- The pins: `7a7cae8` (`user/su`, and ci.yml's comment), `eea2d5d`
  (`kernel/wolf.pin`, `pax_tour.lu`'s line), `dccb51f`
  (`user/pelt.pin`), `b368278` (`user/boreutils.pin`).
- The sessions and the suite: `958c672` (`user/console/pjobs/`,
  `user/console/groups.keys`), `40f154d` (`tests/mpx5-jobs`: the pjobs,
  pjobs-user and groups images, J9, J10), `81f5401` (`PAX_JOBS_BOOTS`),
  `c8c4eb3` (real root's recordings), `87b5ce3` (`tests/ci-plan`),
  `542d3dc` (ci.yml: the job's comment and the sums kept).
- The words: `0439984` (`kernel/README.md`), `ca352da`
  (`docs/SOURCES.md`), `f376bb6` (README), `9010c82` (CHANGELOG).
- The scripts: `f58a928`, `e98598e` (`notes/px51/*.sh`).

### What was measured, and where it is

- **The archives**: wolf 0.2.32 `4c37f9c5…` and lupin 0.1.54
  `175df238…` read from the release API twice and by `sha256sum` of the
  download on kasumi twice (§2).
- **The binaries**: `notes/px51/kasumi-mpx3-shell.out`,
  `kasumi-mpx3-tree.out`, `kasumi-first-mpx5-jobs.build.out`,
  `kasumi-mpx5-jobs.out`, `kasumi-mpx5-accounts.out` (each build's
  `program:` lines: pelt, su, kill, timeout and the rest).
- **Real root's Linux** (kasumi's 7.2.8-1-cachyos `f4c00d5d…` under
  QEMU 11.1.1, `notes/px50/vmjob.c` unchanged as pid 1, built
  `59141431…`; the suite build's own pjobs archive `a5bf603c…`):
  `tests/mpx5-jobs.d/linux/pjobs-*.tty`, `pjobs-user-*.tty`,
  `groups.tty`, `groups-user.tty` and their `.rc` and `vm-*.meta`;
  recorded twice (`vm/rec1`, `vm/rec2`), all 54 the same bytes
  (`notes/px51/kasumi-recordings-twice.out`). The first recording (the
  archive before `true` and `/g/text`), whose groups session raced:
  `notes/px51/linux-first-groups.tty`, `linux-first-groups-user.tty`,
  `kasumi-first-recordings.out`.
- **PAX's first boot** of the new images (that first archive, the
  branch's kernel): `notes/px51/kasumi-first-mpx5-jobs.out` (§3a P3, P4).
- **PAX at the head** (kasumi, TCG, native BIOS, `taskset -c 0-3`):
  `notes/px51/kasumi-mpx5-jobs.out` (every J), and `kasumi-mpx3-*.out`,
  `kasumi-mpx5-accounts.out`, `kasumi-mpx5-users.out`,
  `kasumi-mkw-tour.out`.
- **timeout's threads**: `notes/px51/kasumi-threads.out`
  (`notes/px51/threads.keys`): 5 on PAX, 5 on the one-CPU guest.
- **The kernel's cost**: `notes/px51/kasumi-kernel-cost.txt`.
- **The plants**: CI `notes/px51/ci-39178241978-plant-a.txt`,
  `ci-39178243818-plant-b.txt`; kasumi `notes/px51/kasumi-plant-a.out`,
  `kasumi-plant-b.out`.

### Measured, inferred, not verified

**Measured**: everything in §A to §H but what follows.

**Inferred**:
- That `timeout`'s spawn's channel is the SOCK_SEQPACKET pair on PAX as
  in bu27's Linux trace: PAX has no tracer; the 127 and 126 rows carry
  `execve`'s errors, which come back to timeout only through it.
- That nothing else in the pelt sessions (`mpx3-*`, `mpx5-accounts`)
  would move on a session that started a background job: none does.

**Not verified**:
- Real root was one kernel build (kasumi's CachyOS 7.2.8) and one
  terminal kind (a pseudo-terminal); PAX's console is a serial line.
  The pelt sessions over the PS/2 keyboard were not typed.
- `kill -1` with a real signal (only signal 0, to keep every other
  process of the guest and the container alive).
- `timeout` on a terminal with `--foreground` and a reader in the
  foreground (`timeout 0.5 cat` is the background case only).
- UEFI under KVM on hasu (pax#56): no hasu run in this lane; UEFI on
  CI's full tier only. More than one CPU (PAX runs one).
- The release tier on kasumi: CI's full tier only.

### Issues

- **To close at merge**: none (the lane's contract names no pax issue;
  pax#82, #83 stay open).
- **Would file (none filed)**:
  1. pax: in `tests/mpx5-jobs` the probe boots first, so a kernel break
     the probe catches hangs its boot and qemu-halt's fail-fast refuses
     every later typed boot of the run: a plant's CI run shows nothing of
     the later images (this lane's two, §H). `PAX_JOBS_BOOTS` lets a
     kasumi run pick images; a CI dispatch cannot pass it.
  2. pax: trunk's push run 39086412018 was red on `mpx4-udp` native
     UEFI only (the user image's boot printed nothing, U1–U5); the
     nightly at the same head was green. Seen once.
  3. wolf-lang (a note, not a defect): the kernel's native `.text` grew
     10,416 bytes from 0.2.28 to 0.2.32 with no kernel source change
     (release shrank 37,296 and 8,944): §G, for whoever tracks the
     freestanding target's size.
- Nothing to file for the calls (§C), pelt or boreutils.

## 5. Done-when

- Branch `px51` on origin; pax PR #84, open, unmerged.
- The five sections §1 to §5; the items §A to §H.
- The test checklist:
  - [x] `tests/mpx5-jobs` on kasumi, native BIOS, `taskset -c 0-3`
        (every J; J9 and J10 byte-identical to real root's recordings
        and the container's, root and `pax`)
  - [x] `tests/mpx3-shell`, `mpx3-tree`, `mpx5-accounts`,
        `mpx3-boreutils`, `mpx5-users`, `mpx3-speaker`, `mpx3-console`,
        `mpx3-screen`, `mpx3-threads`, `mkw`, `tour` on kasumi, native
        BIOS
  - [x] `tests/ci-plan`, every case, three of them new
  - [x] real root's recordings made twice, the same bytes
  - [x] plants A and B red in CI (39178241978, 39178243818) and on
        kasumi with the new images
  - [ ] `tier full` at the final head: named in the PR
- `wolf/tools/lane-audit.sh pax px51 84` exit status: named in the PR.
- Trees: kasumi `~/lanes/px51/` keeps `out/`, `keep/`, `ev/`,
  `vm/rec1`, `vm/rec2`, `bin/`, `cache/`; build directories removed at
  the end. Plant branches stay on origin, never to be merged.
