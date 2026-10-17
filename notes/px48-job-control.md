# px48 — Job control (process groups, sessions, the controlling terminal)

Contract: px48's, `sprints/pax/48-job-control/px48-job-control.md` in
wolffe-lang/wolf (planning commit `ed700dc`, read 2026-10-17), ruled by
#79 R9 ("PAX job control after U5"), under the rules of
`sprints/crawl-54.md` and `sprints/wave-53.md` down to `wave-45.md`.
Branch `px48` in pax, cut from pax trunk `5c36560` (px47). §1 to §3 are
committed before the first change to the kernel, a tool, a probe or a
test, and before the first measurement.

One deliverable: **PAX keeps process groups and sessions and a
controlling terminal as Linux does**, measured black-box against Linux:
the group and session calls, the console as a controlling terminal and
its ioctls, `kill` to `0`, `-1` and `-pgid` (px45's `may_signal` per
member), the waits with `WUNTRACED`, `WCONTINUED` and a group or `0`,
stops and continues, the line discipline's signals to the foreground
group and the background rules (`TOSTOP`), hangup and the orphaned
group; and pax#66 (VTIME with VMIN above 0) and pax#68 (the window size
with a display) in the same console code. The witness: a static
Almquist shell, typed at PAX's console doing `sleep 100 &`, `jobs`, a
foreground job stopped by `^Z`, `fg`, `bg`, `kill %1`, `wait`, held to
the same session under real Linux in QEMU and in a container, as root
and as `pax`.

## 1. Forbidden, absolutely

