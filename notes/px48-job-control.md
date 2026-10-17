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
