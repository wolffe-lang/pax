# px45 — The processes (P5 lane U5: who may signal whom, and what only root may do)

Contract: px45's, `sprints/pax/45-the-processes/` in wolffe-lang/wolf
(planning commit `4f28ece`, read 2026-10-14), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/crawl-54.md` and `sprints/wave-53.md` down to
`wave-45.md`. Branch `px45` in pax, cut from pax trunk `2167620`. §1 to
§3 are committed before the first change to the kernel, a tool, a probe
or a test.

One deliverable, the fifth and last kernel-rule lane before the
accounts (U6): **who may signal whom** (`kill`, `tgkill`, `tkill`, and
the signal a dead child's parent gets, by the sender's real and
effective ids against the target's real and saved ids; SIGCONT within
the session); **what only root may do**, each refused to a user as
Linux refuses it (a port below 1024, the speaker's ioctls and the sound
card's where Linux gates them, `/dev` nodes with real modes and owners
that `open` checks through `may`, `setpriority` and
`sched_setscheduler` raising priority, `chroot`, `reboot`, mounting);
**`/proc/<pid>` by owner** (`status`, `cmdline`, `environ`, `fd/`, by
the dumpable rule px39 measured); **`SO_PEERCRED`** on AF_UNIX sockets.
Root for signals and privilege is effective user id 0; root for files
stays file-system user id 0 (R9).

**What this lane does not do.** Job control, sessions and process-group
signals (a separate track, ruling #79: PAX keeps its one session and
one group, so `kill(0, …)` and a negative group still mean every
process, now each one by the rule); passwords and set-ID execution (R1,
R5: a set-ID file still runs with the runner's ids); accounts, `su` and
`login` (U6); the loader limit (px27: PAX runs only the archive's own
bytes); capabilities (out of the campaign: root is effective user id 0
and nothing finer); limits and quotas (out of the campaign:
`prlimit64` stays as it is). The ruled claim is R6's: the checks are
**enforced for honest programs; not a boundary against an attacker**.

## 1. Forbidden, absolutely

- No kernel's, libc's, file system's or ALSA's source is read, nor that
  of `su`, `login`, shadow-utils, util-linux or coreutils (ruling #22).
  Facts come from the man pages (`kill(2)`, `tgkill(2)`, `signal(7)`,
  `sigaction(2)`'s siginfo, `credentials(7)`, `wait(2)`, `bind(2)`,
  `ip(7)`, `raw(7)`, `setpriority(2)`, `sched_setscheduler(2)`,
  `sched(7)`, `chroot(2)`, `reboot(2)`, `mount(2)`, `sethostname(2)`,
  `settimeofday(2)`, `clock_settime(2)`, `mknod(2)`, `ioctl_console(2)`
  and `KIOCSOUND(2const)`, `KDMKTONE(2const)`, `console(4)`, `null(4)`,
  `random(4)`, `tty(4)`, `proc(5)`, `proc_pid_cmdline(5)`,
  `proc_pid_environ(5)`, `proc_pid_fd(5)`, `ptrace(2)`'s access mode,
  `PR_SET_DUMPABLE(2const)`, `unix(7)`, `socket(7)`'s SO_PEERCRED),
  POSIX.1-2024 (XSH `kill()`, XBD 4.5), the uapi headers the refs
  clone's sparse checkout holds, the OSS programmer's guide, pax's own
  source, and px38's to px44's recorded Linux answers.
- A Linux answer nobody recorded is measured black-box as px38 and px44
  measured: real root is kasumi's own kernel image booted under QEMU
  with a static program as pid 1 and the four protected settings
  written to 1 (**vm-protected**, R7); a rootless container is never a
  reference for what root may do, and is not used for root's rows. The
  sound card's answers come from the same kernel and its own modules
  under QEMU with the device PAX drives (`tools/linux-sound`, px30's
  way), run, never read. Each compared row names its reference. Where
  Linux has no equivalent, the note says so and invents no rule.
- No account is made on any host; no `sudo`. A test becomes a user
  through `user/elf/as.c`, or a probe drops to its actors itself.
  Signals in tests go only to processes the test itself started inside
  PAX or inside the Linux guest: never to a host process.
- Refusal cases are built into the image with owners and modes
  (`tools/mkinitramfs` `:MODE:UID:GID`), never by `chown` at run time.
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's
  own glibc.
- Set-ID execution is not honoured; the loader limit is not lifted; no
  job control. Nothing calls PAX secure. No word implying filming.
- No build on nomad-1. kasumi and hasu: commands under `bash`, long
  jobs under `setsid` with a pid file and ended by that pid only; work
  under `~/lanes/px45/`, pruned as I go; never `/tmp`. Host ports 8080
  and 8088 are not used. Nothing is installed anywhere. hasu's
  llama-server (port 9308) is not touched.
- No `rm` outside `~/lanes/px45/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled.
- "Seen red" cites a run. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-14)