- No kernel's, libc's, shell's or terminal driver's source is read, nor
  `su`/`login`/util-linux/procps source (ruling #22). Facts come from
  the man pages (`credentials(7)`, `setpgid(2)`, `setsid(2)`,
  `getsid(2)`, `wait4(2)`, `waitid(2)`, `wait(2)`, `kill(2)`,
  `signal(7)`, `sigaction(2)`, `termios(3)`, `tty_ioctl(4)` /
  `ioctl_tty(2)`, `TIOCSCTTY(2const)`, `TIOCSPGRP(2const)`, `tty(4)`,
  `proc_pid_stat(5)`), POSIX.1-2024 (XBD 11 General Terminal Interface,
  XBD 3 *Orphaned Process Group*, XSH `setpgid`, `setsid`, `tcsetpgrp`,
  `tcgetpgrp`, `tcgetsid`, `waitpid`, `waitid`, `kill`, `_exit`'s
  consequences, the job-control rationale), the allowed uapi headers,
  pax's own source, wolf-lang `211d28cb`'s s240 note, probes (`grp.c`,
  `sess.c`) and their recorded Linux answers and strace transcripts of
  shipped binaries, s242's `[os.proc.wait.note]`, and px38's to px47's
  notes.
- A Linux answer nobody recorded is measured black-box: real root is
  kasumi's own kernel image booted under QEMU with a static program as
  pid 1 (px38's way; px46's `vmtty.c` shape for anything typed on a
  terminal); a rootless container only for a user's rows, never for
  what root may do.
- The witness shell is **run, never read**. The contract names "a static
  dash (the Debian/Ubuntu package's binary)"; no such package exists
  (§2: Ubuntu 24.04 and Debian stable ship `dash` dynamically linked
  and PIE only, which PAX's loader refuses by name). I use the nearest
  thing that is a distribution package's static binary: **Ubuntu 24.04's
  `busybox-static`** (`1:1.36.1-6ubuntu3.1`), whose `sh` is BusyBox's
  `ash`, the Almquist shell dash also descends from, run as `sh -i`.
  This substitution is the lane's, named here and in the report.
- Every check gets a user row (px47's rule); every existing suite stays
  green as root and as a user. Signals in tests go only to processes the
  test started inside PAX, the guest or the container.
- Probe and test binaries are static, built in `px13-ubuntu` (glibc
  2.39), never with kasumi's own glibc (CachyOS, AVX-512).
- No build on nomad-1. kasumi and hasu: commands under `bash` (hasu:
  `env bash`), long jobs under `setsid` with a pid file, ended by that
  pid only (never by name, pattern or process group); work under
  `~/lanes/px48/`, pruned as I go; never `/tmp`. Process, signal and
  terminal tests also under `taskset -c 0-3`; SigBlk and SigIgn read
  before any signal row is called red. Host ports 8080 and 8088 are
  not used. Nothing is installed anywhere. hasu's port 9308 untouched.
- No `rm` outside `~/lanes/px48/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled. "Seen red" cites a run. Nothing says
  "secure"; no word implying filming. If the harness refuses an action
  I stop and report.

## 2. Inputs, verified (2026-10-17)

| input | found |
|---|---|
| pax trunk | `5c36560` (px47 merged, PR #69), the contract's; `origin/trunk` the same at the start; no pax PR open |
| planning repo | `ed700dc` (the contract), `origin/trunk` at `ffd1d4d` when read; crawl 54 records the launch ("yes, launch all three") |
| the kernel's pin | wolf 0.2.28 / lupin 0.1.51 (`kernel/wolf.pin`), unchanged by this lane; pelt's own toolchain (wolf 0.2.30, lupin 0.1.53, wolf-std `fd6bcdc`) is `tools/mkpelt`'s, from pelt's `wolf-toolchain.toml` |
| groups and sessions today | none: `setpgid` (109), `getpgrp` (111), `setsid` (112), `getpgid` (121), `getsid` (124) are -ENOSYS (`tests/mpx5-users`' `IDS_ENOSYS`); `/proc/<pid>/status` prints `NSpgid 1`, `NSsid 1` fixed; there is no `/proc/<pid>/stat` |
| the terminal today | the console answers TCGETS, TCSETS*, TIOCGWINSZ, TIOCSWINSZ and the speaker's two; every other request is refused by name (-ENOTTY); `console.controlling()` is `true` for everyone (px45); `/dev/tty` opens the console for anyone |
| signals today | `kill(0)` and a negative group mean every process (one group, by `may_signal` each); SIGCONT passes `may_signal` for anyone ("one session"); the terminal's keys raise for every process (`signal.tty`); SIGSTOP, SIGTSTP, SIGTTIN, SIGTTOU at their default are dropped with a line `refused: stopping a process (no job control)` |
| waits today | `wait4`'s 0 and -pgid and `waitid`'s P_PGID mean any child; WUNTRACED and WCONTINUED are accepted and nothing is reported; waitid without WEXITED is -EINVAL |
| the console's line discipline | ISIG, the three keys; no TOSTOP, no background check; VMIN above 0 answers whatever is ready (VMIN is not waited for) and VTIME is ignored with it (pax#66); TIOCGWINSZ the screen's grid when a display exists (pax#68) |
| s240's recordings (wolf-lang `211d28cb`, `docs/s240/ev/linux/run-linux.log`) | `grp` and `sess` on Linux 7.2.8 in rootless podman, root and 1000, glibc and musl: the rows §3 builds on (`kill(-G)` with no group ESRCH, all zombies 0, none permitted EPERM; SIGCONT across sessions EPERM; setsid by a group leader EPERM; setpgid into a missing group EPERM, after exec EACCES, of a grandchild ESRCH; tcsetpgrp from an orphaned group ENOTTY (pty), to a missing group ESRCH, 0 ESRCH, -1 EINVAL; WUNTRACED and WCONTINUED each reported once; the interrupt character reaches the foreground group only; the orphaned group's stopped member hears HUP and CONT); dash's strace (`dash-im.trace`): `setpgid` in child and parent, TIOCSPGRP, `kill(-N, …)`, `wait4(-1, …, WNOHANG\|WSTOPPED)`, never WCONTINUED |
| s242's note | `[os.proc.wait.note]`: macOS sends no SIGCHLD for a continue, Linux does; `256 + N` is wolf's encoding, not PAX's (PAX gives Linux's: `(N << 8) \| 0x7f` stopped, `0xffff` continued) |
| a static dash | none packaged: Ubuntu 24.04 `dash 0.5.12-6ubuntu5`, Debian stable `dash 0.5.12-12`, Alpine 3.20 `dash-0.5.12-r2` are dynamic; `busybox-static` (Ubuntu 24.04, `1:1.36.1-6ubuntu3.1`) and `bash-static` (`5.2.21-2ubuntu4`) are `ELF 64-bit LSB executable, statically linked` (ET_EXEC, no PT_INTERP) |
| the harness | `tools/qemu-halt --type` and `tools/linux-tty` type `^C ^D ^U ^W ^\ ^? ^^` and no `^Z`; `notes/px46/vmtty.c` runs `/bin/pelt` only |
| open issues | pax#55, #56, #58, #60, #62, #63, #66, #67, #68, #70, #71 |
| kasumi | Linux 7.2.8-1-cachyos, `/home` 33 GB free, `px13-ubuntu` `ad8964505189` |

## 3. Prediction (committed before the first change and measurement)

**P1. One record, one rule each.** A process's group and session are
two words of its leader's thread record (kernel/sched), inherited by a
fork, kept by `execve` and by a thread; a third word says whether it has
`execve`d since its fork (for `setpgid`'s EACCES). The console keeps
which session holds it and its foreground group (kernel/console). A
stopped process is one more word of the leader's record, and a parked
thread one more thread state; the scheduler parks a stopped process's
thread when it is next dequeued or returns to ring 3. The stop and
continue reports are two more words. No second copy of `may_signal`;
group membership, "orphaned" and "background" are one function each.
**A process the kernel starts** (pid 1 and each run-list command) leads
a session and a group of its own, and **takes the console as its
controlling terminal when the console is started and no session holds
it**, with its group in the foreground: Linux's init has no terminal
and is in session 0 (px38's `ids`: `getsid(0)` 0), so this is named, the
state a getty or `setsid -c` gives a shell on Linux, and every existing
suite's processes (which make no groups) stay in the foreground group
and hear the keys as before. Falsified by a second copy or by an
existing suite's text moving for any reason but those named in P4.

**P2. Linux's answers** (s240's rows where they exist; the rest from
the man pages and POSIX; each measured again on real root's guest by
this lane's probe, as root and as 1000:1000, before the kernel is
written to them):

- *Groups and sessions.* `setsid` by a group leader (a session leader
  included): EPERM; by any other: a new session and group, its id the
  pid, no controlling terminal (`/dev/tty` ENXIO). `setpgid(0, 0)` by a
  session leader: EPERM; of a child into a group of another session or
  a group that does not exist: EPERM; of a child after its `execve`:
  EACCES; of a grandchild or a process that is not the caller's child:
  ESRCH; a negative pgid: EINVAL; of a child into its own new group and
  into a sibling's group: 0. `getpgid` and `getsid` of any process
  (another session's too): its group and session; of none: ESRCH;
  `getpgid(0)`, `getpgrp()`, `getsid(0)`: the caller's. A thread's
  answers are its process's. `/proc/<pid>/stat`'s fields 5 to 8
  (pgrp, session, tty_nr, tpgid) are the process's group and session,
  the terminal's number `(major << 8) | minor` when it has one (0
  otherwise) and the terminal's foreground group (-1 when none).
- *The controlling terminal.* A session leader with none that opens
  the terminal (no O_NOCTTY), when no session holds it, gets it, its
  group in the foreground. TIOCSCTTY: by a session leader with no
  terminal, on a terminal no session holds: 0; by a non-leader: EPERM;
  on another session's terminal: EPERM, unless privileged with arg 1
  (it is taken); on its own: 0. TIOCNOTTY on the caller's terminal by a
  non-leader: the process loses it, nothing is sent; by the leader: the
  foreground group gets SIGHUP and SIGCONT and the session loses it.
  TIOCGPGRP, TIOCSPGRP and TIOCGSID on a terminal that is not the
  caller's: ENOTTY. TIOCSPGRP: a negative group EINVAL, 0 or a group
  that does not exist ESRCH, another session's group EPERM; from a
  background group with SIGTTOU at its default the caller's group is
  stopped by SIGTTOU (not orphaned) or the call is refused (orphaned:
  s240 measured ENOTTY on a pty; on the console's guest I expect the
  same); with SIGTTOU ignored or blocked: 0.
- *Signals.* `kill(0, s)`: every member of the caller's group (the
  caller too); `kill(-g, s)`: every member of g, ESRCH when g has no
  member, a zombie a member until reaped (all zombies: 0), each by
  `may_signal` (none permitted: EPERM; some: 0, only they); SIGCONT
  within a session to anyone, to another session's process by the rule
  (EPERM for a user to root's); `kill(-1)` as px45 left it.
- *Stops and continues.* SIGSTOP, and SIGTSTP, SIGTTIN, SIGTTOU at
  their default, stop every thread of the process: it runs nothing
  until continued (a counter it increments does not move), its parent
  gets SIGCHLD with CLD_STOPPED and the signal (none under the parent's
  SA_NOCLDSTOP), and `wait4` with WUNTRACED (`waitid` with WSTOPPED)
  reports it once (`(sig << 8) | 0x7f`; CLD_STOPPED in waitid's
  siginfo). SIGCONT continues it however its action is set (blocked or
  ignored too), discards a pending stop, and the parent gets SIGCHLD
  with CLD_CONTINUED (none under SA_NOCLDSTOP) and WCONTINUED reports it
  once (`0xffff`; CLD_CONTINUED). A stop signal discards a pending
  SIGCONT. SIGKILL ends a stopped process. A stop that is blocked waits
  and stops the process when unblocked. SIGTSTP, SIGTTIN and SIGTTOU
  sent to a process of an orphaned group are discarded at their
  default; SIGSTOP still stops. A waiting call (a sleep, a read) is not
  ended by a stop and continue: a sleep keeps its deadline. pid 1 is
  never stopped (it takes only signals it handles). Waits select by
  `pid > 0`, `-1`, `0` (the caller's group) and `< -1` (that group);
  `waitid` P_PGID with 0 the caller's group; no such child: ECHILD.
- *The line discipline.* With ISIG, VINTR, VQUIT and VSUSP raise
  SIGINT, SIGQUIT and SIGTSTP for the console's foreground group only
  (nobody when no session holds it); a process of another group does
  not hear them. A background read of the controlling terminal sends
  SIGTTIN to the reader's group (which stops) and the read runs again
  when continued; with SIGTTIN ignored or blocked, or from an orphaned
  group: EIO. A background write: allowed without TOSTOP; with TOSTOP,
  SIGTTOU to the writer's group, and with SIGTTOU ignored or blocked
  the write proceeds; from an orphaned group: EIO. TCSETS from the
  background: as TIOCSPGRP (SIGTTOU unless ignored or blocked).
  TIOCSWINSZ that changes the size sends SIGWINCH to the foreground
  group.
- *Hangup.* A session leader's end with a controlling terminal: SIGHUP
  (and SIGCONT) to the terminal's foreground group, and the terminal
  belongs to no session after it. A process's end that orphans a
  process group with a stopped member: SIGHUP then SIGCONT to every
  member of that group (s240: both heard; their order not measured; I
  expect the handler of the later-numbered, CONT 18, to run first, as
  every pending signal is taken lowest first and laid highest on top,
  which is what s240's `M2:CONT,M2:HUP` shows).

**P3. The counts.**

- This lane's probe (`jobs`, user/elf/jobs.c), as root and as
  1000:1000 (through `as`), each section's lines byte-identical to real
  root's guest at the first boot of the kernel the measurement
  corrected, but for lines named before the boot; the terminal's rows
  on PAX's console against the guest's pseudo-terminal (the same line
  discipline rules; a pseudo-terminal's and the console's device
  numbers differ, so tty_nr is printed as "the terminal's number" or
  not).
- The typed shell session, as root (BusyBox `sh -i` as pid 1 on PAX)
  and as `pax` (through `as 1000 1000`), byte-identical to real root's
  guest (the shell on a pseudo-terminal, vmtty's way) and to the
  container, after pids are masked (`[1] <pid>`) and serial
  normalisation; the shell's job lines (`[1]+  Stopped`, `Running`,
  `Done`, `Terminated`) all there.
- `tests/mpx5-users`' `ids`: its five process-group lines move from
  -38 to answers. Linux's guest runs `ids` as a child of pid 1 in
  session 0 (`getpgrp` 0, `getsid` 0, `setpgid(0, 0)` 0, `setsid` the
  pid); on PAX `ids` is pid 1, a session leader by P1, so its lines are
  `getpgrp` 1, `getpgid(0)` 1, `getsid(0)` 1, `setpgid(0, 0)` -1
  (EPERM), `setsid` -1 (EPERM): they stay PAX's (named), and IDS_ENOSYS
  becomes `125 273 334`. `perm`'s two held rows (px44: the holder does
  not stop) become Linux's: `perm` 337 → 339 of 382. `sig` and `priv`
  keep their counts; their SIGSTOP refusal lines go.
- pax#66: a read with VMIN m > 0 and VTIME t > 0 waits for the first
  byte without a limit, then answers when m bytes are there or t tenths
  pass after the last byte; VMIN m > 0 with VTIME 0 answers when m are
  there (or the caller's count). pax#68: the window size is the device
  the person types at: decided in §F after measuring what pelt and the
  shell do with it; I expect the rule "0 rows 0 columns (a serial
  line's) unless set, whatever the screen", with `mpx3-screen` V6's
  screen row then set by TIOCSWINSZ, as on a Linux VT console nobody
  sized: wrong if `mpx3-screen` cannot keep its V6.

**P4. Existing suites.** Every existing suite passes as root and as a
user. Text moves only where named: the `refused: stopping a process`
lines (`mpx5-users`' PERM_REFUSED and its SIGSTOP holder), `ids`' five
lines and IDS_ENOSYS, `/proc/<pid>/status`'s `NSpgid` and `NSsid`
(where a suite prints them), and any suite whose shell leaves a
background job alive at its end (that job now hears SIGHUP when the
session leader ends, as on Linux's pseudo-terminal side). I expect none
of the last kind to move a compared transcript. Falsified by any other
move.

**P5. The soak.** `jobs soak 100000`, root and 1000:1000: a round is a
fork into a new group, a stop by `kill(-g, SIGSTOP)`, its WUNTRACED
report, a continue and its WCONTINUED report, a `tcsetpgrp` there and
back, a `kill(0, 0)`, and the child's end reaped: 0 wrong answers,
`MemFree` one number at each quarter, slots busy flat.

**P6. Plants**, each a CI run of its own with `mpx5-jobs` the only
suite: A, the line discipline raises its keys for every process again
(the foreground group ignored): red first in the probe's L section at
its first "not in the foreground, heard" row, and in the shell session
at `^Z` (the shell itself stops, or the background job does); B, a stop
does not park the process (the stop report sent but the process runs
on): red first in S at "a stopped process runs nothing".

**P7. What it costs.** Under 32 KiB of kernel text; the thread record
gains under ten words (it has room: 42 of its 64 words used); the console's state
gains under eight words; no table grows.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | the group, session, `execd` and stop words in the leader's record; the console's session and foreground group; one function each for membership, "orphaned" and "background"; a kernel-started process leads its session with the console (named) | so: `pgid`, `sid`, `ctty`, `execd`, `stopped`, `wstop`, `wcont` (§A, §C); `S_TTY_SID`, `S_TTY_PGRP`; `sched.member_after`, `orphaned_but`, `console.job`; `may_signal` the one rule still; the boot's session as §A says. Not predicted: an eighth word (`ssold`) for **`rt_sigsuspend`**, which the shell's `wait` needs (§D), and `/proc/<pid>/stat`, which P2 assumed and §2 had found missing | right (one call more than predicted) |
| P2 | Linux's answers (§3's list) | right but for: **a controlling process's end sends its foreground group SIGHUP only**, not "SIGHUP (and SIGCONT)" (`F:HUP`, §E); the tty is not hung up (not predicted either way); `/proc/<pid>/stat` of the reader's own process says R by `/proc/<pid>` too (the first PAX boot said S); a steal (TIOCSCTTY 1) sends the old foreground group SIGHUP and SIGCONT (not predicted); the orphaned group's handlers ran CONT first, as predicted | wrong (1) |
| P3 | `jobs` byte-identical as root and as 1000:1000 at the first boot of the kernel the measurement corrected; the shell sessions byte-identical; `ids` five lines PAX's (getpgrp 1 …, `setpgid(0, 0)` and `setsid` -1 EPERM), IDS_ENOSYS `125 273 334`; `perm` 337 → 339; `sig` and `priv` their counts; pax#66 as stated; pax#68 "0 by 0 whatever the screen" | `jobs`: the first boot (before §G's and §F's additions) differed in **2 lines** of 166 (the reader's own state by `/proc/<pid>`: S for R), fixed in `kernel/procfs`; the shell's first boot **hung at `wait`** (`rt_sigsuspend` -ENOSYS), fixed (§D); after both, every boot byte-identical. `ids`: it asks each call in a child, so `setpgid(0, 0)` is 0 (Linux's) and `setsid` a pid: **62** of 71 Linux's (predicted 61); IDS_ENOSYS as predicted; `perm` **339** as predicted; `sig` 99 of 102 sender rows as predicted, its 30 reader rows' `stat` field moved (§I); pax#66 as predicted; pax#68 decided otherwise (§F: the device typed at), since "0 by 0 whatever the screen" would have taken px19's screen size from `mpx3-screen` V6 | wrong (the first boots; ids; pax#68) |
| P4 | every existing suite green as root and as a user; text moves only where named | green where run (kasumi: `mpx5-users`, `mpx3-threads`, `mpx3-shell`, `mpx5-accounts`, `mpx3-screen`, `mpx3-speaker`; every suite in CI's pr and full tiers: the PR); text moved where named (`perm`'s held rows, its and `mpx3-threads`' SIGSTOP refusal lines, `ids`) and once where not: **`sig`'s reader rows**, which read `/proc/<pid>/stat` (-2 before, 0 now, Linux's 0) | wrong (one unnamed move) |
| P5 | `jobs soak 100000`, root and 1000:1000: 0 wrong, MemFree one number at each quarter | §H: on hasu under KVM, both tiers; CI's and kasumi's runs 3000 rounds | see §H |
| P6 | plant A red first in the probe's key rows (a process outside the foreground hears) and in the shell at ^Z; plant B red first in S at "a stopped group runs nothing" | A: red first at `T: ^C with the job in the foreground: heard J1:INT,J2:INT,R:INT` (R, in the background, heard it) and in both shells (^Z stopped the background `sleep 100`: `[1]- Stopped sleep 100`); B: red first at `S: a stopped group runs nothing: no`, then `SIGSTOP to it: it runs on yes` (§J) | right |
| P7 | under 32 KiB of text; under ten record words; under eight console words; no table grows | `.text` **+22,032 bytes** native (885,051 → 907,083) and **+54,208 release** (774,667 → 828,875: the release tier inlines the new walks over the slots); `.rodata` +56 and −160, `.data` +304 and 0, `.bss` the same 4,399,200 on both (the thread record has the room; `pax_sched_state` 128 → 256 bytes inside it); 8 record words; 2 console words (`C_LAST`, `C_SRC`) and 3 scheduler words (`notes/px48/kasumi-kernel-cost.txt`) | wrong (the release tier's text) |

## A. Groups and sessions (item 1)

`kernel/sched` keeps a process's group and session as two words of its
leader's record (`pgid`, `sid`), a fork's child taking its parent's, a
thread its process's, `execve` keeping them; a third word (`execd`) says
the process has exec'd since its fork. The five calls are
`kernel/process`'s (`setpgid` 109, `getpgrp` 111, `setsid` 112,
`getpgid` 121, `getsid` 124), each by one function of `kernel/sched`:

- `setsid`: -EPERM for a process that leads a group (a group with its
  pid as id exists: a session leader, or a group leader); otherwise the
  caller leads a new session and group, its id the pid, with no
  controlling terminal (`/dev/tty` -ENXIO, `tcgetpgrp(0)` -ENOTTY).
- `setpgid(pid, pgid)`: a negative pgid -EINVAL; the target is the
  caller or a child of it, else -ESRCH (a grandchild, the parent, a pid
  nobody has); a child that has exec'd -EACCES; a session leader, a
  target in another session, or a group that does not exist in the
  caller's session, -EPERM; pgid 0 is the target's pid.
- `getpgid`, `getsid`: any process, another session's too, a zombie
  until reaped; -ESRCH for none; 0 the caller.
- `/proc/<pid>/stat` and `/proc/self/stat` are new (`proc_pid_stat(5)`'s
  52 fields): the state (R for the reader's own process by either name,
  measured; Z ended, T stopped, S otherwise), the parent, the group and
  session, the terminal's number (the console's 4:64, `0x440`, when it is
  the process's controlling terminal; 0 otherwise) and its foreground
  group (-1 when none); what PAX does not keep reads 0, priority 20 and
  nice 0 (named). `/proc/<pid>/status` says `T (stopped)` for a stopped
  process and its own NSpgid and NSsid (1 and 1 before).

**The boot's session (named).** A process the kernel starts (pid 1, and
each command of a run list) leads a session and a group of its own and,
when the console is a terminal (kmain_console, kmain_session) and no
session holds it, takes the console as its controlling terminal with its
group in the foreground. Linux's init is in session 0 with no terminal
(px38's `ids`: `getsid(0)` 0); this is the state a getty or `setsid -c`
gives a shell there, the state every Linux side here has (the shell or
probe on a pseudo-terminal as its session leader), and the state that
keeps every existing suite's keys reaching its programs (they make no
groups, so they are all in pid 1's foreground group).

Measured (`G` of `jobs`, real root's guest and PAX, root and 1000:1000,
byte-identical): 29 lines, every one of the rules above, a thread's ids
its process's, the stat fields of the caller, a child and a new session.

## B. The controlling terminal and its ioctls (item 2)

The console's session and foreground group are two words of
`kernel/sched` (`S_TTY_SID`, `S_TTY_PGRP`); a process's controlling
terminal is the console when its leader's `ctty` word is 1 and its
session is the console's (a process that gave it up with TIOCNOTTY, or
one whose session lost it, has none). `kernel/console` answers:

| request | rule (measured on real root's guest, a pseudo-terminal) |
|---|---|
| TIOCSCTTY (0x540e) | a session leader with no controlling terminal takes a terminal no session holds: 0; again on its own: 0; a process that leads no session: -EPERM; another session's terminal: -EPERM, unless privileged with arg 1, which takes it (the old foreground group hears **SIGHUP and SIGCONT**, measured: `R:CONT,R:HUP`); a user's arg 1: -EPERM |
| TIOCNOTTY (0x5422) | not the caller's terminal: -ENOTTY; a session leader's: the session loses it and its foreground group hears SIGHUP and SIGCONT (`main:CONT,main:HUP`); anyone else's: that process alone loses it (its `tcgetpgrp` -ENOTTY after), nothing is sent |
| TIOCGPGRP (0x540f), TIOCGSID (0x5429) | -ENOTTY unless it is the caller's controlling terminal; then the foreground group, the session |
| TIOCSPGRP (0x5410) | -ENOTTY unless the caller's; the background rule first (§D: a background group with SIGTTOU at its default is stopped by SIGTTOU, and the call runs again when continued; an orphaned one -ENOTTY, measured: not -EIO); then a negative group -EINVAL, 0 or a group nobody has -ESRCH, another session's -EPERM |
| `/dev/tty` | -ENXIO to a process with no controlling terminal (it opened for anyone before: px45) |
| an open of the console | by a session leader with no controlling terminal, without O_NOCTTY, when no session holds it: it becomes its controlling terminal (inferred from XBD 11.1.3; the probe takes its terminal with TIOCSCTTY) |

`console.controlling` (px45's speaker rule) is the caller's own
controlling terminal now: a user whose session does not hold the
console is refused the speaker's ioctls (-EPERM) as on Linux.

Measured: `T` of `jobs`, its terminal rows, byte-identical as root and
as 1000:1000 (the steal row by rule: 0 and HUP+CONT to root, -EPERM to
a user, both measured).

## C. Stops, continues and the waits that report them (item 3)

A stop at its default (SIGSTOP always; SIGTSTP, SIGTTIN, SIGTTOU with
SIG_DFL) **stops the process when it is sent**, when some thread takes
it then (`sched.job_signal`); one that every thread blocks stays pending
and stops the process when a thread takes it (`signal.act` →
`sched.stop_self`). A stopped process is its leader's `stopped`; its
threads are **parked** (thread state STOPPED, the frame kept) when next
dequeued (`run_next`) or on their way to ring 3 (`signal.on_return` →
`park_current`), and a waiting thread stays in its wait (a sleep keeps
its deadline: measured, `nanosleep(900 ms)` stopped for 300 ms ends at
its deadline on both; a read keeps waiting and then reads its byte).
SIGCONT continues a stopped process whatever its action (blocked or
ignored too), readies its parked threads and discards a pending stop; a
stop discards a pending SIGCONT (measured: SIGTSTP pending, SIGCONT,
then unblocked: no stop); SIGKILL readies a stopped process so it ends.
SIGTSTP, SIGTTIN and SIGTTOU sent to a process of an **orphaned group**
are discarded (measured: it runs on); SIGSTOP stops it. pid 1 is never
stopped (it takes only signals it handles).

The parent is told: its waiting threads are woken, and it is sent
SIGCHLD with CLD_STOPPED or CLD_CONTINUED and the signal (si_status 19,
20, 21, 22 or 18) unless its SIGCHLD action has SA_NOCLDSTOP (measured
both ways). `wait4` reports a stop under WUNTRACED as `(sig << 8) | 0x7f`
and a continue under WCONTINUED as `0xffff`, each once; `waitid` under
WSTOPPED and WCONTINUED with CLD_STOPPED and CLD_CONTINUED, WNOWAIT
leaving the report; waitid without WEXITED is no longer -EINVAL when
WSTOPPED or WCONTINUED is asked. Waits select by pid, -1, 0 (the caller's
group) and -pgid; waitid's P_PGID with 0 is the caller's group; no child
in the selection is -ECHILD (measured: waitpid(0) with no child in the
caller's group, waitpid(-999999)).

The origin word of a pending signal widens its kind to four bits (two
new kinds) and narrows its pid to twenty bits (a pid above 1,048,575 is
carried modulo that: named).

Measured: `S` of `jobs`, 43 lines, byte-identical as root and as
1000:1000; the soak (§H).

## D. The console's signals, and the background rules (item 4)

With ISIG, VINTR, VQUIT and VSUSP raise SIGINT, SIGQUIT and SIGTSTP for
the console's **foreground group** only (`signal.tty` → `sched.raise_pgrp`),
nobody when no session holds the console; measured with the keys typed
on COM1 and on the PS/2 keyboard (`probe` and `probe-ps2`): a job in the
foreground with handlers hears all three, a job at its default is
stopped by ^Z and ended by ^C, and the processes that are not in the
foreground (R, the other job) hear nothing.

`console.job` is the background rule (XBD 11.1.4, termios(3)'s TOSTOP),
for a process whose controlling terminal the console is and which is
not in its foreground group:

| what | SIGTTIN/SIGTTOU at its default | ignored or blocked | from an orphaned group |
|---|---|---|---|
| a read | the group is sent SIGTTIN (stopped); when continued the read runs again, and stops again while it is still in the background (measured) | -EIO | -EIO |
| a write, TOSTOP clear | written | written | written |
| a write, TOSTOP set | the group is sent SIGTTOU (stopped), and again when continued | written | -EIO |
| `tcsetattr` (TCSETS*) | SIGTTOU, as above | 0 | -EIO (inferred: not measured) |
| `tcsetpgrp` (TIOCSPGRP) | SIGTTOU, as above | 0 | -ENOTTY (measured) |

A call the rule stops answers `console.JOB_STOP`: kernel/user rewinds it
to run again, parked with its process, and a handler for the signal ends
it as a waiting call (SA_RESTART runs it again, else -EINTR:
`sched.self_rewound`). TIOCSWINSZ with a new size sends SIGWINCH to the
foreground group (measured: the same size again sends nothing).

`rt_sigsuspend` (130) is new: BusyBox's `wait` waits in it (it was
-ENOSYS: this lane's first boot of the shell on kasumi logged `syscall
130: -ENOSYS` and the shell's `wait` never returned, SIGCHLD blocked for
good; that log was not kept). A handler run from it restores the mask it
replaced at `rt_sigreturn`; a thread let go without one gets it back on
its way out. `pause` (34) stays -ENOSYS (not asked by anything here).

Measured: `T`'s background and key rows, byte-identical as root and as
1000:1000, and the shell sessions (§G).

## E. Hangup and the orphaned group (item 5)

A **controlling process's end** (a session leader holding the console)
sends the console's foreground group SIGHUP — measured on the guest:
SIGHUP only, no SIGCONT (`F:HUP`) — and frees the console (no session
holds it, every member's `ctty` cleared). The terminal itself is not hung
up: a member's nonblocking read after it is -EAGAIN and its write
succeeds (measured: Linux's pseudo-terminal does not hang up its open
files on a controlling process's exit either), and its `tcgetpgrp` is
-ENOTTY. A process's end that **orphans a process group with a stopped
member** — its own group, or a child's (`process_ends` takes each
group's state before the end and after the reparenting) — sends every
member SIGHUP, then SIGCONT (measured: `G:CONT,G:HUP`, the CONT handler
run first, as every pending signal is laid lowest-numbered first).

Measured: `H` of `jobs`, 4 lines, byte-identical as root and as
1000:1000.

## F. pax#66 and pax#68 (item 6)

**pax#66, VTIME with VMIN above 0.** A non-canonical read with VMIN m
above 0 now waits for min(m, the caller's count) bytes (it answered
whatever was ready, one byte, before); with VTIME t above 0 it waits for
the first byte without a limit and then answers what it has once t
tenths of a second pass after the last byte came (`C_LAST`, the tick
each byte is queued at). Measured (`V` of `jobs`, the keys typed with a
pause between them): VMIN 2 VTIME 0, one key and a second 1.5 s later:
`read 2 bytes "xy"`; VMIN 5 VTIME 5, two keys: `read 2 bytes "ab"` after
the timer; VMIN 5 VTIME 5 with nothing for 1.5 s: `read 1 bytes "q"`
(no timer before the first byte). Linux's guest and PAX the same.

**pax#68, the window's size with a display.** PAX's one console is a
serial line and, with a display, a screen at once; Linux would have two
terminals (ttyS0, 0 rows 0 columns until someone sets it, and a virtual
terminal, its screen's grid). Decided: **the size follows the device a
person types at** (`console.typed_at`): when input comes from a device
other than the last input's, the size becomes that device's — a serial
line's 0 by 0 after a byte from COM1, the screen's grid after a key of
the PS/2 keyboard; before any input it is the screen's grid when there
is a screen (px19's, unchanged: `mpx3-screen` V6's `ask` asks before any
key). A size a program sets holds until the person moves to the other
device. No SIGWINCH is sent for the move (named: nothing here redraws
for it). Measured: the probe's `V: TIOCGWINSZ after the keys` is
`0 rows 0 cols` typed on COM1 with a display (Linux's pseudo-terminal's
answer; 160 columns before), and the screen's grid typed on the PS/2
keyboard (held by rule in `mpx5-jobs` J1). So a typed session on COM1
no longer needs its lines under 80 for PAX's sake once it has typed.

## G. The witness: a job-control session in BusyBox's ash (item 7)

`user/console/jobs-shell.keys`, typed at `sh -i` (Ubuntu 24.04's static
busybox, `tools/fetch-busybox`, by the .deb's and the binary's digests):
`sleep 100 &`, `jobs`, `/bin/sleep 50` stopped by ^Z (`[2]+ Stopped`),
`jobs`, `bg; sleep 1`, `jobs`, `fg %1` ended by ^C, `jobs`, `kill %2;
wait` (`[2]+ Terminated`), `jobs`, `sleep 2 & wait` (`[1]+ Done`),
`jobs`, `exit`. As root (`shell`, pid 1 on PAX, prompt `~ # `) and as
`pax` (`shell-user`, through `as 1000 1000`, prompt `~ $ `): 30 lines
each, **byte-identical** to real root's guest (the shell on a
pseudo-terminal as its session leader) and, the user's, to the
container's.

Two things the session is shaped around, each a Linux race and not a
rule: busybox's `sleep` is an applet the shell runs in its own process
(`sleep 50` in the foreground is no job: ^Z reaches nobody stoppable;
`/bin/sleep 50` is a child); and a continue's or an end's SIGCHLD that
reaches the shell while it waits at its prompt redraws the prompt
(seen in the container: one extra prompt after `bg`, and the keys after
it typed one prompt early), so `bg` and `kill` are followed by a
command on the same line (`bg; sleep 1`, `kill %2; wait`). On PAX a
continue is told to the parent when it is sent, so PAX never showed the
extra prompt; the guest's one CPU did not either.

## H. The suite, its soak, and CI (item 8)

`tests/mpx5-jobs` (J0 to J6, the script's comment): three images of
kmain_console — `probe` (the probe as root, then as 1000:1000, then the
soak as root and as 1000:1000; keys on COM1, and again on the PS/2
keyboard), `shell` and `shell-user` — each typed transcript held to real
root's recordings (`tests/mpx5-jobs.d/linux/`, `vm-*.meta`: kasumi's
`f4c00d5d…` under QEMU 11.1.1, `notes/px48/vmjob.c` as pid 1), the
user's also to a container's run live (`tools/linux-tree --rdev
--nsproc`), each run's own witness (who it runs as, the foreground
group's keys, the job lines), the soak's 0 wrong and flat MemFree, and
no -ENOSYS but 273 and 334 and nothing refused by name.

CI: a job `mpx5-jobs` in `.github/workflows/ci.yml`; `tools/ci-tiers.map`
puts it among `@user`, `@console` and `@asuser` and `tools/mkas`'s
readers; `tests/ci-plan` holds that its own files reach it (four new P2
cases). Its new paths are its own by the derivation.

**Harness findings.** `tools/linux-tty --root --pid1` mounted `/proc`
from the namespace it runs in, not the program's: `/proc/<pid>` of a pid
the program sees was another process (the probe's stat rows read nothing
in the container); `--nsproc` (and `tools/linux-tree --nsproc`) mounts it
from the program's own pid namespace. The container's `/dev/tty` needs
`--rdev` (px47's rootless-bind finding, for `/dev/tty` this time: EACCES
without it). `tools/qemu-halt` and `tools/linux-tty` type `^Z` now.

## I. Every existing suite, and what moved (P4)

Text moved only where §3 named it, and three suites' expectations moved
with it:

- `tests/mpx5-users`: `perm`'s two held rows are Linux's now that the
  holder stops (`perm.pax`; 337 → **339** of 382 lines; its three `!
  the holder did not stop` lines and PERM_REFUSED's SIGSTOP refusal
  gone); `ids` answers the five group calls (`ids.pax`, IDS_ENOSYS `125
  273 334`; `setpgid(0, 0)` by its child is Linux's 0: 61 → **62** of
  71; `getpgrp`, `getpgid`, `getsid` read 1 on PAX, whose pid 1 leads
  session 1, and 0 on Linux, whose init is in session 0; `setsid` a
  child's pid); `sig`'s 30 reader rows find `/proc/<pid>/stat` (`stat 0`
  for `-2`, Linux's field: `sig.pax`), its sender rows unchanged (99 of
  102).
- `tests/mpx3-threads`: the probe's `~stop` child is in an orphaned group
  (the probe is pid 1, alone in its group) and its SIGTSTP is discarded —
  on Linux's side too (`0x300`, both) — so T3 no longer expects px26's
  refusal line.
- Not moved: the typed sessions (pelt makes no groups; its keys reach its
  group, the foreground), `mpx3-screen` V6, the speaker's sessions,
  `mpx5-accounts`, `mpx3-shell`.

## J. Plants (P6)

Each a branch never to be merged, cut from `f660b32` (the code and the
tests as at the head but the note), one commit, run in CI by dispatch
with `mpx5-jobs` the only suite; see §4 for the runs.

| plant | branch, commit | break |
|---|---|---|
| A | `px48-plant-a` `bf939d8` | the console's keys raised for every process (the foreground group ignored) |
| B | `px48-plant-b` `4ff0135` | a stopped process parks nothing (it is reported stopped and runs on) |

## K. What U9 (`login` makes a session) needs next (item 9)

`login` is left out (the contract). What it can rely on now, and what it
still needs:

- **A session to make.** `login` run by root on the console (pid 1's
  session holds it) forks, and its child calls `setsid` and then takes
  the console with **TIOCSCTTY(1)** — a privileged steal, which PAX does
  as Linux does (the old session's foreground group hears SIGHUP and
  SIGCONT, so pid 1 must ignore SIGHUP or be the one that gave the
  console up with TIOCNOTTY first, as the probe's `main` does) — or pid 1
  gives it up and the child takes it with arg 0. Either works on PAX
  today.
- **The terminal's owner.** Linux's `login` gives the terminal to the
  user (`fchown`/`fchmod` of the tty); PAX's `/dev` refuses an owner
  (px42's `~fixed`, -EROFS). U9 needs the console to take an owner and a
  mode that `open` then asks (px45's checks), or a ruling that it stays
  root's 0600 with descriptors 0-2 inherited (px45's note: as `su` on
  root's VT).
- **The hangup.** When the user's shell (the new session's leader) ends,
  its foreground group hears SIGHUP and the console is free again; pid 1
  must take it back (TIOCSCTTY) before it reads, or its reads are a
  terminal's that is nobody's controlling terminal (allowed: no
  background rule applies).
- **`utmp` and `lastlog`, `getlogin`.** None: `logname` stays out of the
  sessions (px46); `/var/run/utmp` is U9's to rule on.
- **pelt's own job control** (sh-lanes, H3e) can run on PAX's console
  now: everything BusyBox's ash asked here is answered as Linux answers
  it.

## 4. Evidence index

Shas are this branch's (`px48`). kasumi paths are under `~/lanes/px48/`;
hasu's likewise.

### What was written

- The prediction: `f24b113` (§1 to §3, before any change or measurement).
- The harness: `3975712` (`tools/qemu-halt` types `^Z`), `4caca20`
  (`tools/linux-tty` the same), `bdba835`, `f33a8d7` (`--nsproc`),
  `2de9d31` (`tools/fetch-busybox`, `user/busybox.pin`), `8f3a7f0`
  (`tools/mkjobs`), `bb081f1` (`notes/px48/vmjob.c`, `linux-vm.sh`).
- The probe and its keys: `206b9ee`, `93089d5`, `a58f347`, `fc6bbb9`,
  `7008f06` (`user/elf/jobs.c`, `user/console/jobs.keys`); the shell's
  keys: `93089d5`, `7dced78` (`user/console/jobs-shell.keys`).
- The kernel: `908dcb5` (`boot/sched.S`), `c19e160` (`kernel/sched`),
  `3a460f5` (`kernel/signal`), `d72a2b5` (`kernel/process`), `d09e9a9`,
  `1a0c93b` (`kernel/console`: pax#66, pax#68), `e3d257c`
  (`kernel/files`), `471b1b9` (`kernel/procfs`), `d5913d9`
  (`kernel/user`).
- The suite: `a20d3ca`, `bea058d`, `f660b32` (`tests/mpx5-jobs`),
  `842dd18`, `92432f8` (`tests/mpx5-jobs.d/linux/`, real root's
  recordings); CI: `6e770fc`, `e5d4c51`, `cd9e9cc`.
- The other suites' expectations: `d5d540b`, `ebbbfb2`
  (`tests/mpx5-users`, `perm.pax`, `ids.pax`, `sig.pax`), `11aa55c`
  (`tests/mpx3-threads`, `user/elf/threads.c`'s comment).
- The words: `f7d7c99` (`kernel/README.md`), `928c5d2`
  (`docs/SOURCES.md`), `f7aad22` (README), `26cc04b` (CHANGELOG).

### What was measured, and where it is

- **Real root's Linux** (kasumi's 7.2.8-1-cachyos `f4c00d5d…` under QEMU
  11.1.1, `notes/px48/vmjob.c` `9820d265…` as pid 1, the suite's own
  archives): `tests/mpx5-jobs.d/linux/probe.tty`, `probe-user.tty`,
  `shell.tty`, `shell-user.tty` and their `vm-*.meta`. The shell's two
  recordings were made twice with the same keys (rec3 and rec4) and are
  the same bytes (`eeb8988b…`, `3dca2d6d…`).
- **PAX at trunk `5c36560`**, the probe's image on trunk's kernel:
  `notes/px48/pax-5c36560-probe.session` (55 lines, 9 of them the
  recording's; then no stop, so `waitpid(-G, WUNTRACED)` waits for good)
  and its verdict `pax-5c36560-probe.verdict` (`NOT HALTED: prompt 1 …
  did not come within 300s`).
- **PAX, the branch** (kasumi, TCG, native BIOS, the kernel at
  `f660b32`'s code): `notes/px48/kasumi-mpx5-jobs-f660b32.out` (every J
  PASS), the same images under `taskset -c 0-3`:
  `kasumi-taskset-0-3-mpx5-jobs-f660b32.out` (every J PASS);
  `kasumi-mpx5-users-f660b32.out`, `kasumi-mpx3-threads-f660b32.out`,
  `kasumi-mpx3-shell-f660b32.out`, `kasumi-mpx5-accounts-f660b32.out`,
  `kasumi-mpx3-screen-f660b32.out`, `kasumi-mpx3-speaker-f660b32.out`,
  `kasumi-mpx3-console-f660b32.out`, `kasumi-mpx3-tree-f660b32.out`
  (`mpx4-session` and `mpx4-lobo` need a container engine on the host
  for their Linux sides, which this lane's kasumi wrapper builds inside
  one: CI's runs only).
- **hasu, KVM** (BIOS, native and release, `PAX_JOBS_SOAK=100000`, the
  images built on kasumi): `notes/px48/hasu-kvm-mpx5-jobs-f660b32.out`.
- **The kernel's cost**: `notes/px48/kasumi-kernel-cost.txt`.
- **The plants on kasumi**: `notes/px48/kasumi-plant-a-bf939d8.out`,
  `kasumi-plant-b-4ff0135.out`; in CI: §J and the pull request.
- **CI**: named in the pull request (a commit naming the head's runs
  would move the head).

### A slip

One command of this lane wrote an 8,813-byte scratch file to kasumi's
`/tmp` (a mistyped redirect while counting the trunk probe's lines,
§1 forbids `/tmp`); it was removed at once and nothing read it.

### Measured, inferred, not verified

**Measured**: everything in §A to §I but what follows.

**Inferred**:
- An open of the console (not `/dev/tty`) by a session leader with no
  controlling terminal takes it (XBD 11.1.3; Linux's guest was not asked:
  the probe takes its terminal with TIOCSCTTY, and opens `/dev/tty`).
- `tcsetattr` from an orphaned background group answers -EIO (not asked;
  `tcsetpgrp`'s -ENOTTY was).
- A stop that reaches a thread waiting in `rt_sigsuspend` ends the wait
  (-EINTR) where Linux keeps it waiting; nothing here asks it.
- A process-directed signal taken by another thread while a thread waits
  in `rt_sigsuspend` lets that thread go with -EINTR (Linux would keep it
  waiting); single-threaded programs here only.

**Not verified**:
- Real root was one kernel build (kasumi's CachyOS 7.2.8) and one
  terminal kind (a pseudo-terminal in the guest); PAX's console is a
  serial line and a screen. The guest's own serial console as a
  controlling terminal was not measured.
- The witness is BusyBox's ash, not dash (none is packaged static); bash
  (`bash-static` is packaged) was not run.
- UEFI under KVM on hasu (pax#56): BIOS only there; UEFI on kasumi's
  TCG and in CI's full tier.
- More than one CPU (PAX runs one); the soak's rounds on more than one
  core.
- pelt's own job control (it makes no groups yet).

### Issues

- **To close at merge**: pax#66, pax#68 (the PR says so; GitHub's
  `closes` phrasing is the orchestrator's to use).
- **Would file (none filed)**:
  1. pax: `pause` (34) is -ENOSYS (px45's list had it; still so).
  2. pax: TIOCSTI, TCFLSH, TCSBRK (`tcflush`, `tcdrain`) on the console
     are refused by name; nothing here asks them.
  3. pax: `rt_sigsuspend` is ended by a stop or by another thread taking
     the signal (inferred above); Linux keeps waiting.
  4. pax: the background rules do not apply to a console written by
     `sendfile` or `splice`.
  5. pax: a controlling process's end does not hang up the console's open
     files (Linux's pseudo-terminal does not either: measured; a serial
     line's was not measured).
- Not chased, did not occur in this lane's runs: pax#55, #56, #58, #60,
  #62, #63, #67, #70, #71.

## 5. Done-when

- Branch `px48` on origin; pax PR #72, open, unmerged.
- The five sections §1 to §5; the items §A to §K.
- The test checklist:
  - [x] `tests/mpx5-jobs`, native BIOS on kasumi (TCG), and under
        `taskset -c 0-3`
  - [x] the same on hasu under KVM, native and release, BIOS, with a
        100,000-round soak as root and as 1000:1000
  - [x] `tests/mpx5-users`, `mpx3-threads`, `mpx3-shell`,
        `mpx5-accounts`, `mpx3-screen`, `mpx3-speaker`, `mpx3-console`,
        `mpx3-tree` on kasumi
  - [x] `tests/ci-plan`, every case, four of them new
  - [x] plants A and B red on kasumi; in CI: the pull request
  - [ ] the pr tier at the final head, and `tier full`: named in the PR
- `wolf/tools/lane-audit.sh pax px48 72` exit status: named in the PR.
- Trees: kasumi `~/lanes/px48/` keeps `out/`, `vm/rec4`, `bin/`,
  `keep/`; build directories removed at the end. hasu `~/lanes/px48/`
  keeps `out/`. Plant branches stay on origin, never to be merged.
