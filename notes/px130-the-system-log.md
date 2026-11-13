# px130 — a kernel log you can read, a quiet console, and where the system's logs live (pax#383)

Base: trunk `0e2843cf`. Queued ahead of this branch, fast-forward only: pax#379 (the console draws only what
changes), then pax#347, pax#350's successor, pax#361, pax#358, pax#359. pax#379 changes when the screen draws
(`kernel/screen`'s held write, `kernel/serial`), which is where this branch's console level sits; expect a rebase
onto it, delivered as a new branch and pull request.

## 0. The prediction (written before the first change)

**Why.** The kernel writes a line for every process its signal's default action ends (`kernel/signal`'s `die`:
`user: NAME pid N killed: SIG…[, a write to a pipe with no reader] after N runs`) through `kernel/log`, and every
byte `kernel/log` writes goes through `serial.put`, which draws it on the screen before the serial port takes it.
So a line about a program run over ssh lands wherever the console's cursor is, over the console's prompt. And
nothing keeps a kernel line once it has scrolled: no ring buffer, no `dmesg`, no `/dev/kmsg`.

**The measurement (item 1).** An installed-shape image (the burrowd suite's tree: `/bin/login` as pid 1, pelt
with its friendly prompt and lope's hook from `/etc/shrc`, den, boreutils, burrowd) booted under QEMU with the
console logged in as root and one ssh session at a pseudo-terminal as `pax`, once with `quiet` (as an installed
system boots) and once without (every exec and exit narrated, to name each pid). What I expect each piece of
ordinary work to write:

| work over ssh | line(s) expected | verdict expected |
|---|---|---|
| `yes \| head -n 3`, `seq 1 100000 \| head -n 2`, `cat BIG \| head -n 1` | the writer `killed: SIGPIPE, a write to a pipe with no reader` | correct: the writer of a pipeline whose reader ended dies of SIGPIPE on Linux too; shells say nothing |
| `ls /bin \| head -n 3` (a short writer) | none, or ls killed by SIGPIPE when its output outruns head | correct either way |
| Ctrl-C on a foreground `sleep 30`; Ctrl-\\ | `sleep … killed: SIGINT` (`SIGQUIT`) | correct |
| `exit` | pelt's `exit_group 0` (narrated only without `quiet`) | correct |
| the client dropped (its process killed) | pelt `killed: SIGHUP` (the pty hung up), and any job left in the session | correct |
| pelt's friendly prompt and lope's hook (a `cd`, a jump) | lope's exec and exit per directory change, no `killed:` | correct |
| `den init`, `add`, `commit`, `status`, `log` | each den's `exit_group 0`; none killed | correct |
| `den push` / `den fetch` to a file remote | den and its upload-pack / receive-pack helpers exit 0 | if a helper dies of SIGPIPE or SIGTERM, a den fault to file there |

Prediction: on an installed system (`quiet`) the only lines over the prompt are `killed:` lines, almost all
SIGPIPE from pipelines and SIGINT from Ctrl-C, each correct behaviour; whatever is not (a helper that should have
exited on its own) is a fault in that tool, filed there and left visible.

**The design (items 2 and 3).**
- *The ring buffer.* A new module below `kernel/log` keeps every kernel line as a record: a sequence number, a
  level (syslog's 0-7, the facility `kern`), a timestamp from the tick counter (the clock `CLOCK_MONOTONIC`
  reads, 10 ms steps, 0 before the tick starts) and the text. Fixed static storage of 128 KiB, oldest records
  overwritten; nothing survives a reboot (the boot's own bytes keep px118's separate record). A line written
  without a level gets the default level, 4 (warning), as Linux gives one; the lines of a program's ordinary life
  (killed by a signal, exec, exit, a thread's exit, the counts after a run) are written at 6 (info).
- *Readers.* `syslog(2)` (actions 0-10, as `syslog(2)` documents them) and `/dev/kmsg` (character device 1:11:
  one record per read, `PRI,SEQ,USEC,-;TEXT\n`; a reader that has caught up blocks, or answers -EAGAIN with
  O_NONBLOCK; a reader whose next record was overwritten gets -EPIPE once and goes on from the oldest; a write
  adds a record at the level its `<N>` prefix names; SEEK_SET, SEEK_END and SEEK_DATA as the kmsg document says;
  `poll` ready when a record is there). `/proc/sys/kernel/dmesg_restrict`, 1 at boot: reading is root's.
  `/proc/sys/kernel/printk` reports the console level.
- *`dmesg`* on every image: boreutils has none (coreutils carries none; util-linux does) and busybox is not on the
  images, so a small one in wolf (`user/dmesg`), reading `/dev/kmsg`: `[seconds.micro] text`, `-r` raw, `-l`
  levels, `-w` follow, `-n LEVEL` and `-C` / `-c` for root.
- *The console level.* `log` decides at a line's first byte whether the line reaches the screen: a line at or
  above the console level (less severe) goes to the serial port and the ring buffer only. Today's behaviour is
  level 8, every line shown, and stays the default: the development and test images, which boot without `quiet`,
  keep it. With `quiet` (every shipped image and every installed system) the level drops to 5 once the first
  program starts: warnings and worse (and every line with no level) still draw, info does not. `loglevel=N` on
  the command line sets it from the start; root's `dmesg -n N` (`syslog(2)` action 8) at run time. The serial
  port keeps every byte it has today: no suite's serial expectations move.

**What each row should show** (rows in `tests/mpx5-burrowd`, which already boots the installed shape with `quiet`
and drives an ssh session at a terminal, unless named):

| row | at the rows' commit (before the kernel change) | after |
|---|---|---|
| a writer killed by SIGPIPE over ssh: the console's screen unchanged (screendumps before and after equal) | red: the line is drawn | green |
| the same line in the ring buffer with a timestamp: root's `dmesg` at the console shows it | red: no `dmesg`, no buffer | green |
| `dmesg` refuses `pax` by default (`dmesg_restrict` 1) | red: no `dmesg` | green |
| a warning still reaches the screen | green by accident (every line draws) | green |
| the serial port still has the `killed:` line, byte for byte | green | green |
| `/dev/kmsg` (a kernel suite's program, against Linux's own `/dev/kmsg` where it answers): the record format, -EAGAIN, follow, -EPIPE on a wrap, a write's level, `syslog(2)` READ_ALL and SIZE_BUFFER, the refusal to a user | red: no device, -ENOSYS | green |
| the buffer wraps at its size: after more than 128 KiB of records the oldest is gone, the sequence numbers run on, the newest is whole | red | green |
| every suite that reads `killed:` lines from serial | green | green, unchanged |

The plant: the console level ignored (every line drawn again): the screen row red by name.

## 1. The measurement: which programs die by which signals in ordinary work over ssh

**The rig** (`notes/px130/rig/measure.py`, run by `measure.sh` in the burrowd suite's container, three takes at
`30286627`, `6f89b0ec` and `9fa21372`): the burrowd suite's installed shape (its tree, built once at `30286627`:
`/bin/login` as pid 1, pelt `b80d6570`, lope's hook from `/etc/shrc`, den `291011dd`, burrowd `7aa182f8`, boreutils
with `head`, `seq`, `yes` and the rest of the work's programs), booted under QEMU with KVM twice a take, without
`quiet` (every exec and exit narrated, so each pid has a name) and with it (what an installed system shows). Root is
logged in at the console first; then four or five ssh sessions as `pax` at a pseudo-terminal of the rig's own type
the work, each step timed on the host's monotonic clock, and every serial line is stamped with the time its newline
arrived and put to the step in progress. From the second take on, the rig's terminal answers pelt's cursor query as
a terminal emulator does; from the third, pax's login shell is `/bin/pelt`, as the guided installer writes an
account (`user/install/prepare.lu`), so pelt starts friendly (invoked as `sh`, the suite's own `/etc/passwd`, it
does not: pelt's docs/FRIENDLY.md) and its prompt runs `den status --porcelain` once a prompt; the third adds a
repository of 400 files with 60 changed.

**Every `killed:` line, and what it was** (18 lines a plain boot in each take, 17 under `quiet`; the same set in
all three takes but for the pids):

| the work over ssh | the line | who sent the signal | verdict |
|---|---|---|---|
| `yes \| head -n 3`, `seq 1 200000 \| head -n 2`, `cat big.txt \| head -n 1`, `x=$(yes \| head -n 1)` | the writer: `killed: SIGPIPE, a write to a pipe with no reader` | the kernel, to the writing thread itself (`pipe(7)`) | correct: Linux ends the writer the same way, and no shell says so |
| `(yes; echo done) \| head -n 1` | `yes` and the subshell (pelt) `killed: SIGPIPE` | the kernel | correct: the subshell's `echo` writes to the same pipe; bash's subshell ends the same way |
| `ls /bin \| head -n 3`, `ls -l /bin \| head -n 2`, `den diff \| head -n 3`, `den log \| head -n 2` | none: the writer's output fit in the pipe | — | — |
| Ctrl-C on a foreground `sleep 30`, `cat`, `yes > /dev/null` | `killed: SIGINT` | the pty's line discipline (ISIG), to the foreground group | correct |
| Ctrl-\ on `sleep 30` | `killed: SIGQUIT` | the pty | correct |
| the client dropped (its process killed) | the session's pelt `killed: SIGHUP`; a job stopped earlier in the session `killed: SIGHUP` | the kernel: the pty's hangup to the controlling process (px111), the orphaned group with a stopped member (XSH _exit) | correct |
| `exit` | pelt `exit_group 0`; burrowd's session processes exit 0 | — | correct |
| the console's root shell exits (the machine's end) | burrowd's two and every program left `killed: SIGTERM` | the kernel's end of the run | correct |
| `den init`, `add`, `commit`, `status`, `log`, `branch`, `remote add`, `push` and `fetch` to a file remote, `clone` | every den exits 0, two to four processes a push or fetch (den and its upload-pack or receive-pack through the `git-*-pack` wrappers) | — | correct: no den is killed |
| the friendly prompt's `den status --porcelain`, once a prompt | `exit_group 128` outside a repository, `0` inside, the 400-file one with 60 changed too; never killed | — | correct |
| lope's hook (`cd`, autocd's `../`, `g`) | lope exits 0; autocd's two subshells exit 1 | — | correct |

So every line a person at an installed machine saw drawn over the console's prompt is a program's correct end:
mostly a pipeline's writer told by SIGPIPE that its reader is gone, and Ctrl-C, Ctrl-\ and a dropped session. No
den helper and no pelt subshell lingered or died where it should have exited on its own, so there is no fault to
file in den or pelt. What was wrong is where the lines went: every one was written over the console's screen,
wherever its cursor was, and nowhere they could be read later.

**Two findings that are not kill lines**, both pelt behaving as dash and POSIX do, neither a fault:
- a session dropped with a foreground `sleep 100` running: pelt dies of SIGHUP, the sleep runs on (its line is the
  machine's end's SIGTERM). bash resends SIGHUP to its jobs when it receives one (bash(1)); dash and pelt do not,
  and the kernel signals only the controlling process at a hangup (px111 measured Linux doing the same); decision 10;
- `kill %1` of a stopped job leaves it stopped (its SIGTERM pending until the session's hangup sends SIGHUP and
  SIGCONT). Measured in a container: bash continues it and it ends, dash leaves it stopped, as pelt does.


## 2. The design, as built

**The ring** (`kernel/kmsg`, new; it imports nothing, so `kernel/log` can sit above it). 128 KiB of `.bss`
(`boot/console.S`'s `pax_kmsg_buf`) holding records back to back: a sequence number (0 for the boot's first line), the
time in microseconds, `level | facility << 3 | length << 16`, then up to 992 bytes of text. A record that needs room
drops the oldest records, whole, as many as it takes; one that does not fit before the ring's end goes to its start.
Nothing survives a reboot: `.bss` is zeroed by every boot (the boot's own console bytes are px118's, kept apart).
The time is the tick count (the clock CLOCK_MONOTONIC reads, 10 ms steps, 0 until the tick starts): decision 1.

**Levels.** `log.at(level)` before a line's first byte; a line written without one is at 4, warning, Linux's
default for a line with no level, so every line the kernel writes today keeps reaching the screen unless it is
marked (decision 3). The lines of a program's ordinary life are marked 6, info: a death by a signal's default
action (`kernel/signal`'s `die`), a death by a fault (`kernel/user`'s `kill`, as Linux's segfault line: decision 8),
an exec, an exit and a thread's exit, an `execve` that ended threads, the -ENOSYS, -EBADF and -EFAULT lines and the
census lines (a full tree stays a warning).

**The screen.** `kernel/log` decides at a line's first byte whether its bytes go to `serial.put` (the screen, then
the wire) or to `serial.put_wire` (the wire alone, and px118's boot record): the screen when the line's level is
below the console level. The console level is 8 (every line) until something lowers it: `quiet` on the command line
lowers it to 5 when the first program starts (`kmain_console`, where px118 seals the boot record), so warnings and
worse still draw and info does not (decision 2); `loglevel=N` sets it from the start; root's `dmesg -n N`,
`syslog(2)`'s CONSOLE_LEVEL, CONSOLE_OFF and CONSOLE_ON and a write of `/proc/sys/kernel/printk` set it at any
time. The serial port gets every byte it got before: no suite's serial expectations move.

**Readers.** `syslog(2)` (103): actions 0-10 as syslog(2) has them; every action but READ_ALL and SIZE_BUFFER is
root's, and those two are too while `/proc/sys/kernel/dmesg_restrict` is 1 (its value at boot: decision 5);
READ waits for a record as a pipe's reader waits. `/dev/kmsg` (mem's 1:11, 0644): one record a read in the
dev-kmsg document's form (`PRI,SEQ,USEC,-;TEXT`, bytes below 0x20, above 0x7e and `\` as `\xNN`), -EINVAL for a
buffer the record does not fit; at the end -EAGAIN (O_NONBLOCK) or a wait, woken by the next record through
`kernel/sched`'s `wake_sleepers`; -EPIPE once for a reader the ring overtook, then on from the oldest; SEEK_SET,
SEEK_END and SEEK_DATA with offset 0 (-ESPIPE for another offset, -EINVAL for another whence); poll; a reader is
refused -EPERM by dmesg_restrict at open, a user's write -EACCES by the mode. A write is a record at its `<N>`
prefix's level and facility, LOG_USER for none and for the kernel's own, and is drawn as a kernel line at that
level would be; a `writev` is one record. Linux limits a burst of writes to /dev/kmsg by default and PAX does not
(decision 7). `/proc/sys/kernel/printk` reads `8	4	1	8` (the console level, the default level, the
minimum, the default console level).

**`dmesg`** (`user/dmesg`, wolf, builtins only, a six-call assembly membrane; `tools/mkdmesg`; `/bin/dmesg` on
every image): boreutils has none (coreutils carries none: it is util-linux's) and busybox is not on the images
(decision 6). It reads `/dev/kmsg` as util-linux's does (O_RDONLY|O_NONBLOCK; O_RDONLY for `-w`; syslog(2)'s
READ_ALL when the device is missing) and prints `[SSSSS.UUUUUU] TEXT`; `-r`, `-t`, `-l LEVELS`, `-w`, `-W`, `-c`,
`-C`, `-n LEVEL` (a name means that level and worse: its number + 1, as util-linux 2.39 sends it), `-D`, `-E`; its
refusals in util-linux's words and status (`dmesg: read kernel buffer failed: Operation not permitted`, exit 1).

**What else moved.** `tests/mpx5-users`' privilege probe: `/dev/kmsg`'s device row is Linux's now and its open rows
are root's 0 and the user's -13, as Linux's (22 of 30 lines Linux's, from 21). The tiers map runs every suite for a
change to `kernel/kmsg`, as for `kernel/log`.

