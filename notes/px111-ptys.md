# px111 — pseudo-terminals

Contract: the planning repo's `sprints/pax/111-ptys/px111-ptys.md`. Base: pax trunk `4d899ea4`.
The prediction: `notes/px111/prediction.txt` (committed before the first kernel change); the red
rows before it: `notes/px111/red.txt`.

## 1. What this lane does

PAX had one terminal, the console. It now has Linux's pseudo-terminals, so a program written for
Linux's ptys runs unchanged: an ssh server's session, a terminal multiplexer, `script`, a shell
driven from another program.

- **`/dev/ptmx` and `/dev/pts`.** Opening `/dev/ptmx` (devtmpfs' 5:2, 0666) makes a pty: the
  lowest free number of 256, its slave locked until `unlockpt`. `/dev/pts` is devpts, a file
  system of its own with Linux's default options (R-px111-1): its directory (inode 1), its
  `ptmx` (inode 2, mode 0000) and each live pty's number (inode N + 3, 0600, owned by the
  opener's file-system ids, 136:N). A slave's name goes when its master closes; the pty goes
  when both ends have. `/proc/sys/kernel/pty/nr` counts them, `max` reads 256 (R-px111-4, -5).
- **One line discipline.** The slave is a terminal over the console's own line discipline,
  which now keeps its state per terminal: every routine takes the terminal's id (the console,
  or a pty's slave), and a slave's state and ring live in frames its pty holds. A slave's echo
  and output go into the pty's output queue for the master (20480 bytes); the master's bytes
  wait in an input queue (16384 bytes) until the line discipline takes them, as Linux's
  buffers do for byte-at-a-time writes (R-px111-6). A pty starts with Linux's pty settings,
  IXON included, and honours it (R-px111-2); the console keeps px13's IXON clear.
- **Sessions per terminal.** kernel/sched keeps each terminal's session and foreground group
  by its id; a process's controlling terminal is an id. `setsid`, `TIOCSCTTY`, `TIOCNOTTY`,
  an open without `O_NOCTTY`, `/dev/tty`, `TIOCGPGRP`/`TIOCSPGRP`/`TIOCGSID` (through the
  master too), the background rules (SIGTTIN, SIGTTOU, TOSTOP), the keys' signals for the
  foreground group, a controlling process's end, and `/proc/<pid>/stat`'s `tty_nr` and
  `tpgid` all work for a pty as they did for the console.
- **SIGWINCH and SIGHUP.** `TIOCSWINSZ` on either end sets the size and sends SIGWINCH to the
  foreground group when it changes. The master's last close hangs the slave up: the
  controlling process hears SIGHUP and SIGCONT, the session loses the terminal, the slave
  reads end of file and every other call is -EIO. Every slave descriptor closed: the master
  reads what is left, then -EIO, and polls HUP.
- **The ioctls.** `TIOCGPTN`, `TIOCSPTLCK`, `TIOCGPTLCK`, `TIOCGPTPEER`, termios on either end,
  the window size, `FIONREAD`, `TIOCOUTQ`, `TCFLSH`, `TCSBRK`; everything else refused by name,
  packet mode (`TIOCPKT`) among them (R-px111-3, -8).
- **A steal signals nobody.** `TIOCSCTTY` with 1 by a privileged session leader takes a
  terminal from another session and signals no one, the console's too (R-px111-9). px48 sent
  the old foreground group SIGHUP and SIGCONT there, from a recording whose `R:CONT,R:HUP` was
  the thief's own `TIOCNOTTY` (the thief, a child of R, kept R's tag and handlers).
  mpx5-jobs' transcript is unchanged by the fix and is its guard.
- **The suite.** `tests/mpx5-pty` boots two images: the probe (`user/elf/ptyprobe.c`, 286
  rows: opening, termios, the controlling terminal, the window, the hangup, poll and the full
  buffers, many ptys and none left) as root and as 1000:1000, and the session, where the probe
  drives pelt on a pty from the master side (a window resize reaching `$COLUMNS` through a WINCH
  trap, the byte 0x03 ending a foreground `sleep`, a hangup ending pelt). Each run's rows are
  held to what Linux 7.2.4 printed for the same binaries, recorded under QEMU from the suite's
  own archives (`tests/mpx5-pty.d/linux/`), each difference named in
  `tests/mpx5-pty.d/ruled.txt`.

