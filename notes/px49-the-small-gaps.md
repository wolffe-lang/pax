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

(after the measurements)