**With px129 (pax#379).** px129 holds the screen's drawing to the end of a write (`screen.batch_begin`/`end`) and
moves a few lines of `kernel/serial` and `kernel/console`; this branch adds `serial.put_wire` beside `put` and sends
the console's and AHCI's bytes inside a kernel line through `kernel/log`. A line spared the screen never enters
the screen's held drawing at all, so the two compose; the rebase onto pax#379 meets them in `kernel/serial`'s
`put` (one hunk each side) and `kernel/console`'s `put_kernel` (untouched here).

## 3. The rows

- `tests/mpx5-kmsg` (new): one probe (`user/elf/kmsgprobe.c`, `tools/mkkmsg`), 41 rows as root and as 1000:1000,
  held line for line to Linux 7.2.4's answers for the same binary (`tests/mpx5-kmsg.d/linux/`, recorded by
  `notes/px130/rig/record.sh` under QEMU with `printk.devkmsg=on`): the node; the record's form; the reader at the
  end, -EAGAIN; a read too small; every seek rule; poll; `<4>`, none, `<14>`, `<30>`, `<9999>` and `<x>`; the
  escapes; a reader woken by a record written 300 ms later; SIZE_BUFFER, READ_ALL's lines, a short READ_ALL, the
  errors; printk and CONSOLE_LEVEL, OFF and ON; dmesg_restrict; **the wrap**: a reader held at the oldest record,
  the ring flooded past its size, -EPIPE once, then a record past the held one, the numbers consecutive, the newest
  record the last written and whole; CLEAR and SEEK_DATA; and as a user every refusal. No row is ruled.
