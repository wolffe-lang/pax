# px49 — The small gaps, and the pelt and boreutils pins

Contract: px49's, `sprints/pax/49-the-small-gaps/px49-the-small-gaps.md`
in wolffe-lang/wolf (planning commit `9b3c382`, read 2026-10-17),
launched as px48's follow-on (crawl 54, "px48 merged; px49 launched"),
under px48's "Forbidden / rules" word for word but where px49 changes
them, and the rules of `sprints/crawl-54.md` and `sprints/wave-53.md`
down to `wave-45.md`. Branch `px49` in pax, cut from pax trunk
`6d4072c` (px48). §1 to §3 are committed before the first change to the
kernel, a tool, a probe, a test or a pin, and before the first
measurement.

Two deliverables. **(A) Nine small kernel gaps**, each measured
black-box against Linux, root and user: pax#58 (`fstat`'s owner of an
AF_INET or TCP socket, an eventfd, an epoll object and an end `accept`
made), #60 (`faccessat2`'s AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH), #63
(`fallocate`'s other modes), #70 (a user's `unlink("/dev")`), #71
(`mpx3-shell` procs-user gets a row a broken `as` turns red, planted),
#73 (`pause`), #74 (TIOCSTI, TCFLSH, TCSBRK on the console), #75
(`rt_sigsuspend` across a stop and when another thread takes the
signal; Linux measured first), #76 (SIGTTOU for a background group's
`sendfile`/`splice` to the console under TOSTOP). **(B) Pin bumps**:
pelt to `1102498` (sh17; static `07bb5156…`, rebuilt and read twice)
and boreutils to `8f0bbb1` (bu25; static cat release `1f00ef21…`).

## 1. Forbidden, absolutely

px48's §1, unchanged but for the lane's name and paths, and these:

- No kernel's, libc's, shell's or terminal driver's source is read, nor
  `su`/`login`/util-linux/procps source (ruling #22). Facts come from
  the man pages (`pause(2)`, `sigsuspend(2)`, `signal(7)`,
  `ioctl_tty(2)`, `TIOCSTI(2const)`, `TCFLSH(2const)`,
  `TCSBRK(2const)`, `tcflush(3)`/`tcdrain(3)` in `termios(3)`,
  `sendfile(2)`, `splice(2)`, `fallocate(2)`, `access(2)`/`faccessat2`,
  `unlink(2)`, `stat(2)`, `socket(7)`, `eventfd(2)`, `epoll_create(2)`,
  `accept(2)`, `credentials(7)`), POSIX.1-2024 (XSH `pause`,
  `sigsuspend`, `tcflush`, `tcdrain`, `tcsendbreak`, `faccessat`,
  `unlink`; XBD 11.1.4), the allowed uapi headers, pax's own source,
  px38's to px48's notes, sh17's and bu25's notes.
- A Linux answer nobody recorded is measured black-box: real root is
  kasumi's own kernel image under QEMU with a static program as pid 1
  (px48's `vmjob` way, the probe on a pseudo-terminal as its session
  leader); a rootless container only for a user's rows.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals go only to processes the test started.
- Probe binaries static, built in `px13-ubuntu`, never with kasumi's
  CachyOS glibc. No build on nomad-1. kasumi and hasu under `bash`
  (hasu `env bash`), long jobs `setsid` with a pid file, ended by that
  pid only; work under `~/lanes/px49/`, pruned; never `/tmp`. Process,
  signal and terminal tests also under `taskset -c 0-3`; SigBlk and
  SigIgn read before a signal row is called red. Ports 8080 and 8088
  unused; nothing installed; hasu's maintainer data and :9308
  untouched.
- `cat`'s input-is-output refusal is dark on PAX (no `/proc/self/fd`
  links): recorded, and `/proc/self/fd` is not added in this lane.