## 2. Rulings

All eleven ruled A, as recommended (the orchestrator, 2026-11-09):

- **R-px111-1** devpts' options: Linux's defaults (a slave 0600 and the opener's ids,
  `/dev/pts/ptmx` 0000); no tty group.
- **R-px111-2** IXON on a pty: Linux's default iflag 0x500, honoured; the console unchanged.
- **R-px111-3** packet mode refused by name (-ENOTTY and the kernel's line).
- **R-px111-4** 256 ptys at once (11 frames each while open), -ENOSPC past them.
- **R-px111-5** `/proc/sys/kernel/pty/nr` and `max` served.
- **R-px111-6** 20480 bytes each way.
- **R-px111-7** a refused open of a locked slave changes nothing for open descriptors.
- **R-px111-8** every other request refused by name.
- **R-px111-9** a steal signals nobody, the console's too.
- **R-px111-10** `$COLUMNS` reached through a WINCH trap typed in the session; pelt setting
  COLUMNS itself is the orchestrator's backlog.
- **R-px111-11** the console stays one terminal; only its state is addressed by id.

## 3. Named differences, and the prediction scored

PAX answers as Linux in every row of every run but these (`tests/mpx5-pty.d/ruled.txt`):

- O36: `TIOCPKT` -ENOTTY, refused by name (R-px111-3); Linux 0.
- O40, O43: a refused open of a relocked slave; Linux then answers -EIO to the slave's open
  descriptors (R-px111-7).
- P5, P10, P11, P13, P10a#2, P10a#3, P10b#2, P10b#3, P10c: the full buffers' counts. Linux's
  move with the write size and from run to run (13824 to 22096 measured; P5 read 13824 and
  15360 in two recordings of one binary); PAX's are 20480 each way, Linux's count for writes of
  one byte (P10a, P10b, held to Linux).

The prediction (`notes/px111/prediction.txt`), scored:

- Right: every row's Linux answer recorded before the change is PAX's now but for the ruled
  rows; the kernel's shape (§D) as built; the plant's rows.
- Wrong:
  - P10c: predicted "the slave reads 20479", that Linux lost 12 bytes. Neither loses a byte:
    the last write's part of a line with no newline is not a line yet (Linux: 12 bytes of
    20512; PAX: 79 of 20479), so the slave reads 20400 on PAX.
  - P9 was not ruled and was first red: a master's read stops at the end of the 4096-byte
    stretch it starts in (Linux read 4095 after one byte). PAX now does the same.
  - Not predicted: a signal key's flush also discards the echo its own write made and nothing
    else (C31), and pelt's line editor leaves raw mode between its cursor query and its prompt,
    so the driver waits 0.3 s before typing (S|1 read `sstty` on PAX's first run).
  - Not predicted: TIOCGPTN, TIOCSPTLCK and TIOCGPTLCK on a terminal are -ENOTTY on Linux; PAX
    first refused them by name.

## 4. What is not done

- **The 860 (contract item 4).** No metal run here. The first metal check should look for:
  `ls -l /dev/ptmx /dev/pts` on the installed system's console (crw-rw-rw- 5,2; the directory
  with `ptmx` alone); `script`-like use is not shipped, so the check is a pty opened by a
  program: `sudo -u pax pelt -c 'tty'` prints `/dev/ttyS0` (the console) today and will print
  `/dev/pts/0` only under bw05's ssh server; once burrow's bw05 lands, `ssh 860` from another
  machine opening pelt (`tty` says `/dev/pts/0`, a resize of the client's window redraws
  pelt's line, Ctrl-C ends a `sleep`, closing the client ends pelt and leaves
  `/proc/sys/kernel/pty/nr` at 0).
- epoll's edge-triggered counts for a pty: level-triggered only (the mask, no counts).
- `chown` and `chmod` of `/dev/pts/N` (an ssh server gives the slave to the user it logs in):
  refused by name as every `/dev` node's; bw05's server needs them or opens the pty after
  dropping to the user.
- `TIOCSIG`, `TCXONC` (tcflow), `TIOCEXCL`, `TIOCCONS`, `TIOCSETD`, `vhangup`: refused by name
  (R-px111-8).
- The Linux side is recorded on a lane host, not re-run on the hosted runner (its references
  are committed; no row needs a fixture staged on a lane host).

## 5. Evidence index

(filled at the prepared head)