- `tests/mpx5-burrowd` B40-B43, at the installed shape the suite boots with `quiet`, root logged in at the console:
  B40 `yes | head -n 1` over ssh leaves the console's screen the same picture (QEMU's screendump) before and after,
  and the serial port has its `killed: SIGPIPE` line as it always did; B41 root's `dmesg` shows that line with its
  time, `dmesg -r -l info` at `<6>`, `dmesg -l err,warn` not at all; B42 pax's `dmesg` over ssh is refused in
  util-linux's words, status 1; B43 through sudo over ssh, a `<6>` record written to `/dev/kmsg` leaves the screen
  as it was and a `<4>` one is drawn, both on the serial port. The numbers start at 40, clear of rows other open
  branches add to the same suite (B19-B29, B30-B32). The suite's tree gains boreutils' `head` and `yes` for B40.
  A kernel line reaches the serial port wherever the console's own output stands, so after root's `$ ` when the
  console waits at its prompt: B40 and B43 find their lines anywhere on a line, not only at its start (the first
  development take read the `<6>` record there and called it missing).

## 4. User-space logging: a proposal (not built)

**Where PAX is.** After this branch the kernel's own lines are kept (the ring, `dmesg`, `/dev/kmsg`), but only until
the next boot. User space keeps five private files, each written by its program in its own form: `/var/log/boot.log`
and `/var/log/boot.summary` (pax-boot-status, at each boot; boot.log rotated at 256 KiB, four kept), `sudo.log`
(every use, allowed or refused), `burrowd.log` (one line a connection), `pax-upgrade.log`, and the installer's
transcripts on the stick. None is rotated but boot.log; nothing records who logged in at the console or over ssh
and when they left; `who` (boreutils) reads a `/var/run/utmp` nothing writes, and there is no `last`. There is no
`/dev/log`, no `logger`, and PAX's AF_UNIX sockets are stream sockets only (syslog's socket is a datagram one).