- No `rm` outside `~/lanes/px49/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer. No other lane's run
  cancelled; plants by dispatch for one suite. A pin bump is a full-tier
  change: `full-matrix` only once the head is final. If the harness
  refuses an action I stop and report.

## 2. Inputs, verified (2026-10-17)

| input | found |
|---|---|
| pax trunk | `6d4072c` (px48, PR #72 merged), the contract's; no pax PR open |
| planning repo | `9b3c382` (the contract and crawl 54's px48 entry) |
| px48's note | §4 inferred: an open of the console taking it, `tcsetattr` from an orphaned group, **`rt_sigsuspend` ended by a stop and by another thread's take** (pax#75), pause -ENOSYS (pax#73), TIOCSTI/TCFLSH/TCSBRK refused (pax#74), sendfile/splice skip TOSTOP (pax#76); its tools `--nsproc`, `--rdev`, `notes/px48/vmjob.c`, `linux-vm.sh` |
| `rt_sigsuspend` today | `kernel/sched` `suspend_current`: state SUSPEND, -EINTR in the frame, the old mask in `ssold`; `kernel/signal` `on_return` lets the thread go (`suspend_over`) whenever it comes back to ring 3 with nothing to take: after a stop it took at its default (a blocked stop the suspend mask unblocked), and when it was woken for a process signal another thread then took |
| `pause` (34) | -ENOSYS (`tests/mpx5-users`' sig targets wait in it: px45's U2 names it) |
| the console's ioctls | TCGETS, TCSETS*, TIOCGWINSZ, TIOCSWINSZ, the controlling-terminal five (px48), the speaker's two; everything else refused by name (`console.REFUSED`), TIOCSTI (0x5412), TCFLSH (0x540b), TCSBRK (0x5409) among them |
| the background rule | `console.job(J_WRITE)` is asked by `write` only (`kernel/user`); `files.sendfile` and `files.splice` write the console with `console.put_kernel` and ask nothing |
| `fstat`'s owner | `files.n_owner`: an inode's, a pipe's and a socketpair's (`P_OWNER`), an AF_UNIX socket's (`unix.owner`), /proc's; 0:0 for an AF_INET datagram socket (K_INET), a TCP block (K_TCP, made by `socket` or by `accept`), an eventfd, an epoll object. The open-file record has 8 words, 7 used (word 7 free) |
| `faccessat2` | `files.faccessat`: any flag but AT_EACCESS -EINVAL |
| `fallocate` | `files.fallocate`: mode 0 only; any other refused by name (`R_FALLOC`), -EOPNOTSUPP |
| `unlink("/dev")` | `files.unlinkat`: `unname` asks the directory only when both it and the name are the tree's inodes, so `/dev` (and `/proc`, `/sys`) answer -EISDIR to anyone before any check |
| procs | `user/elf/procs.c` prints no id a user's run would change (px47 §C: "procs asks nothing a user is refused") |
| pelt | `1102498` (sh17's last code commit; trunk `c435b9a` adds notes only after it, `git diff 1102498 c435b9a -- src wolf-toolchain.toml` empty); from `06223a8`: `src/` +1407 −138 in 11 files (aliases, `hash`/`type`/`command`, `$'…'`, `pipefail`, option clusters, `read`'s corners); `wolf-toolchain.toml` unchanged; sh17's static build at pax `5c36560`'s `tools/mkpelt` with `ld.lld`: `07bb5156…`, 15,047,176 bytes; `tools/mkpelt` unchanged between `5c36560` and `6d4072c` |
| boreutils | `8f0bbb1` (bu25); from `23ea8dd`: `src/cat.lu` +16 −2, `src/bore/inout.lu` new (203 lines), `src/inout_test.lu` new; `wolf-toolchain.toml` unchanged; bu25's static cat (px12-ubuntu, `-static`): release `1f00ef21…0790`, dev `b9f8276b…03ed`; on Linux cat asks `statx("/proc/self/fd/1")`, `/proc/self/fdinfo/1`, `statx(path)` per operand, `lseek(SEEK_CUR)` |
| `/proc/self/fd` on PAX | listed (px45) but a lookup of an entry is -ENOENT (`files` "a descriptor's link is listed, not followed"), so cat's check finds nothing to compare |
| kasumi | Linux 7.2.8-1-cachyos, `/home` 32 GB free, `px13-ubuntu` `ad8964505189`; `dev.tty.legacy_tiocsti` 0 |
| open issues | pax#55, #56, #58, #60, #62, #63, #67, #70, #71, #73, #74, #75, #76 |

## 3. Prediction (committed before the first change and measurement)

**P1. Where the rows live.** One new probe, `user/elf/gaps.c` (built by
`tools/mkjobs` beside `jobs`), asks #58, #60, #63, #73, #74, #75 and
#76, as root and as 1000:1000 (through `as`), in a fourth image of
`tests/mpx5-jobs` (`gaps`), each run held byte-identical to real root's
guest recording (`tests/mpx5-jobs.d/linux/gaps.tty`, `gaps-user.tty`)
and the user's also to the container. The guest's `vmjob` brings the
loopback up first (px49's copy, named) so `accept` has a peer. #70 is a
row of `user/elf/tree.c` (`tests/mpx3-tree`, probes and probes-user:
the container's `/` is root's 0755, as PAX's is, ruling #85), and its
root answer is measured on real root's guest by `gaps` too. #71 is a
`creds` row of `user/elf/procs.c` and a new check in `tests/mpx3-shell`
that asks each side's own answer.

**P2. Linux's answers** (man pages and POSIX; measured before the
kernel is written to them; where my guess is weak I say so):

- *#73 pause.* -EINTR only after a handler ran; not ended by an ignored
  signal, a SIGCHLD or SIGCONT at their default, nor by a stop and a
  continue; SIGKILL ends the process. PAX: `pause` is
  `rt_sigsuspend` with the caller's own mask.
- *#75 rt_sigsuspend.* (a) SIGSTOP then SIGCONT to a suspended process:
  it keeps waiting, and a later SIGUSR1 with a handler ends it (-EINTR);
  (b) a SIGTSTP blocked and pending, then `sigsuspend` with an empty
  mask: the process stops; SIGCONT: it keeps waiting; (c) two threads,
  B (the main thread) and A in `sigsuspend`; process-directed SIGUSR1s
  with a handler: A returns only when its own handler ran ("returned
  without its handler" 0 of N). PAX today: (a) right (a SUSPEND thread
  is not readied by a stop or a continue), (b) and (c) wrong (-EINTR
  with no handler). Fixed in `kernel/signal`: a thread leaving
  `rt_sigsuspend` with no handler run and its process not ending goes
  back to its wait (the same mask, the same saved mask).
- *#74.* TIOCSTI (0x5412) with `dev.tty.legacy_tiocsti` 0: root (it has
  CAP_SYS_ADMIN) 0, the byte read back as if typed; a user -EIO. TCFLSH
  (0x540b): TCIFLUSH (0) discards what was typed and not read (a read
  after it waits; nonblocking -EAGAIN), TCOFLUSH (1) and TCIOFLUSH (2)
  0, any other -EINVAL; from a background group SIGTTOU as TCSETS
  (`tcflush(3)`). TCSBRK (0x5409): a non-zero arg (`tcdrain`) 0; arg 0
  (`tcsendbreak`) 0 after about a quarter of a second on a serial line,
  and on a pseudo-terminal 0 at once — weak guess; from the background
  SIGTTOU (weak). PAX: TIOCSTI goes through the line discipline's
  input (echo, ISIG, editing), TCFLSH TCIFLUSH empties the queue,
  TCSBRK answers 0 (the console's writes are synchronous: nothing to
  drain; no break is put on COM1, named).
- *#76.* `sendfile` from a file and `splice` from a pipe to the
  controlling terminal by a background group with TOSTOP: SIGTTOU (the
  group stops; when continued and still in the background, again);
  with SIGTTOU ignored: written; without TOSTOP: written. PAX: both ask
  `console.job(J_WRITE)` before they write the console.
- *#58.* An AF_INET datagram socket, a TCP socket, and the end `accept`
  makes: the **maker's file-system ids** (the acceptor's for an
  accepted end), as px43 measured for a pipe and a socketpair. An
  eventfd and an epoll object: **0:0** whoever makes them (an anonymous
  inode is one inode, the kernel's) — so PAX's 0:0 is already right for
  those two (weak guess; if Linux gives the maker's, PAX follows). PAX:
  the open-file record's free word 7 keeps the maker's file-system ids
  for K_INET and K_TCP; `n_owner` reads it.
- *#60.* `faccessat2(AT_SYMLINK_NOFOLLOW)` asks of a link itself (its
  0777 mode, so every mode is 0 for anyone, a dangling link's F_OK 0);
  without the flag the target's answer; `AT_EMPTY_PATH` with `""` asks
  of the descriptor's file (a user: a 0600 root file it holds open by an
  inherited descriptor is -EACCES for R_OK), without the flag `""`
  -ENOENT; another flag still -EINVAL.
- *#63* (on the guest's root, tmpfs). FALLOC_FL_KEEP_SIZE (1): 0, the
  size unchanged; PUNCH_HOLE|KEEP_SIZE (3): 0, the range reads as zero,
  the size unchanged; PUNCH_HOLE alone (2): -EOPNOTSUPP; ZERO_RANGE
  (0x10), COLLAPSE_RANGE (8), INSERT_RANGE (0x20), UNSHARE_RANGE
  (0x40): -EOPNOTSUPP on tmpfs; COLLAPSE or INSERT with KEEP_SIZE:
  -EINVAL; an unknown bit: -EOPNOTSUPP. Each served mode takes a user's
  set-ID bits as a write does (weak). PAX: KEEP_SIZE checked and served
  (no space is set aside: named, as for mode 0), PUNCH_HOLE|KEEP_SIZE
  writes zeros over the range inside the size; the rest Linux's answer,
  no longer refused by name.
- *#70.* `unlink("/dev")`, `unlink("/proc")`, `unlink("/sys")`: root
  -EISDIR, a user -EACCES (the directory's write and search asked
  first, `unlink(2)`). PAX: `unlinkat` asks `/`'s write and search
  before -EISDIR for a name that is no inode of the tree.
- *#71.* procs' new line `creds: …` (getresuid, getresgid) is root's
  0s in `procs` and 1000s in `procs-user`, on both sides; a new check
  holds each side's own line to the user's ids, so plant B (`as` keeps
  root's uid: px47's `13f690c`) is red there and green in S2.

**P3. The counts.** `gaps` about 60 lines, byte-identical to real root's
guest as root and as 1000:1000 at the first PAX boot after the fixes,
but for lines named before that boot; the first PAX boot of `gaps` on
trunk's kernel (before any fix) differs in the rows of all nine items
but #58's eventfd/epoll and #75(a). `tree` gains one line on both sides;
`procs` one.

**P4. The pins.** `tools/mkpelt` at `1102498` in `px13-ubuntu` builds
`07bb5156…` (15,047,176 bytes), twice and in CI; `tools/mkboreutils`
builds `cat` as `1f00ef21…` (release, 13,952,560 bytes) and every other
utility to its trunk digest unchanged (no other `src/` file moved). **No
compared session moves** with either pin: nothing PAX types asks an
alias, `type`, `command -v`, `$'…'`, `pipefail` or `read`'s corners,
and cat's new calls on PAX find no `/proc/self/fd/1` and refuse nothing
(and print no `refused:` line: `statx` of a missing name is -ENOENT).
cat's refusal is dark: `cat f >> f` on PAX copies (Linux refuses,
"input file is output file", status 1): recorded once, in this note,
not in a compared session. Falsified by any compared session's text
moving.

**P5. Existing suites.** Every suite green as root and as a user, text
moving only where named: `tests/mpx5-users`' sig targets' `pause`
answered (its `-ENOSYS` allowance for 34 goes); `mpx5-jobs`' probe
untouched; `mpx3-tree`'s and `mpx3-shell`'s one new line each.

**P6. Plants**, each a CI run of its own on a branch never merged:
A, `as` keeps root's user ids (px47's plant B, re-cut on this head):
`mpx3-shell` red at the new procs-user check only, S2 green; B, the
re-suspend removed (the thread let go with -EINTR as before): `mpx5-jobs`
red first at #75's (b) row in `gaps`, as root and as a user.

**P7. What it costs.** Under 6 KiB of kernel text native; no table and
no record grows (the open file's word 7 was free).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | one probe (`gaps`) in a fourth image of `mpx5-jobs`, root and 1000:1000, held to real root's guest (px49's `vmjob`, the loopback up) and the user's to the container; #70 a `tree` row, #71 a `procs` row and a check that asks each side | so, but the gaps image boots **kmain_session**, not kmain_console: on trunk's kmain_console (which starts no network stack) the probe's `connect` to 127.0.0.1 waited for good (`build/t0`'s boot, `prompt 2 … did not come within 900s`), so the image takes the session kernel (the console as kmain_console's, the network as kmain_sockets') and `mpx5-jobs` builds both. Not predicted: `/sys` mounted in the guest too (for root's `unlink("/sys")`) | right (one kernel more) |
| P2 | Linux's answers (§3's list) | every row as predicted but **two**: `fallocate`'s COLLAPSE_RANGE\|KEEP_SIZE and INSERT_RANGE\|KEEP_SIZE are -EOPNOTSUPP on tmpfs, not -EINVAL. The weak guesses held: eventfd and epoll 0:0; TCSBRK(0) 0 at once on a pseudo-terminal; TCFLSH, TCSBRK(1) and TCSBRK(0) from the background stopped by SIGTTOU; a user's set-ID bits taken by every served mode, past the end too. Not predicted: TIOCSTI by root into a terminal that is not its own is 0 (the byte arrives); a user's TIOCSTI is -EIO before its pointer is read; an output flush on a pseudo-terminal discards lines its reader has not taken (the container lost three, §C); in a user namespace the anonymous inode reads 65534:65534 (§E) | wrong (2 rows) |
| P3 | `gaps` about 60 lines, byte-identical at the first boot after the fixes; trunk's kernel differs in every item but #58's eventfd/epoll and #75(a); one line each in `tree` and `procs` | **103** lines; the first boot of the branch (`b1`, native) byte-identical as root and as 1000:1000; trunk's 49 of 103 lines differ, in every item but #58's eventfd and epoll rows, #75(a) and #70 (root's `unlink` is -EISDIR before and after: the user's row is `tree`'s, red on trunk, §J); `tree` and `procs` one line each | right (but the line count) |
| P4 | `07bb5156…` (15,047,176) and `1f00ef21…` (13,952,560), twice and in CI; no compared session moves; cat's refusal dark, `cat f >> f` copies | both digests in `mpx3-shell`'s and `mpx3-tree`'s builds on kasumi (two builds) and CI's (§I); no compared session moved on kasumi (`mpx3-shell`, `mpx3-tree`, `mpx3-speaker`, `mpx5-accounts`, `mpx3-boreutils`, `mpx3-console`, `mpx3-screen`) nor in CI; on PAX `cat /cf >> /cf` **did not end in 600 s** (it reads what it appends, without end), where the container's cat refused it (`input file is output file`, status 1) | right ("copies" understated: without end) |
| P5 | every suite green as root and as a user; `mpx5-users`' allowance for 34 goes | so (`mpx5-users`' sig U2: `-ENOSYS only for 273 334`; its rows unchanged) | right |
| P6 | plant A red in `mpx3-shell` at the new check only, S2 green; plant B red first at #75's (b) row | §K | see §K |
| P7 | under 6 KiB of text native; no table and no record grows | kmain_console native `.text` 907,083 → **910,171** (+3,088), kmain_session 909,835 → 912,923 (+3,088); release −18,512 (kmain_console) and +14,192 (kmain_session), the release tier's inlining; `.rodata` −80, `.data` and `.bss` the same; the open file's free word 7 (`notes/px49/kasumi-kernel-cost.txt`) | right (native; release not predicted) |

## A. pause (pax#73, item 6)

`pause` (34) is `rt_sigsuspend` with the caller's own mask
(`kernel/user`): it answers -EINTR only after a handler ran, and waits
through SIGCHLD and SIGURG at their default, SIGCONT to a running
process, an ignored signal, and a stop and a continue; SIGKILL ends it.
Measured (`P` of `gaps`, real root's guest and PAX, root and 1000:1000,
byte-identical). Trunk answered -ENOSYS at once (the child reported it
on every round). `tests/mpx5-users`' sig targets, which wait in `pause`,
no longer spin: sig's 99 of 102 rows as before, its -ENOSYS list `273
334`.

## B. rt_sigsuspend across a stop and another thread's take (pax#75, item 8)

Measured on Linux first (`U` of `gaps`, this lane's first guest boot,
`notes/px49/linux-first-gaps*.txt`): (a) SIGSTOP and SIGCONT to a child
waiting in `sigsuspend`: it keeps waiting, and a later SIGUSR1 with a
handler ends it (-EINTR); (b) a SIGTSTP blocked and pending at its
default, then `sigsuspend` with an empty mask: the child stops; SIGCONT:
it keeps waiting; (c) two threads, A in `sigsuspend` and B (the main
thread) sending the process SIGUSR1 while blocking it and then
unblocking it, 20 rounds: each signal handled once, and A **never**
leaves `sigsuspend` without its own handler (0 of 20); a `tgkill` to B
leaves A waiting.

PAX's trunk: (a) right (a SUSPEND thread is not readied by a stop or a
continue), (b) `sigsuspend returned EINTR, with no handler run` at the
SIGCONT, (c) 20 of 20 returns without A's handler (A was woken as the
signal's taker, B took it first, A found nothing and was let go). The
fix is one rule in `kernel/signal`'s `on_return`: a thread on its way
back to ring 3 from `rt_sigsuspend` (W_SUSPEND) with nothing to take
goes back to its wait (`sched.resuspend`: state SUSPEND, the same frame
with -EINTR in it, the same mask and the same mask to put back), so
only a handler (or the process's end) lets it go. px48's `suspend_over`
is gone. Measured: `U`, byte-identical as root and as 1000:1000.

## C. TIOCSTI, TCFLSH and TCSBRK (pax#74, item 7)

| request | Linux (real root's guest, a pseudo-terminal; kasumi's `dev.tty.legacy_tiocsti` 0) | PAX (`kernel/console`) |
|---|---|---|
| TCFLSH (0x540b) | the background rule first (SIGTTOU, as TCSETS); TCIFLUSH discards a typed line not read (a read after it: 0 bytes); TCOFLUSH, TCIOFLUSH 0; 3 -EINVAL | the same; TCIFLUSH and TCIOFLUSH empty the input queue and the line being edited; TCOFLUSH has nothing to discard (the console writes as it is asked) |
| TCSBRK (0x5409) | after the background rule (SIGTTOU for arg 1 and arg 0): `tcdrain` 0, `tcsendbreak` 0 at once | the same; no break is put on COM1 (named) |
| TIOCSTI (0x5412) | root: 0, the byte read back as typed, also into a terminal that is not its own (a child in a session of its own put `w` in main's input); a bad pointer -EFAULT; a user: -EIO before anything else | the same: `dev.tty.legacy_tiocsti` 0 is PAX's fixed setting; the byte goes through the line discipline's `input`; a key that raises a signal raises it at the next interrupt (named) |

**An output flush on a pseudo-terminal discards what its reader has not
taken**: the container's first run lost the three lines printed just
before TCOFLUSH (`notes/px49/container-first-gaps-user.txt`), which the
guest's faster reader had taken. The probe waits 1.5 s before each
output flush. PAX's console has no output queue: nothing is lost.

**A host that lets a user TIOCSTI.** The container's user is refused
TIOCSTI only where its host's `dev.tty.legacy_tiocsti` is 0 (kasumi's;
the guest's own kernel too). A CI runner whose kernel says 1 would let
the container's user put a byte in its terminal: `tests/mpx5-jobs`
reads the host's setting and, when it is not 0, leaves `gaps-user`'s
TIOCSTI rows out of the container's comparisons (J0, J3), named; J7
holds PAX to real root's recording all the same.

Measured: `I` of `gaps`, byte-identical as root and as 1000:1000.

## D. sendfile and splice from the background under TOSTOP (pax#76, item 9)

`sendfile` from a file and `splice` from a pipe to the controlling
terminal by a background group: without TOSTOP written; under TOSTOP the
group is stopped by SIGTTOU, and again when continued in the background;
given the foreground and continued, the call runs again and writes; with
SIGTTOU ignored, written (Linux measured, `B` of `gaps`). PAX's
`files.sendfile` and `files.splice` now ask `console.job(J_WRITE)`
before they write the console, as `write` does; its `JOB_STOP` rewinds
the call (px48's). Trunk wrote at once under TOSTOP (`B: sendfile under
TOSTOP: sendfile answered its count`). Measured: `B`, byte-identical.

## E. fstat's owner of sockets, an eventfd and an epoll object (pax#58, item 1)

Root, making each object under `setfsuid(1001)`/`setfsgid(2001)` (a
listener under 1001, a client under 1002, the `accept` under 1003), and
a user (all 1000:1000): an AF_INET datagram socket, a TCP socket, the
client end and the end `accept` made are the **maker's file-system
ids** (the acceptor's, 1003:2003, for the accepted end), as px43
measured for a pipe; an eventfd and an epoll object are **0:0** on real
root's guest (an anonymous inode is one, the kernel's) and **65534:65534**
in the container (the host's root, unmapped in its user namespace: the
overflow id), so the probe prints for those two only that they are not
the maker's. PAX keeps the maker's file-system ids in the open file's
free word 7 (`O_OWNER`) for K_INET and K_TCP (`files.owned`, set where
`socket` and `accept` make the descriptor); `n_owner` finds the one open
file that names the socket. An eventfd and an epoll object stay 0:0, as
Linux's. Trunk: every socket 0:0. Measured: `O`, byte-identical.

## F. faccessat2's AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH (pax#60, item 2)

Measured (`A` of `gaps`): AT_SYMLINK_NOFOLLOW asks of a last link itself
— its mode is 0777, so R_OK, W_OK and X_OK are 0 for root and a user
alike (with AT_EACCESS too), a dangling link's F_OK 0 (-ENOENT
following it); on a file it changes nothing (a user's R_OK of root's
0600 file -EACCES). AT_EMPTY_PATH with `""` asks the descriptor's file
(a user's W_OK of root's 0644 file -EACCES, its R_OK 0; the 1777
directory's W_OK 0; AT_FDCWD the working directory); without the flag
`""` is -ENOENT; with a name the flag changes nothing; a closed
descriptor -EBADF; the flag 0x2 -EINVAL. PAX: `faccessat` takes both
flags (`resolve_who` with `empty_ok` and F_NO for the last link). Trunk:
-EINVAL for either. Measured: `A`, byte-identical.

## G. fallocate's modes (pax#63, item 3)

On the guest's root (tmpfs), each row on a fresh 10-byte file of mode
06755 (`F` of `gaps`):

| mode | Linux | the file after | PAX |
|---|---|---|---|
| 0, KEEP_SIZE (1), KEEP_SIZE past the end | 0 | mode 0: grown; KEEP_SIZE: the size kept | served (KEEP_SIZE sets nothing aside: named, as mode 0's hole) |
| PUNCH_HOLE\|KEEP_SIZE (3), over the end, past the end | 0 | the range inside the size reads as zero, the size kept | served (`tree.punch`: the frames kept, zeroed) |
| PUNCH_HOLE alone, ZERO_RANGE (with KEEP_SIZE or not), COLLAPSE_RANGE, INSERT_RANGE (each with KEEP_SIZE or not), UNSHARE_RANGE, PUNCH_HOLE\|ZERO_RANGE\|KEEP_SIZE, the bit 0x100 | -EOPNOTSUPP | unchanged | the same, no longer refused by name (px44's `R_FALLOC` is gone) |
| KEEP_SIZE with length 0; PUNCH_HOLE\|KEEP_SIZE at -1 | -EINVAL | unchanged | the same (px44's order) |
| a pipe; a read-only descriptor | -ESPIPE; -EBADF | — | the same |

A served mode takes a user's set-ID bits as a write does, past the end
too (06755 → 0755 for the user, kept for root); a refused one keeps
them. Trunk: -EOPNOTSUPP refused by name for every mode but 0 (30
`refused:` lines in its boot). Measured: `F`, byte-identical.

## H. A user's unlink of /dev, /proc and /sys (pax#70, item 4)

`unlinkat` asked the directory's write and search (`unname`) only when
both the directory and the name were the tree's inodes, so `/dev`,
`/proc` and `/sys`, names in `/` that are not, answered -EISDIR to
anyone. Now a name in a directory of the tree that is no inode of it
asks the directory's write and search first. Root's answers measured on
real root's guest (`D` of `gaps`: -EISDIR for all three); a user's in
the container, where `/` is root's 0755 as PAX's is (ruling #85: the
guest's initramfs root is 1777, so the guest is no reference for it):
`tests/mpx3-tree`'s probes and probes-user, a new line `remove: unlink
of /dev -21, of /proc -21` (root) and `-13, -13` (the user), T1 green on
both. The container has no `/sys` (`tools/linux-tree` without `--sys`),
so the user's `/sys` is asked by neither side. Trunk's kernel with the
branch's probes-user image: `-21, -21` for the user (§J), which T1 holds
against the container's `-13, -13`.

## I. procs-user's own witness (pax#71, item 5)

`user/elf/procs.c` prints `creds: getresuid 0: R E S; getresgid 0: R E
S` after its ids; `tests/mpx3-shell`'s new **S7** holds each side's own
line, on PAX and on Linux, to root's 0s (procs, procs-quiet) or the
user's 1000s (procs-user). S2 cannot see a broken `as`: the container
runs the same `as` and agrees with itself. Plant A (§K) is red there.
On kasumi: S7 PASS on all three sessions, procs-user's S2 46 lines.

## J. The pins (items 10, 11)

`user/pelt.pin` → pelt `1102498` (sh17); `user/boreutils.pin` →
boreutils `8f0bbb1` (bu25), each its own commit. Built in `px13-ubuntu`
by the suites' own tools (`tools/mkpelt` with `ld.lld`,
`tools/mkboreutils`): pelt **`07bb5156919c1b9ceb2e97c755a377a33aee10910969d713f2d0faf3f75c2819`**,
15,047,176 bytes, and cat **`1f00ef21b92277704045004df6bcf60b099da10fa637f9155a9c189a32ef0790`**,
13,952,560 bytes, in `mpx3-shell`'s build and again in `mpx3-tree`'s
(two builds, each digest read in each; `notes/px49/kasumi-mpx3-shell.out`,
`kasumi-mpx3-tree.out`), the same as sh17's and bu25's own; CI's builds
in §L.

**What moved.** No compared session's text moved with either pin, on
kasumi (`mpx3-shell`, `mpx3-tree`, `mpx3-speaker`, `mpx5-accounts`,
`mpx3-boreutils`, `mpx3-console`, `mpx3-screen`) or in CI (every suite,
§L): nothing PAX types asks an alias, `type`, `command`, `$'…'`,
`pipefail` or `read`'s corners, and cat's new calls on PAX find no
`/proc/self/fd/1` and refuse nothing (a `statx` of a missing name is
-ENOENT, no `refused:` line). So nothing was re-recorded; the recorded
references (`tests/mpx3-speaker.d/linux/`, `tests/mpx5-accounts.d/linux/`,
`user/console/*.expect`) are held by their suites against the new
binaries and stood.

**cat's refusal, dark on PAX.** bu25's cat refuses an input that is its
output by asking `/proc/self/fd/1` and `/proc/self/fdinfo/1`; PAX lists
`/proc/<pid>/fd` (px45) but a lookup of an entry is -ENOENT, so on PAX
the check finds nothing. Recorded once, mpx3-tree's shell image
(`notes/px49/cat-dark.sh`): `echo abc > /cf`, then `cat /cf >> /cf;
echo "status $?"`. The container: `cat: /cf: input file is output
file`, `status 1`, `/cf` still `abc`. PAX: `cat` ran on, copying what it
appended, and had not ended when the 600 s ran out
(`notes/px49/cat-dark-pax.txt`, `cat-dark-linux.txt`). `/proc/self/fd`
is not added in this lane (the contract).