| input | found |
|---|---|
| pax trunk | `2167620` (px44 merged), the contract's; `origin/trunk` the same at the start |
| planning repo | `4f28ece`: the contract, the campaign file with R1 to R9, crawl 54 |
| the kernel's pin | wolf 0.2.28 / lupin 0.1.51 (`kernel/wolf.pin`), unchanged |
| the rules to call | `kernel/files`' `may(a, who, n, want)` (the class rule), `owns`, `member`/`member_as`; `kernel/cred`'s `uid`, `gid`, `in_list`, `dumpable`; cred's `privileged` (effective user id 0) is private to the id calls |
| who may signal today | anyone may signal anyone: `kernel/signal`'s `kill`, `tgkill`, `tkill` ask no id; `kill(-1)` and `kill(0)` reach every process; siginfo's `si_uid` is 0 for every signal (`signal.lu`'s frame comment says so); `kill` of a zombie is -ESRCH (`sched.raise_pid` finds live processes only), where `/proc/<pid>` still shows it |
| what only root may do today | nothing: `bind` takes any port from anyone; `KIOCSOUND`/`KDMKTONE` answer anyone's console descriptor; `socket(AF_INET, SOCK_RAW)` is refused by name for everyone (-ESOCKTNOSUPPORT); `mknod` refused by name for everyone (-EPERM); `setpriority` (141), `chroot` (161), `settimeofday` (164), `mount` (165), `umount2` (166), `reboot` (169), `sethostname` (170), `clock_settime` (227) and the `sched_*` calls are -ENOSYS for everyone |
| `/dev` | synthetic, fixed: `null` 1:3 0666, `console` 5:1 and `tty0` 4:0 0620, `stdin`/`stdout`/`stderr` (what descriptor 0, 1, 2 is), `dsp` (px30); no `zero`, `full`, `random`, `urandom`, `tty`, `ttyS0`; none checked on `open` or `access` (px44's "what U5 should know": `openat`'s `named` test is `ty(n) == T_INO`); everything root's |
| `/proc/<pid>` | `status` and `setgroups` only (px25, px39), owned by px42's rule; no `cmdline`, `environ`, `fd/`; `/proc/self/exe` the one link |
| `SO_PEERCRED` | refused by name for an AF_UNIX socketpair's end (-EOPNOTSUPP; `tests/mpx5-users.d/ids.pax`); path sockets the same |
| `sig` (px38's probe, byte for byte: `d84c3243…`) as the first program on trunk | **33 of its 102 sender rows** Linux's (`notes/px45/pax-2167620-sig.txt` against px38's vm-protected `sig` section, which is its vm section to the byte): the 69 others are a user's signals PAX lets through (52) and the 17 rows of the target that runs a set-ID copy, which does not settle on PAX (its copy is written since boot: px27) and is a zombie, -ESRCH to every `kill` |
| `priv` (px38's, `a3a24d21…`) as the first program on trunk | **4 of its 30 lines** Linux's (`notes/px45/pax-2167620-priv.txt`) |
| `tests/mpx5-users` | 19 sessions; `ids` 60 of 71 (its `SO_PEERCRED` line one of the 11 PAX's) |
| `tools/ci-tiers.map` | `kernel/signal`, `kernel/cred`, `kernel/files`, `kernel/procfs`, `kernel/user`, `kernel/process`, `kernel/console` are `@user`'s (19 suites, `mpx5-users` among them); `kernel/socket`, `kernel/tcp`, `kernel/udp`, `kernel/unix` `@net`'s; `kernel/speaker`, `kernel/sound` `@music`'s; `kernel/sched` is core (every suite) |
| pax#58 | open: `fstat`'s owner is 0:0 for AF_INET sockets, eventfd, epoll and accepted ends ("if in reach") |
| pax#62 | open: `mpx3-threads` T1's `tgkill` of a just-joined thread races on the Linux reference (the probe asks before Linux retires the tid) |
| kasumi | Linux 7.2.8-1-cachyos (`vmlinuz` `f4c00d5d…`, the image px38 recorded with), 16 cpus, QEMU 11.1.1, `px13-ubuntu`, `/home` 36 GB free (97%) |

The trunk boots were made with a scratch script on kasumi
(`~/lanes/px45/job-boot.sh`: an image of `/bin/<probe>`, `/bin/as`,
`/etc/passwd`, `/etc/group`, `/t/` and `/t/<probe>/` 0777, the probe run
as `/bin/<probe> /t/<probe>`; `kmain_console`, native, BIOS, TCG).

## 3. Prediction (committed before the first change)

**P1. One rule for signals, one test for privilege, both called.** A
signal from a process to another is allowed when the sender's
effective user id is 0, or its real or effective user id is the
target's real or saved user id, or the signal is SIGCONT (PAX has one
session); else -EPERM — one function in `kernel/signal`, asked by
`kill`, `tgkill` and `tkill` and by each process `kill(-1)` and
`kill(0)` reach. A signal the kernel raises (a child's end, the
terminal's keys, SIGPIPE, a fault) asks nothing. What only root may do
asks one public test in `kernel/cred` (effective user id 0); files keep
file-system user id 0 through `may` and `owns`. Falsified if a second
copy of either is needed.

**P2. Linux's answers where nobody recorded them** (measured on
vm-protected by this lane's probe, as root dropping to px38's sender
states and to chosen readers, and again as 1000:1000 through `as`). I
expect:

- *Signals.* The 102 rows px38 recorded, from the same rule, for
  `tkill` too and for a target in the state a set-ID run leaves
  (`setresuid(1000, 1001, 1001)` then `execve`), which PAX can make
  without honouring a bit. A zombie is signalled by the same rule
  (0 or -EPERM, never -ESRCH: `kill(2)`'s ERRORS says an existing
  process may be a zombie), and `tgkill` of a zombie leader is -ESRCH.
  `tgkill` naming a thread not in the group: -ESRCH, before any
  permission. `kill(-1, sig)` by a user: 0 when some process other than
  pid 1 and the caller exists, whether or not it was permitted (px38's
  (1003 1003 1003) row reads 0 with no permitted target), -ESRCH when
  none; only the permitted are signalled. `kill(0, sig)`: 0 (the
  caller's own group holds the caller). siginfo's `si_uid` is the
  sender's real user id for `kill`, `tgkill`, `tkill`; SIGCHLD reaches
  a parent whatever either's ids, its `si_uid` the child's real user
  id.
- *Ports.* `bind` of a TCP or UDP port below 1024 by a caller whose
  effective user id is not 0: -EACCES, also when the port is taken
  (asked first); port 0 and 1024 and up: anyone's;
  `/proc/sys/net/ipv4/ip_unprivileged_port_start` reads `1024`, 0644,
  root's. A raw socket: -EPERM for a user (asked before the type is
  refused).
- *Priority.* `setpriority(PRIO_PROCESS)`: anyone may raise its nice
  value (lower its priority); lowering it below the current one is
  -EACCES unless effective user id 0; another process's: -EPERM unless
  the caller's effective user id is the target's real or effective id,
  or 0; `getpriority` answers 20 minus the nice value.
  `sched_setscheduler(SCHED_FIFO or SCHED_RR)`: -EPERM for a user, 0 for
  root; SCHED_OTHER with priority 0: anyone's for itself.
- *Root's calls.* `chroot`, `reboot`, `sethostname`, `settimeofday`,
  `clock_settime`, `mount`, `umount2`, `mknod` of a device: -EPERM for
  a user, asked before the arguments (a bad `reboot` magic, a missing
  `chroot` directory: still -EPERM).
- *The speaker.* `KIOCSOUND` and `KDMKTONE` on a virtual terminal root
  opened and the user inherited: -EPERM (px38); on the caller's own
  controlling terminal: 0 for anyone (to be measured; if so, the rule
  is "privileged, or the terminal is yours").
- *`/dev`* on devtmpfs (no udev): `null`, `zero`, `full`, `random`,
  `urandom`, `tty` 0666; `console`, `tty0`, `ttyS0` 0600; all 0:0 (px38's
  rows); a user's `open` of a 0600 node -EACCES, by the class rule.
  `/dev/dsp` (virtio-snd with the OSS emulation) 0600 root's on
  devtmpfs, so a user's `open` is -EACCES; the OSS ioctls on a
  descriptor root opened are not gated (0).
- *`/proc/<pid>`* (px38's 30 rows): the directory the target's
  effective ids, 0555; `status` and `cmdline` anyone's; `environ` (0400)
  and `fd/` (0500) the target's effective ids while it is dumpable,
  0:0 when not; read only by effective user id 0, or by a reader whose
  file-system ids equal all three of the target's user and group ids
  while it is dumpable (`ptrace(2)`'s access mode); else -EACCES.
- *`SO_PEERCRED`* (`struct ucred`: pid, uid, gid): a socketpair's ends
  both answer the maker's pid and effective ids; a connected path
  socket answers the listener's ids as they were at `listen`, the
  accepted end the connector's at `connect`; an unconnected socket
  pid 0 and uid and gid -1; a length under 12: the first bytes
  (truncated), no error.

**P3. The counts.**

- `sig` (px38's probe, byte for byte, as the first program): **99 of
  102** sender rows Linux's (from 33). The three left are the set-ID
  target's rows whose sender matches only 1001, the copy's owner
  (`(1001 1001 1001)`, `(1003 1001 1003)`, `(1001 1003 1003)`): the copy
  does not run (px27) and would not raise an id (R5), so that target is
  a zombie of (1000 1000 1000). Its `kill(1, 0)`, `kill(-1, 0)` and
  `kill(pid, 65)` lines Linux's. Its 30 `/proc` rows stay PAX's whole
  (PAX has no `stat`, `maps`, `mem`, `auxv`, `io`, `limits`, `exe`,
  `cwd`, `root` of another process), but their `status`, `cmdline`,
  `environ`, `fd/` fields and the directory's owner are Linux's in the
  25 rows of the five targets that settle.
- `priv` (px38's, byte for byte, as the first program): **20 of 30**
  lines (from 4). The ten left: `mem`, `kmsg` and `ptmx` (PAX has
  none), root's raw socket (refused by name), `prlimit64` (limits are
  out of the campaign), `mknod` of a FIFO (PAX makes none; on the
  chroot lines), `/dev/tty` (-ENXIO on Linux, where the probe has no
  controlling terminal; PAX's console is every process's), root's
  and the user's open-for-writing lines for those reasons.
- This lane's probe (`rights`), as root dropping to its actors and as
  1000:1000: every line Linux's (vm-protected) at the first boot of
  the kernel the measurement corrected, none by rule.
- `ids`: its `SO_PEERCRED` line Linux's: 61 of 71 (from 60).
- Every other session of `tests/mpx5-users` keeps its numbers.

**P4. Existing suites.** Every existing suite runs as root and passes
unchanged: effective user id 0 passes every signal and every privilege
test, file-system user id 0 every `/dev` and `/proc` check; no suite
signals a process as a user, binds a low port as a user or opens
`/dev` as a user. No file under `tests/` is edited but
`tests/mpx5-users` and its directory (and `tests/ci-plan` if a place is
added). Falsified by an edit to another suite or a red one.

**P5. The soak.** `rights soak 100000`, as root and as 1000:1000: ten
calls a round (a signal refused and one allowed, a `tgkill` refused, a
low port refused, a priority lowered, a 0600 node opened, another
process's `environ` read, `SO_PEERCRED` read, a `chroot`, a `reboot`):
0 wrong answers, `MemFree` one number at each quarter.

**P6. Plants.** A, the signal rule ignored (every sender allowed): red
first in `sig` at its first refused row, `(1000 1000 1000)` to
`(1002 1000 1001) no exec`. B, the port test ignored: red first in
`priv` at its user `bind` line. Each red in CI with `mpx5-users` the
only suite.

**P7. What it costs.** The kernel's text grows by under 8 KiB; the
process area gains under ten words; no inode or table changes.

### Corrections to §2 and §3, found after they were committed

- §3 P2 named `rights`' rows before they were written; they came out as
  seven sections (S, K, H, E, P, D, R, C): 284 lines as root dropping to
  its states and 20 as 1000:1000 (§F).
- §3 P1 said "under ten words" of the process area and "no inode or
  table changes" (P7): the area gained six words (202 to 207), and
  kernel/unix's table grew by two words a socket (SO_PEERCRED's), 4 KiB
  of `.bss` (§F, P7).
- After the first boot of `rights` on PAX (eight lines apart, of four
  kinds, §3a P3), three kinds were the probe's and were changed before
  any count was taken: root's raw socket (PAX has none: refused by name, so it is a
  user's row only), a user's KIOCSOUND on root's descriptor (Linux's
  probe has no controlling terminal and every PAX process's is the
  console: §B), and the environment a target that does not `execve`
  inherits (the machine's own; the probe now re-executes itself with
  one environment, `PX45=rights`, on both). The Linux recording was
  taken again with the changed probe (`vm-rights.meta`).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | one signal rule in `kernel/signal`, asked by `kill`, `tgkill`, `tkill` and each process `kill(-1)` and `kill(0)` reach; what the kernel raises asks nothing; one privilege test in `kernel/cred` | `signal.may_signal` (§A), asked at those six places and nowhere else; `cred.privileged`, made public, asked by kernel/socket, kernel/process, kernel/files (`/proc`'s guard), kernel/user (`mknod`, the speaker) — no second copy of either | right |
| P2 | Linux's unrecorded answers (§3's list) | right but for: **`tgkill` of a zombie** answers by the rule like `kill` (0 or -EPERM), not -ESRCH; **`chroot`, `umount2` and `clock_settime`** ask their arguments first (a missing directory -ENOENT, a file -ENOTDIR, CLOCK_MONOTONIC -EINVAL, to a user too), where §3 said -EPERM first (only `reboot` and `sethostname` answer -EPERM before their arguments); **a listening socket's own SO_PEERCRED** is its own ids at `listen` and an AF_INET socket's is pid 0 and -1, neither predicted; `setpriority` of a zombie is 0 (not predicted); a zombie's `/proc` files are root's (not predicted). The rest as §3 said (§A to §E). The kernel was written after this measurement (`rights` on vm-protected, `notes/px45/devs.c` under tools/linux-sound), so P3's first boot is a test of the code against Linux, not of P2 | wrong (5) |
| P3 | `sig` 99 of 102 sender rows, the three set-ID rows left; `priv` 20 of 30; `rights` every line Linux's at the first boot; `ids` 61 of 71 | `sig` **99 of 102**, exactly the three rows named; `priv` **19 of 30** — the user's KIOCSOUND row is PAX's too: Linux gates the speaker by the controlling terminal (measured, §B) and every PAX process has the console for one; `rights` **276 of 284** at the first boot (the kernel at `92e113b`; `notes/px45/pax-p4a-rights.txt` against the same probe's Linux run, `linux-try2-rights.txt`: eight lines of four kinds, two each — the three the probe's above, and one the kernel's: a process that had just ended had no `/proc/<pid>` until the next fork or wait, where Linux's is a zombie at once; kernel/sched fixed, `9731dbd`), then **284 of 284** and `rights-user` **20 of 20** at every boot after; `ids` **61 of 71** | wrong (priv by one; rights not at the first boot) |
| P4 | every existing suite green as root; no test edited but `tests/mpx5-users` and its directory | {{P4}} | {{P4V}} |
| P5 | the soak: 0 wrong, `MemFree` one number | `rights soak 100000` as root and as 1000:1000: 1,000,000 calls each, **0 wrong answers**, `MemFree` one number at every quarter on {{SOAKLEGS}} | right |
| P6 | plant A red first in `sig` at `(1000 1000 1000)` to `(1002 1000 1001) no exec`; plant B red first in `priv` at its user `bind` line | {{P6}} | {{P6V}} |
| P7 | under 8 KiB of text; under ten area words; no inode or table changes | `.text` **+24,096 bytes** (859,259 to 883,355; `.rodata` +560, `.data` +344), six area words, and kernel/unix's table **+4 KiB** of `.bss` (`notes/px45/kasumi-kernel-cost.txt`) | wrong |

## A. Who may signal whom (item 1)

`kernel/signal`'s `may_signal(me, t, sig)` is the rule, measured on
real root (px38's `sig`, 102 rows; `rights` S, 119 rows with `tkill`,
the set-ID state and two zombies):

- a sender may signal when its **effective user id is 0**, or its
  **real or effective user id is the target's real or saved user id**
  — a target's effective id is never asked; a sender whose only match
  is its own saved id is refused; (0, 1003, 0) is refused every user's
  process and allowed root's, (1003, 0, 1003) allowed everyone's;
- **SIGCONT** to anyone: Linux allows it within a session, and PAX has
  one session holding every process (no job control, ruling #79);
- **a zombie** answers by the same rule against the ids it ended with
  (`kill`, `tgkill`, `tkill`: 0 or -EPERM) and is signalled nothing;
  before px45 PAX answered -ESRCH;
- **validity first**: signal 65 is -EINVAL before any permission (root's
  target, by a user), no such process -ESRCH, `tgkill` of a thread not
  in the group -ESRCH, `tkill(999999)` -ESRCH;
- **`kill(-1, sig)`** signals every permitted process but pid 1 and the
  caller and answers 0 whenever some such process exists, permitted or
  not (five sender states); **`kill(0, sig)`** and a negative group are
  every process on PAX (one group), each by the rule, 0 when one was
  signalled (the caller always is);
- **siginfo** (`rights` H): `si_uid` is the sender's **real** user id
  ((1003 1000 1003) is told as 1003), `si_code` SI_USER (0) for `kill`
  and SI_TKILL (-6) for `tgkill`, `si_pid` the sender's;
- **a child's end** (`rights` E): SIGCHLD reaches the parent whatever
  either's ids (a parent of 1002 or 1003, children of 1000, 1001,
  (1001 1003 1001) and (0 1003 0)), with CLD_EXITED or CLD_KILLED, the
  child's pid, its **real** user id and its status;
- what the kernel raises — SIGCHLD, the terminal's keys, SIGPIPE, a
  fault — asks nothing.

`sig` on PAX: **99 of 102** sender rows Linux's (33 at trunk
`2167620`). The three left are the set-ID target's (`1000 ran 04755 of
1001`) where the sender matches only 1001, the copy's owner:
`(1001 1001 1001)`, `(1003 1001 1003)`, `(1001 1003 1003)`. On Linux
that target is (1000 1001 1001); on PAX its copy cannot run (written
since boot, px27) and would raise no id if it did (R5), so it is a
zombie of (1000 1000 1000). `rights` makes the same state without a
bit (`setresuid(1000, 1001, 1002)` then `execve`: (1000 1001 1001)) and
holds its rows, all Linux's. Its other lines: the 30 `/proc` reader
rows are PAX's whole (PAX has no `stat`, `maps`, `mem`, `auxv`, `io`,
`limits`, `exe`, `cwd`, `root` of another process); `/proc is mounted`
reads `? (?)` (no mountinfo); the set-ID target's line and its `!`
line. Held whole to `tests/mpx5-users.d/sig.pax`.

`tgkill`'s race (pax#62) is the reference's: Linux answers a just-joined
thread's tid before it retires it; nothing here touches `mpx3-threads`'
probe or PAX's answer (-ESRCH, unchanged), and the fix is not one line
(the probe must wait for the tid to go), so it stays its issue's.

## B. What only root may do (item 2)

Each measured as Linux answers a user (`rights` P, four states: root,
(1000 1000 1000), (1000 0 1000) which is root by its effective id, and
(0 1000 0) which is not), and px38's `priv`:

| operation | Linux, to a user | Linux, to root | PAX now |
|---|---|---|---|
| `bind` TCP or UDP 1 to 1023 | -EACCES, before whether the port is taken (81 held by root: -EACCES to a user, -EADDRINUSE to root) | 0 | the same (`socket.may_bind`) |
| `bind` 0, 1024 and up | 0 | 0 | the same |
| `/proc/sys/net/ipv4/ip_unprivileged_port_start` | `1024`, 0644, root's | | the same, fixed |
| `socket(AF_INET, SOCK_RAW)` | -EPERM | 0 | -EPERM to a user; root's refused by name (-ESOCKTNOSUPPORT: PAX has no raw socket) |
| `setpriority(PRIO_PROCESS)` | its nice raised: 0; lowered (even from 5 to 4): -EACCES; another's: 0 when the caller's effective id is the target's real or effective one (a zombie's too), else -EPERM; no process -ESRCH; `which` 7 -EINVAL; 25 is cut to 19 | anything | the same (`process.setpriority`; kept and reported, the scheduler unchanged: named drift); PRIO_PGRP and PRIO_USER refused by name |
| `getpriority` | 20 minus the nice value, anyone's | | the same |
| `sched_setscheduler` | SCHED_FIFO, SCHED_RR -EPERM; SCHED_OTHER 0; priority out of range -EINVAL first; another's by the same rule as `setpriority` | 0 | the same (kept and reported); SCHED_DEADLINE and SCHED_RESET_ON_FORK refused by name |
| `chroot` | the path first (missing -ENOENT, a file -ENOTDIR), then -EPERM | 0 | the same; root: the tree's root 0, any other directory refused by name (-EOPNOTSUPP: PAX keeps one root) |
| `reboot` | -EPERM, even with a bad magic | a bad magic -EINVAL | the same; root's with a good magic refused by name (PAX halts when init ends) |
| `sethostname`, `setdomainname` | -EPERM, even for 100 bytes | 100 bytes -EINVAL | the same; root's refused by name (uname is fixed) |
| `clock_settime` | CLOCK_MONOTONIC -EINVAL first; CLOCK_REALTIME -EPERM | MONOTONIC -EINVAL | the same; root's REALTIME refused by name |
| `settimeofday` | -EPERM | (not asked: it would change the machine) | -EPERM; root's refused by name |
| `mount` | -EPERM | (not asked) | -EPERM; root's refused by name ("mounting if any path exists": none does) |
| `umount2` | the path first (-ENOENT), then -EPERM | a missing path -ENOENT | the same; root's refused by name |
| `mknod` of a character device | -EPERM | 0 | -EPERM to a user; root's refused by name as before (PAX makes no node) |
| `prlimit64` raising a hard limit | -EPERM (lowering it 0) | 0 | -EPERM for both, as before (limits are out of the campaign) |
| `kill(1, SIGTERM)` | -EPERM | | the same (§A) |
| KIOCSOUND, KDMKTONE (the speaker) | -EPERM on a virtual terminal that is not its controlling terminal, whether root opened it or the user owns it; **0 on its controlling terminal** (`notes/px45/devs.c`, `linux-devs.serial.log`) | 0 | the rule (`console.controlling`): the console is every PAX process's controlling terminal (one session), so anyone with a console descriptor may sound it — as a user `su`'d on Linux's console may; `priv`'s user row (Linux's probe has no controlling terminal) is held to PAX's text by name |
| the sound card (`/dev/dsp`, OSS on virtio-snd) | its own `open` -EACCES (0600, root's: devtmpfs's, no udev); the OSS ioctls on a descriptor root opened 0, and a write 4096 (not gated) | 0 | the same (§C): the class rule on `open`, nothing on the ioctls |

`reboot`/halt from pelt's `exit`: PAX halts when init ends and nothing
else halts it; a user cannot be init (R2: the image boots to root's
shell), and `reboot(2)` is -EPERM to a user.

## C. `/dev`: modes and owners, checked on open (item 3)

Measured on devtmpfs with no udev (`rights` D, `priv`'s device lines):
every node 0:0.

| node | mode | numbers | PAX |
|---|---|---|---|
| `null`, `zero`, `full`, `random`, `urandom` | 0666 | 1:3, 1:5, 1:7, 1:8, 1:9 | the same; `zero` and `full` read zeros, `full`'s write -ENOSPC, `random` and `urandom` are `getrandom`'s (never blocking) — `zero`, `full`, `random`, `urandom` new |
| `tty` | 0666 | 5:0 | new: opens the console (every process's controlling terminal); Linux's probe has none and is told -ENXIO (named) |
| `console`, `tty0`, `ttyS0` | **0600** | 5:1, 4:0, 4:64 | 0600 (0620 before); `ttyS0` new |
| `dsp` | **0600** | 14:3 | 0600 (0666 before) |
| `mem`, `kmsg`, `ptmx` | 0600, 0644, 0666 | | not there (-ENOENT) |

`open` and the access family ask the class rule of each (`files.checked`
and `may`, owner 0): a user's open of `console`, `tty0`, `ttyS0` and
`dsp` is -EACCES, of the 0666 ones 0 (`rights` D, `priv`). A descriptor
already open keeps what it was opened with (a user's inherited console
descriptors 0-2). What `/dev/stdin`, `stdout` and `stderr` reopen keeps
its own answer: devtmpfs has no such names to measure (they are udev's
links), named. A distribution's udev gives some nodes to a group
(`tty0` 0620 root:tty, `dsp` 0660 root:audio); PAX has no such group
and keeps the kernel's own (named).

## D. `/proc/<pid>` by owner and dumpable (item 4)

Measured (`sig`'s 30 reader rows and `rights` R: 8 readers, 7 targets,
two of them zombies):

- `/proc/<pid>` is the target's **effective** ids, 0555, dumpable or not;
- `status` and `cmdline` (0444) are anyone's to read; their owner is
  the target's effective ids while it is dumpable, **0:0** when it is
  not and when it has ended;
- `environ` (0400) and `fd/` (0500), owned as above, are read only by
  the target itself, by a reader whose **effective user id is 0** — and
  whose file-system ids pass the mode (root after `setfsuid(1002)` is
  refused 1000's `environ`) — or by one whose **file-system user and
  group ids are each of the target's real, effective and saved ones
  while it is dumpable** ((1003 1000 1003) with file-system id 1000
  reads (1000 1000 1000)'s; (0 1000 0) does not read root's); everyone
  else -EACCES (`files.may_read_of`);
- `cmdline` is the program's argument strings as they are now in its
  memory and `environ` its environment strings, NULs included (at most
  a page on PAX, named); a zombie's `cmdline` is empty, its `environ`
  opens for root and its read is -ESRCH, its files are 0:0;
- `fd/` lists the open descriptors (three for a target that `execve`d);
  PAX lists them as links and does not follow or read them (a lookup
  of `fd/<n>` is -ENOENT: named).

## E. SO_PEERCRED (item 5)

Measured (`rights` C, `ids`): `getsockopt(SOL_SOCKET, SO_PEERCRED)`
answers a `struct ucred` — pid, uid, gid — of the **effective** ids:

- a socketpair's ends (stream and SOCK_SEQPACKET): the maker's pid and
  ids at `socketpair` (a child that becomes 1002 later is still told
  its parent's 0:0; a maker (1001 1002 1003) with groups (2001 2002
  2003) gives 1002:2002, and still after `setfsuid(1003)`);
- a listening path socket: its own pid and ids **at `listen`** (root
  that listened and then became 1001 is told 0);
- a connector's end: the listener's at `listen`; the accepted end: the
  connector's at `connect` ((1002 1003 1002), gids (2002 2003 2002):
  1003:2003);
- a socket never connected, and every AF_INET socket: pid 0, uid and
  gid -1;
- a length of 8 writes 8 bytes (the gid untouched) and answers 8; 16
  answers 12.

`kernel/files`' `peercred`; kernel/unix keeps the pid and ids in two
new words a socket. `ids`' socketpair line is Linux's now (61 of 71).
pax#58's remainder (an AF_INET socket's, an eventfd's and an accepted
end's `fstat` owner) was not reached.