**What a Linux distribution does** (syslog(3), logger(1), utmp(5), the Filesystem Hierarchy Standard's
`/var/log`, RFC 3164 and RFC 5424; a black-box look at Ubuntu 24.04's base system in a container):
- the kernel's ring and printk levels, read through `/dev/kmsg` (what this branch gives PAX);
- `syslog(3)`: a program sends one datagram a message to `/dev/log` (`<PRI>TIMESTAMP TAG[PID]: TEXT`, RFC 3164's
  shape; RFC 5424 adds a version, a host, structured data); `logger(1)` does it from a shell;
- a daemon (rsyslogd, or systemd-journald) owns `/dev/log`, drains `/dev/kmsg`, stamps each message and routes it
  by facility and severity: Debian and Ubuntu write `/var/log/syslog`, `/var/log/kern.log` and `/var/log/auth.log`
  (sudo, sshd, login: the auth and authpriv facilities), Red Hat `/var/log/messages` and `/var/log/secure`;
  journald keeps a structured binary journal (`journalctl`), in `/run` or, made persistent, in `/var/log/journal`;
- login accounting: `/run/utmp` (who is on now), `/var/log/wtmp` (every login, logout, boot and shutdown),
  `/var/log/btmp` (failed logins), `/var/log/lastlog`, written by login, sshd and the display manager through PAM,
  read by `who`, `w`, `last`, `lastb` and `lastlog` (Ubuntu's base image ships `wtmp`, `btmp`, `lastlog` and
  `faillog` empty, root:utmp, and no syslog daemon at all: a container has none);
- `logrotate`, run daily: each log rotated by size or age, compressed, a number kept;
- the kernel's audit subsystem (auditd) for security events, a separate and much larger thing.

**Options.**
- **A. What is there, and `dmesg`.** Each program keeps its own file; one README section lists them. No new
  program, and the kernel's lines still go with each reboot.
- **B. A small log service (recommended, in three steps, each worth having alone).**
  1. *The kernel's lines kept across boots.* `logd`, a small wolf program started by the boot hooks as burrowd
     is (by pid 1's successor once init lands): it reads `/dev/kmsg` from the first record, follows it, and
     appends each record to `/var/log/kern.log` as `TIME LEVEL TEXT` (the wall clock, ISO 8601 UTC, and the
     record's own monotonic time), rotating at 1 MiB with four kept. Nothing in the kernel changes. This alone
     answers "when, where and how" for every kernel event, a program's death included, after a reboot.
  2. *Who was on.* `login` (console), `burrowd` (each session) and pid 1 (boot and shutdown) append utmp(5)
     records to `/var/log/wtmp` and keep `/run/utmp`; a `last` (wolf) reads wtmp; boreutils' `who` and `users`
     start answering. Failed logins to `/var/log/btmp`.
  3. *One place for user space.* AF_UNIX datagram sockets in the kernel (a kernel item: PAX has stream sockets
     only); `logd` binds `/dev/log` and writes `/var/log/messages` and, for the auth and authpriv facilities,
     `/var/log/auth.log` (root's, 0600); a `logger`; then sudo, burrowd, login, pid 1, pax-upgrade and
     pax-boot-status send their lines there (RFC 3164's shape, with RFC 5424's ISO time) and their private
     files go after one release that writes both.
- **C. A journal.** journald's structured, indexed binary store and a `journalctl`. Far more than PAX needs now,
  and a format of its own to keep.
- **D. Everything through the kernel's ring.** Root's programs write their lines to `/dev/kmsg` (a facility each),
  and step 1's drain is the only writer of disk. Smallest of all, but a user's program cannot write it (0644,
  root's, as on Linux), the ring is 128 KiB, and a flood from one program pushes the kernel's own lines out.

**Recommendation: B, step 1 first.** It is small (a reader of a device PAX now has, an appender, a rotation), it
changes no program, and it turns this branch's ring into a record that survives a reboot. Step 2 is next for the
question "who was on, and when", and step 3 waits for datagram sockets. The smallest version worth having is step
1 alone.


## 5. Decisions (each with its options and a recommendation)

- **Decision 1, the records' clock.** (a) The tick count, the clock CLOCK_MONOTONIC and `/proc/uptime` read: steps of
  10 ms, 0 until the tick starts, the same time a program's own log would stamp. (b) kernel/clock's nanoseconds:
  finer, but kernel/clock writes its own lines through kernel/log, so the ring would call up through an address
  hook (wolf refuses an import cycle), and a line written while kernel/clock is being started could not be timed.
  (c) The TSC: no calibration below kernel/clock. **Recommended and built: (a).** Measured at the installed shape
  (the development take's serial port, `dmesg` at the console): the tick does not run through most of the boot, so
  378 of the boot's lines read `0.000000` and its last ones `0.070001`, though the boot took 773 ms by its own
  record; every line after the boot carries its time to 10 ms. A later step, if the boot's lines want times:
  kernel/clock hands kmsg its TSC calibration once it has one (kernel/clock may import kmsg: no cycle), and a
  record is stamped from the TSC from then on.
- **Decision 2, what lowers the console level.** (a) `quiet`, from the first program on: every shipped image (the
  release and dev ISOs, the stick) and every installed system boots with it, so an installed machine gets it with
  its next kernel and no new boot entry; `loglevel=8` keeps today's screen on any image. (b) A new command-line
  word only the installer and the upgrade's entry write: an installed system's existing entry would not have it.
  (c) Always. The development and test kernels the suites boot without `quiet` keep every line on the screen under
  any option, and the serial port keeps every line under all three. **Recommended and built: (a).** Read this way,
  the dev ISO's screen (it boots `quiet`) no longer shows a program's death either; its serial port and `dmesg` do.
- **Decision 3, a line with no level.** (a) Warning, Linux's default, and only a program's ordinary life marked
  info: every other kernel line reaches the screen as before (the boot's narration, a refusal, a full tree, the
  network's). (b) Every boot narration line info, drawn only during the boot: hundreds of call sites, and a line a
  person needs after the boot (a refusal) could be hidden by mistake. **Recommended and built: (a).**
- **Decision 4, the ring's size.** 128 KiB of `.bss` (Linux's common default, `CONFIG_LOG_BUF_SHIFT` 17), about 1,500
  lines of the boot's length; a line keeps 992 bytes (the serial port keeps it whole). **Built.**
- **Decision 5, who reads the log.** dmesg_restrict 1 at boot, as the Linux 7.2.4 the probe is held to answers (K27):
  root's (`sudo dmesg`); root may write 0 to `/proc/sys/kernel/dmesg_restrict`. **Built.**
- **Decision 6, which dmesg.** (a) PAX's own, in wolf, small (`user/dmesg`). (b) busybox's applet: busybox is a test
  input here, not on the images. (c) util-linux's: not in the org, and C. **Recommended and built: (a).**
- **Decision 7, writes to /dev/kmsg.** (a) Every write kept: only root writes the node (0644). (b) Linux's default
  limit on a burst (`printk.devkmsg=ratelimit`), which drops the rest and says so. **Recommended and built: (a);**
  the Linux reference is recorded with `printk.devkmsg=on` so the wrap row compares like with like.
- **Decision 8, a program's fault.** (a) Info, as Linux's lines for a segfault are: a program's end, not the
  kernel's fault; on the serial port and in `dmesg`, off a quiet screen. (b) Warning, on the screen.
  **Recommended and built: (a).** A fault in the kernel is a panic and is drawn as before.
- **Decision 9, user-space logging.** Section 4: option B, step 1 first (a drain of `/dev/kmsg` to
  `/var/log/kern.log` with rotation, no program changed). Not built.
- **Decision 10, pelt and a dropped session.** A foreground job outlives a dropped ssh session (pelt dies of SIGHUP and
  does not resend it to its jobs, as dash does not; bash does). Options: (a) leave it, POSIX's behaviour; (b) ask
  pelt to resend SIGHUP to its jobs as bash does. **Recommended: (b), a pelt issue to file;** not filed here
  (no fault: it is a choice).

## 6. What is fit for an image

The branch is fit for an image: its gauntlet is green at `b3662f7f` (§7), the kernel, `/bin/dmesg` and the images'
trees move, and nothing an installed system keeps on disk does (no new file, no format, no boot entry: `quiet` is
already on every entry). What a person at an installed system booted from it should see:
no `killed:` line over the console's prompt while working over ssh (pipelines, Ctrl-C, a dropped session); `sudo
dmesg` shows each of them with its time (`dmesg | tail`, `dmesg -w` to watch); `dmesg` without sudo says
`read kernel buffer failed: Operation not permitted`; the boot's own narration on the screen as before, and past
the boot a warning, a kernel fault or a panic still drawn; `sudo dmesg -n 8` puts every line back on the screen
until the next boot, and `loglevel=8` on the kernel's command line from the boot on.

## 7. Seen red, and the evidence index

Every record is the local recorder's (steps mode, `--keep-going`, `--preflight`, KVM): its header carries the head,
the tree, the manifest's digest and `preflight=ok`, and the rig's files by digest (`notes/px130/rig/`).

- **The rows' commit** `47f8aeb7` (the rows, the probe and the rig on the measurement; the kernel and the images as
  trunk has them): `red-47f8aeb7.log`, sha256 `12e57b8e84b1f98e046dc3648f1e3be0e2d2447f2eb3a081412d143f48a1bf91`,
  worst 1. `END kmsg-native-bios exit=1 secs=11`: M1 red (32 of 33 rows differ: `K1: stat -2`, no node) and M2 red
  (7 of 8: `K30: open O_RDONLY -ENOENT`, `K32: READ_ALL -ENOSYS`, …).
  `END burrowd-native-bios exit=1 secs=1638`, `mpx5-burrowd native bios: FAIL B0 B40 B41 B42 B43`, every other
  row PASS: B0 `the tree builds no /bin/dmesg (tools/mkdmesg)`; B40 `the serial line b'user: yes pid 406 killed:
  SIGPIPE, a write to a pipe with no reader after 3 runs'; the screen CHANGED (the line drawn over the console)`;
  B41 and B42 `dmesg: not found`; B43 `cannot create /dev/kmsg: Read-only file system`.
- **The final code head** `b3662f7f`: `final-b3662f7f.log`, sha256
  `e1a1f6d78a00db5dd8f942fad61e8293cf107a18db7d06999d58bf60c399b4fc`, worst 0: `END ci-plan exit=0 secs=72`,
  `END census exit=0 secs=26`, `END kmsg-both exit=0 secs=406` (M0-M3 on the native and the release kernel, BIOS
  and UEFI), `END burrowd-both-bios exit=0 secs=4134` (B0-B43, native and release, 66 rows PASS, 0 skipped),
  `END users-both-bios exit=0 secs=740` (U0-U5, native and release).
- **The plant** `px130-plant-level` (`ae3f337f`, one line of `kernel/log` on `b3662f7f`: a line's first byte sends
  it to the screen whatever its level): `plant-ae3f337f.log`, sha256
  `58d7adf73a168924b744efafe031d9c129abb42435103c38ac1c148cf3e20fd3`, worst 1,
  `END burrowd-native-bios exit=1 secs=1528`, red at B40 alone and by name: `FAIL B40 the session exit 0, stdout
  b'y\nB40-ran\n', stderr b''; the serial line b'user: yes pid 406 killed: SIGPIPE, a write to a pipe with no
  reader after 3 runs'; the screen CHANGED (the line drawn over the console)`. B41-B43 pass on it: a write to
  `/dev/kmsg` decides its screen in `log.inject`, which the plant leaves alone.
- **The suites that read the kernel's `killed:` lines (or its screen, or the boot record) from the serial port**,
  native on BIOS at `b3662f7f` on a second build host whose lane disk is an ext4 volume 91% full:
  `killed1-b3662f7f.log` (sha256 `5ff8013772d8b5b99c3d201ccadc2939c76698419a29a5e10396072267b4cba4`): mpx3-user,
  -loader, -boreutils, -threads, -maps, -tree `exit=0`; mpx3-shell `exit=1` at one row, S2 shell-long.
  `killed2-b3662f7f.log` (sha256 `7b9527b5621b79eca63cfc034bfecaf756b0d9b72550f2563a22b8575f9fabc6`): mpx4-udp,
  -tcp, -unix, -ready, -lobo `exit=0`; mpx4-session `exit=1` at one row, E2 session-shell.
  `killed3-b3662f7f.log` (sha256 `f9aecbf8300ef2d2a130d81127bc71cad17c36f5875a51073600c0c96acb273a`): mpx5-accounts,
  -forks, mpx3-screen, mpx5-screen `exit=0`; mpx6-journal, -root and -bootlog stopped at their disk builder (the
  rig's in-container engine took no `--user`, which tools/e2fs passes; `74d90a78` gives it the option), and ran at
  `f9911306` (`b3662f7f` and three notes-only rig commits): `disks-f9911306.log`, sha256
  `edcf842b487225354ff661f0ad7d16872cd9032043f623dca436dd90ad8bf452`, worst 0, `END mpx6-bootlog exit=0 secs=150`,
  `END mpx6-journal exit=0 secs=467`, `END mpx6-root exit=0 secs=146`.
  The two red rows are the host's, not PAX's: each compares `ls -l`'s `total` (and S2 `stat`'s `%b` of
  `/bin/ls`) with Linux's for the same tree, and here Linux's side is the larger: PAX's `/bin/ls` 29968 blocks,
  15339584 bytes in whole pages, Linux's 29976. A copy of that `ls` on the same volume took 5 and 6 extents and
  29976 blocks three times out of three (ext4 adds an index block past four extents). Every row that reads a
  kernel line in those suites passed (U3's and U10's `killed by name`, S1-S6 but shell-long's S2, E1's quiet and
  E4's signals).
  On a build host whose disk keeps that `ls` in two extents (29968 blocks, three copies of three), at `e2324002`
  (`b3662f7f` and the notes-only `hostdisk.manifest`): `hostdisk-e2324002.log`, sha256
  `8371ae63c0d2940e5ba557e9e47b5a00016ad53404e9c4b3beae7867466ab839`, worst 0, `END mpx3-shell exit=0 secs=495`
  (S2 shell-long byte-identical to Linux's, 44 lines), `END mpx4-session exit=0 secs=244` (E2 session-shell
  byte-identical, 29 lines).

## 8. The prediction, scored

- **The measurement**: held. Every line drawn over the prompt was a program's correct end, almost all SIGPIPE
  from a pipeline and SIGINT from Ctrl-C, with SIGQUIT, a dropped session's SIGHUP and the machine's end's
  SIGTERM besides; `ls | head` wrote none; no den helper or pelt subshell died where it should have exited, so
  nothing was filed in den or pelt. Not foreseen: the killed program is almost never pelt but the pipeline's writer
  (`yes`, `seq`, `cat`), and pelt's own lines come only from a dropped session and a pipeline's subshell.
- **The design**: built as predicted, with two corrections. The development ISO boots with `quiet` too, so its
  screen also stops showing a program's death past the boot (decision 2; `loglevel=8` gives it back). And the
  boot's own lines carry no useful time (decision 1's measurement).
- **The rows**: held at the rows' commit: the screen row red (the line drawn), the dmesg rows red (no `dmesg`), the
  `/dev/kmsg` rows red (no node, -ENOSYS), the serial line there before and after; all green at the final head,
  native and release. The warning half of B43 was green by accident at the rows' commit only in prediction: there,
  with no `/dev/kmsg` to write, B43 is red as a whole.
