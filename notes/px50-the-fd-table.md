# px50 — /proc/<pid>/fd and /proc/<pid>/fdinfo (pax#78, #80, #79)

Contract: px50's, `sprints/pax/50-the-fd-table/px50-the-fd-table.md`
in wolffe-lang/wolf (planning commit `37decac`, read 2026-10-17),
launched in crawl 54's batch 6, under px48's "Forbidden / rules" word
for word but where px50 changes them (pax trunk `d0a48be` or later; the
CI share is with r36, s244 and bu26; never any kernel's procfs source),
and the rules of `sprints/crawl-54.md` and `sprints/wave-53.md` down to
`wave-45.md`. Branch `px50` in pax, cut from pax trunk `d0a48be` (px49).
§1 to §3 are committed before the first change to the kernel, a tool, a
probe or a test, and before the first measurement.

Three deliverables. **(A) pax#78**: `/proc/<pid>/fd/N` and
`/proc/<pid>/fdinfo/N` served as Linux serves them, measured black-box
— `readlink` of each entry (a file, a directory, a pipe's two ends, a
socketpair's end and the other sockets, an eventfd, an epoll object, the
terminal), `stat`/`statx` through the entry (the target's identity) and
`lstat` of it, opening through it, listing both directories, and
`fdinfo`'s `pos`, `flags` (octal, the append bit), `mnt_id` and `ino`
lines; permission as Linux (a user reads its own, not root's nor
another user's) — and the witness: boreutils' `cat` (bu25, pinned by
px49) refuses on PAX every input-is-output shape it refuses on Linux,
as root and as `pax`. **(B) pax#80**: a user's `rmdir` and `rename` of
`/proc` and `/sys` measured and matched (px49's #70 ordering). **(C)
pax#79**: why `tests/mpx4-ready`'s nbprobe row `a write of 1 then`
races on the Linux side, from evidence, and the row made deterministic,
never by a retry.

## 1. Forbidden, absolutely

px48's §1 and px49's, unchanged but for the lane's name and paths, and
these:

- **No kernel's procfs source**, nor any kernel's, libc's, shell's or
  terminal driver's source, nor `su`/`login`/util-linux/procps source
  (ruling #22). Facts come from the man pages (`proc(5)`,
  `proc_pid_fd(5)`, `proc_pid_fdinfo(5)`, `readlink(2)`, `open(2)`,
  `stat(2)`, `statx(2)`, `getdents64(2)`, `ptrace(2)`'s access modes,
  `prctl(2)` PR_SET_DUMPABLE, `pipe(7)`, `socket(7)`, `eventfd(2)`,
  `epoll_create(2)`, `rmdir(2)`, `rename(2)`, `tcp(7)`, `socket(7)`'s
  SO_SNDBUF, `ioctl_tty`-free `ioctl(2)` SIOCOUTQ/SIOCINQ in `tcp(7)`),
  POSIX.1-2024, the allowed uapi headers, pax's own source, px38's to
  px49's notes, bu25's note and boreutils' own source (the org's, not
  GNU's).
- A Linux answer nobody recorded is measured black-box: real root is
  kasumi's own kernel image under QEMU with a static program as pid 1
  (px49's `notes/px49/vmjob.c`, via px48's `notes/px48/linux-vm.sh`); a
  rootless container only for a user's rows.
- Every check gets a user row; every existing suite stays green as root
  and as a user. Signals go only to processes the test started.
- Probe binaries static, built in `px13-ubuntu`, never with kasumi's
  CachyOS glibc. No build on nomad-1. kasumi and hasu under `bash`
  (hasu `env bash`), long jobs `setsid` with a pid file, ended by that
  pid only; work under `~/lanes/px50/`, pruned; never `/tmp`. Process,
  signal and terminal tests also under `taskset -c 0-3`; SigBlk and
  SigIgn read before a signal row is called red. Ports 8080 and 8088
  unused; nothing installed; hasu's maintainer data and :9308
  untouched.
- No `rm` outside `~/lanes/px50/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer. No other lane's run
  cancelled; plants by dispatch for one suite. `full-matrix` only once
  the head is final. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-17)

| input | found |
|---|---|
| pax trunk | `d0a48be` (px49, PR #77 merged), the contract's; no pax PR open |
| planning repo | `37decac` (batch 6's contracts) |
| open issues | pax#55, #56, #62, #67, #78, #79, #80 |
| `/proc/<pid>/fd` today | `kernel/procfs`: entry PFD (0500, the process's effective ids while dumpable), and FDENT + n per descriptor, mode S_IFLNK\|0700 whatever the access mode; `kernel/files` lists them (`getdents`) but `syn_child` answers every lookup in it -ENOENT ("listed, not followed") |
| `/proc/self/fd` today | **absent**: `/proc/self` is a directory of fixed entries (status, cgroup, setgroups, cmdline, environ, stat), so `/proc/self/fd` is -ENOENT before any entry is asked |
| `fdinfo` today | absent, `/proc/<pid>/fdinfo` and `/proc/self/fdinfo` -ENOENT |
| `readlinkat` today | `/proc/self/exe` and the tree's own links; anything else -EINVAL |
| the open file | 8 words (refs, kind, node, offset, flags, words 5–6 a `/proc` file's text, word 7 a socket's maker): words 5–7 are unused by K_FILE and K_DIR |
| a file's name | the tree keeps names in directories (`name_of(d, c)`) and a directory's parent; a file has no parent word (hard links), so nothing says by which directory an open file was opened |
| a user's `rmdir`/`rename` of `/proc`, `/sys` today | `rmdir("/proc")`: `unname` asks nothing of a name that is no inode, then `tree.rmdir` looks `proc` up in `/` and finds nothing: **-ENOENT to anyone**; `rename("/proc", …)` and onto `/proc`: **-EXDEV to anyone** before any check |
| nbprobe | `user/net/nbprobe.c`: after `send` until -EAGAIN on an accepted, non-blocking TCP end over loopback, `write(s, "z", 1)` printed; run 39058414358 attempt 1, the container's Linux said `1` where every recording since px24 says `-EAGAIN` |
| bu25's `cat` | boreutils `8f0bbb1` `src/bore/inout.lu`: when `fstat(1)` is a regular file, `stat("/proc/self/fd/1")` (followed) and, per operand, `stat(path)` (or `stat("/proc/self/fd/0")` for `-`), compared by `dev` and `ino`; the `flags:` line of `/proc/self/fdinfo/1` read as octal, bit 02000 the append; `lseek(fd, 0, SEEK_CUR)` of the input and of 1. No `/proc/self/fd/1`: nothing refused |
| boreutils' shapes | `tests/inout/cases.toml`, 52, run under bash with `dd` helpers (`in_at`, `out_at`); PAX's shell image has pelt and boreutils' twenty-odd utilities, no `dd` |
| kasumi | Linux 7.2.8-1-cachyos, `/home` 28 GB free, `px13-ubuntu` `ad8964505189`; man-pages 6.19 |

## 3. Prediction (committed before the first change and measurement)

**P1. Where the rows live.** One new probe, `user/elf/fdtab.c` (built by
`tools/mkjobs` beside `jobs` and `gaps`), in a fifth image of
`tests/mpx5-jobs` (`fds`, kmain_session, as gaps: its socket rows need
the network stack), run as root and as 1000:1000 through `as`, each run
held byte-identical to real root's guest recording
(`tests/mpx5-jobs.d/linux/fds.tty`, `fds-user.tty`) and the user's also
to the container; host-dependent numbers (inode numbers, `mnt_id`, the
terminal's name) printed by rule, never by value (`pipe:[its fstat
st_ino]`, "the same mnt_id as …"). #80's rows are rows of the same probe
on the guest, whose `/` is made root's 0755 first (PAX's root is root's
0755, ruling #85; the guest's initramfs root is 1777) and which has
`/sys` mounted (px49's vmjob), so a user's `rmdir`/`rename` of `/proc`
and `/sys` is measured on real Linux, not only in a container without
`/sys`. **cat's refusal** is a typed session in `tests/mpx3-tree`'s
shell images (`shell-inout`, root, and `shell-inout-user`, after `su
pax`), boreutils' shapes rewritten for pelt and the image's utilities
(`read` and `echo -n` move the offsets where boreutils' cases use `dd`),
held byte-identical to the same session in the container (T1), as the
other typed sessions are.

**P2. Linux's answers** (man pages; measured before the kernel is
written to them; weak guesses said so):

- *readlink.* A file: its absolute path; renamed while open: the new
  name; unlinked while open: the path and ` (deleted)`; a directory:
  its path; `/dev/null`, `/dev/zero`, `/dev/tty`: those paths; a pipe's
  ends `pipe:[I]`, a socketpair's end, a UDP socket, a TCP socket and
  an AF_UNIX path socket `socket:[I]`, I the descriptor's `fstat`
  `st_ino`; an eventfd `anon_inode:[eventfd]`, an epoll object
  `anon_inode:[eventpoll]`; a buffer of 3 gets 3 bytes, no NUL; a
  buffer of 0 -EINVAL; a closed descriptor's entry -ENOENT.
- *lstat of an entry.* S_IFLNK, owner the process's effective ids, size
  64, link count 1; mode by the access mode — 0500 for O_RDONLY, 0300
  for O_WRONLY, 0700 for O_RDWR (weak: it could be 0700 for all, PAX's
  today).
- *stat and statx through it*: the target's `dev`, `ino`, mode, `rdev`
  and size, the same as `fstat` of the descriptor, for every kind.
- *Opening through it*: a file opens afresh (offset 0, the flags asked,
  its own offset), for writing too when the opener may write the file,
  whatever the descriptor's own access; a path through a directory's
  entry (`fd/N/name`) reaches the directory's file; a pipe's end opens
  as the end asked (O_RDONLY through the write end reads what is
  written); a socket -ENXIO; an eventfd and an epoll object -ENXIO
  (weak); O_NOFOLLOW -ELOOP; `fd/01` -ENOENT (weak).
- *Listing*: `.`, `..`, then each open descriptor in increasing order
  (the listing's own descriptor among them); `fdinfo/` the same names.
- *fdinfo/N*: `pos:\t<n>\nflags:\t0<octal>\nmnt_id:\t<n>\nino:\t<n>\n`
  (`proc_pid_fdinfo(5)`). `flags`: the access mode and the status flags,
  O_LARGEFILE (0100000) for every file and directory `open` made
  (x86-64), O_APPEND 02000, O_NONBLOCK 04000, O_CLOEXEC 02000000 while
  FD_CLOEXEC is set (moving with `fcntl`), O_CREAT, O_EXCL and O_TRUNC
  not kept; a pipe's ends 00 and 01 (no O_LARGEFILE, weak); `pos` the
  open file's offset, shared by a `dup`; `mnt_id` one number for every
  file of `/`, another for `/proc`'s (weak: the same as `/proc`'s for
  a pipe or a socket is not asked); `ino` the `fstat` `st_ino`. An
  eventfd adds `eventfd-count:` (hexadecimal) and perhaps an id line
  (weak); an epoll object with nothing registered adds nothing.
- *Permission.* `fd/` and `fdinfo/` are the process's (its effective
  ids while dumpable, root's when not), `fd/` 0500, `fdinfo/` 0500
  (weak: 0555), `fdinfo/N` 0400 (weak: 0444, `proc_pid_fdinfo(5)` says
  readable only by the owner); `readlink`, a walk through and `fdinfo`
  are `ptrace(2)`'s read mode with the file-system ids
  (`proc_pid_fd(5)`): root reads anyone's; 1001 reads its dumpable
  sibling's (1001); 1001 is told -EACCES for root's process, for
  1002's, and for a non-dumpable 1001 sibling's; a user opening,
  through its own entry, a pipe another user made (0600, that user's)
  is told -EACCES (`proc_pid_fd(5)`'s example).
- *#80.* root: `rmdir("/proc")`, `rmdir("/sys")` -EBUSY (mount points),
  `rename("/proc", "/pq")`, `rename("/sys", "/sq")` and a directory
  renamed onto `/proc` -EBUSY (weak: -EXDEV); a user, `/` root's 0755:
  -EACCES for each, before what the name is.
- *#79.* The cause, predicted: Linux's loopback TCP moves bytes from
  the sender's queue to the receiver's after `send` has returned
  -EAGAIN (the receiver's acknowledgement frees send buffer, and its
  receive buffer grows), so a `write` a moment later can find room; on
  a 4-vcpu CI runner that happens between the two calls now and then.
  The witness: SIOCOUTQ and poll(POLLOUT) sampled after the first
  -EAGAIN, in a loop of many rounds under `taskset -c 0-3`, showing
  room coming back after -EAGAIN. The fix: the probe sends until the
  end has stayed unwritable for a settling wait (poll(POLLOUT) with a
  timeout answering 0, after the last -EAGAIN), then asks `write` of 1;
  the row's text unchanged (`-EAGAIN`), so no recording moves; on PAX
  the wait answers at once with nothing ready (its loopback is
  synchronous). 0 of N rounds racy after the fix.

**P3. PAX's change.** `kernel/procfs`: `fdinfo` (a directory) and its
entries; `/proc/self/fd` and `/proc/self/fdinfo` the caller's; the
entries' modes. `kernel/files`: a lookup in `fd/` or `fdinfo/` finds an
open descriptor's entry; a walk FOLLOWS an fd entry (it is a magic link:
not text but the descriptor's own node, after `ptrace(2)`'s read check)
as it follows a link, so `stat`, `open` and a walk through it reach the
target; `readlinkat` answers the entry's text (a file's path: the open
file keeps the directory it was opened in, held, in its free word 5,
and the name is that directory's for the inode; a removed name ` (deleted)`
— the name kept by the open file when its last name goes); `fdinfo/N`'s
text made at open from the descriptor; `rmdir`/`rename` of `/proc` and
`/sys` as `/dev`'s (px47). Under 8 KiB of kernel text native; the open
file stays 8 words.

**P4. The counts.** `fdtab` about 120 lines, byte-identical to real
root's guest as root and as 1000:1000 at the first PAX boot after the
fixes, but for lines named before that boot; trunk's kernel differs in
nearly every row (every lookup -ENOENT) but the closed descriptor's,
`readlink` size 0 and `fd/01`. The inout sessions: about 40 shapes
each; on trunk's kernel every shape Linux refuses is copied on PAX (the
`f >> f` ones without end: cut by `ulimit`-free means — the session is
run on trunk only for the shapes that end, named), after the fix every
line identical as root and as `pax`.

**P5. Existing suites.** Every suite green as root and as a user, text
moving only where named: `mpx5-users`' rights rows (`fd/ … open`, the
count of entries) unchanged; `mpx3-tree`'s and `mpx3-shell`'s sessions
unchanged (none asks `/proc/self/fd`, and cat's check finds the same
answers it would on Linux); `mpx4-ready` unchanged in text.

**P6. Plants**, each a CI run of its own on a branch never merged: A,
the magic link no longer followed (trunk's -ENOENT): `mpx5-jobs` red at
fds' first row that follows, and `mpx3-tree` red at the first refused
`cat` shape — dispatched as two runs, one suite each; B, the nbprobe
fill without its settling wait (the old loop): run as a loop of the
Linux side only, red at a rate above 0 on the runner (weak: a plant of a
race may be green; if so, the witness's own counts are the evidence).

**P7. Cost.** Under 8 KiB of kernel text native; no record grows.

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | one probe (`fdtab`) in a fifth image of `mpx5-jobs` (`fds`, kmain_session), root and 1000:1000, held to real root's guest and the user's to the container, numbers by rule; #80 rows of the same probe on a guest with `/` made 0755 and `/sys` mounted; cat's refusal as two typed sessions in `mpx3-tree`'s shell images | so. Not predicted: the user's inout session leaves out the three shapes that name `/dev/null` (the container's is not the user's to open: `cat: /dev/null: Permission denied` there); the container run of `fdtab` mounts `/sys` (`--sys`); one row of the user's run (a zombie's `fd/`) is the host kernel's and is left out of the container's comparisons (§F) | right |
| P2 | Linux's answers (§3's list) | every row as predicted where the prediction was firm. The weak guesses: the access-mode bits on a link's `lstat` held (0500, 0300, 0700); `fd/01` -ENOENT held; an eventfd's and an epoll object's entry -ENXIO held **for root only** (a user -EACCES: their 0600 anonymous inode is root's); a pipe's ends `00`/`01` held; `fdinfo/` is **0555**, not 0500, and `fdinfo/N` **0444**, not 0400 (both the weak alternatives); rename of `/proc` -EBUSY, not -EXDEV. Not predicted (§A to §E): `fd/`'s size is the number of descriptors open; a directory removed while open reads `<path> (deleted)` too; O_DIRECTORY and O_NOFOLLOW stay in `flags`, O_NOCTTY does not; `/dev`'s nodes and `/proc`'s files get O_LARGEFILE; an eventfd adds `eventfd-count` (sixteen wide), `eventfd-id` and `eventfd-semaphore`, a socketpair's end `scm_fds: 0`; `fdinfo/` keeps the process's ids when it is not dumpable while `fd/` and the entries are root's; a zombie's `fd/` is its ids (on 7.2.8); a process not dumpable still enters its own root-owned `fd/`; a lookup in another's `fdinfo/` (0555) asks `ptrace(2)`'s read mode; the terminal's entry opened by a user -EACCES (the pseudo-terminal is root's); O_CREAT through an entry 0, O_CREAT\|O_EXCL -EEXIST; `rename("/proc", "/proc")` 0 for anyone; `rmdir("/proc/self/fd")` -EPERM, `rename` of `/proc/self` -EXDEV | right on every firm row; 5 weak guesses right, 3 wrong |
| P2 #79 | the cause: the peer's acknowledgement frees send buffer after `send`'s -EAGAIN, and a runner slow to the next call finds room; the fix: send again while poll(POLLOUT) says writable | the cause measured (§G): the room comes back **30 to 49 ms** after the -EAGAIN (300 of 300 rounds), the peer's delayed acknowledgement, and **POLLOUT never comes back** (0 of 300 at once, 1, 10 and 100 ms) though a write of 1 then is taken (300 of 300) with 95,231 bytes more. So the predicted fix would not have helped: nbprobe instead waits 100 ms and sends again until a send after the wait takes nothing (one more pass on Linux, none on PAX) | cause right, fix wrong |
| P3 | `kernel/procfs` and `kernel/files` as listed; the open file stays 8 words | so, and two changes not predicted: `prctl(PR_SET_DUMPABLE)` (PAX answered -EINVAL, so the probe's dumpable rows could not be made: `kernel/cred`, `kernel/user`), and `stat` of `/dev/stdin` answering the descriptor's node (bu25's `cat` compares `/dev/stdin` by `dev` and `ino`; PAX answered the console's: the shape `cat /dev/stdin < f >> f` copied without end at the first boot). The open file stays 8 words (words 5 and 6, a `/proc` file's, hold a file's directory and its gone name) | right, two more changes |
| P4 | `fdtab` about 120 lines, byte-identical at the first boot after the fixes but for lines named before it; trunk's kernel differs in nearly every row; the inout sessions about 40 shapes, identical as root and as `pax` | `fdtab` **132** lines (root) and **127** (user); the first boot (`b1`) differed in 4 and 8 lines — the terminal's mode (the host's: the probe now prints its type), the dumpable rows (`PR_SET_DUMPABLE`), the user's run meeting root's leftover files (the probe now removes them) — and the second (`b2`, after those three changes) was byte-identical; trunk `d0a48be` differs in **117 of 132** and **112 of 127** lines; the inout sessions **35** shapes as root (21 refusals) and **32** as `pax` (20), identical at the third boot (§E) | right but the first boot |
| P5 | every suite green, text moving only where named | on kasumi (native, BIOS): `mpx5-jobs` (every J), `mpx3-tree` (every T, both new sessions), `mpx5-users` PASS; `mpx3-shell`'s root sessions need their Linux side as root (`linux-tty` binds `/dev`), which kasumi's rootless build cannot: CI's; `mpx4-ready` needs root for `tools/linux-net`: CI's (§H) | see §H |
| P6 | plant A (no magic link) red in `mpx5-jobs` at fds' first followed row and in `mpx3-tree` at the first refused shape; plant B (nbprobe's old row) red at a rate above 0, perhaps green | A: `mpx5-jobs` J8 red on all four legs at line 3 (`S: a file opened O_RDONLY: … stat …`); `mpx3-tree` T1 red at the first refused shape (`cat f >> f`) for both sessions on every leg it reached (§I). B was cut as the old row **made 60 ms late** (the measured mechanism, not a dice roll): red on every leg at `a write of 1 then: 1` on the Linux side | right |
| P7 | under 8 KiB of kernel text native; no record grows | **+22,736** bytes of `.text` native (kmain_console 910,171 → 932,907; kmain_session 912,923 → 935,659), +17,264 and +10,272 release; `.bss` +24 (the walk's note, three words); no record grows (`notes/px50/kasumi-kernel-cost.txt`) | wrong (three times the text) |

## A. The entries of /proc/<pid>/fd (pax#78, item 1)

Real root's answers (`L:` and `S:` and `O:` of `fdtab`,
`tests/mpx5-jobs.d/linux/fds.tty`), PAX's now:

- **What it names.** An entry is a magic link: a walk follows it where
  it would follow a link (not as the last component of `lstat`,
  `readlink`, O_NOFOLLOW or O_CREAT\|O_EXCL), to the node the
  descriptor is open on — no text is read and no path walked, so a file
  renamed, moved or unlinked since is still reached — after
  `ptrace(2)`'s read mode with the file-system ids (`may_trace`, px45's
  rule now shared with `environ`). `stat` and `statx` through it are
  `fstat`'s answer for every kind; `chdir` and `fd/N/name` and
  `fd/N/..` walk on from a directory's entry; a trailing `/` on a
  file's is -ENOTDIR; the 41st link is -ELOOP. A closed descriptor's
  entry, `fd/01`, `fd/x` -ENOENT.
- **`lstat` of an entry**: a link, the read and write bits of the
  descriptor's access mode and the search bit (0500, 0300, 0700), 64
  bytes, one link, the process's owner rule. `fd/` itself: 0500, as
  large as the descriptors open (24 for 24), two links.
- **`readlink`** (`fd_text`): a file's absolute path — the open file
  keeps the directory it was opened in (word 5, held), and the name is
  the one that directory gives the inode now, so a rename in the
  directory is followed, and a `rename` to another directory moves the
  word (`moved`); once the last name goes the open file keeps
  `<path> (deleted)` in a frame of its own (word 6, `mark_gone`, at
  `unlink`, `rmdir` and a `rename` that replaces); a directory's path
  (walked up, as `getcwd`); `/dev/null`, `/dev/zero`, `/dev/tty`; the
  console as a process starts with it `/dev/ttyS0` (its numbers, 4:64:
  `stat` of that path is the descriptor's terminal, which is what the
  probe asks, Linux's being a pseudo-terminal's name); a pipe's ends
  `pipe:[N]`, every socket `socket:[N]`, N the `st_ino` `fstat`
  answers; `anon_inode:[eventfd]`, `anon_inode:[eventpoll]`;
  `/proc/self/…` as `/proc/<pid>/…`. Cut at the buffer, no NUL; a
  buffer of 0 -EINVAL; `readlink` of `fd/` itself -EINVAL.
- **`open` through it** makes a new open file (offset 0), with the
  flags asked: a file for writing when its mode lets the opener write
  it, whatever the descriptor's own access (root's 0644 file: root 0, a
  user -EACCES); a pipe's end as the end asked, by the pipe's owner
  and 0600 (`proc_pid_fd(5)`'s example: 1001 is told -EACCES for a pipe
  root made); a socket's -ENXIO; an eventfd's and an epoll object's
  -EACCES to a user and -ENXIO to root; the terminal by its mode (a
  user -EACCES); an unlinked file's still reads; O_CREAT 0,
  O_CREAT\|O_EXCL -EEXIST, O_NOFOLLOW -ELOOP, O_DIRECTORY on a file's
  -ENOTDIR, a directory's O_WRONLY -EISDIR. What `/dev/std*` reopens
  copies the directory word too.
- **Listing** (`D:`): `.`, `..`, then every open descriptor in order, the
  listing's own among them, `DT_LNK`; `/proc/self` and `/proc/<pid>`
  list `fd` and `fdinfo`.

## B. /proc/<pid>/fdinfo (pax#78, item 2)

`fdinfo/` (0555, the process's effective ids whatever its dumpable
state) lists the same numbers (`DT_REG`); `fdinfo/N` (0444, the files'
owner rule) is made at its open (`fdinfo_of`, `procfs.fdinfo`):

    pos:\t<offset>
    flags:\t0<octal>
    mnt_id:\t<a number per file system>
    ino:\t<fstat's st_ino>

`flags` is the access mode and the status flags as `open` kept them
(O_APPEND 02000, O_NONBLOCK 04000, O_DIRECTORY 0200000, O_NOFOLLOW
0400000 stay; O_CREAT, O_EXCL, O_TRUNC, O_NOCTTY go), O_CLOEXEC
02000000 while the descriptor has it (it moves with F_SETFD), F_SETFL's
O_APPEND seen at once, and O_LARGEFILE 0100000 for what `open` made (a
file, a directory, `/dev`'s nodes, `/proc`'s files), not for a pipe
(`00`, `01`; `pipe2`'s flags `02004000`), a socket (`02`), an eventfd
(`02`, `04002` non-blocking) or an epoll object. `>>` is `0102001`,
bu25's measured line. `pos` is the open file's, so a `dup` shares it.
An eventfd adds `eventfd-count: ` (the counter in hexadecimal, sixteen
wide), `eventfd-id: ` and `eventfd-semaphore: 0`; an AF_UNIX socket
`scm_fds: 0`. `mnt_id` numbers PAX's file systems (the tree, `/proc`,
`/sys`, `/dev`, and the kernel's own for pipes, sockets and anonymous
inodes); the probe asks only which are the same, Linux's numbers being
its mounts'. EFD_SEMAPHORE stays refused by name (`kernel/ready`), so
the probe asks a non-blocking eventfd instead.

## C. Who may read another's (pax#78, item 3)

`P:` of `fdtab` (root's run makes targets of 0, 1001, 1002 and a 1001
that is not dumpable, each holding `/dev/null` as descriptor 7, and
asks as root and as 1001; a user's run its own child, dumpable and
not): root reads every one; 1001 reads its dumpable sibling's (1001's,
after `prctl(PR_SET_DUMPABLE, 1)`, since a change of ids makes a
process not dumpable); 1001 is told -EACCES for root's, 1002's and a
not-dumpable 1001's — `fd/` open, `readlink`, `stat` and `lstat` of an
entry, the entry's `open`, `fdinfo/`'s open and `fdinfo/7`'s `lstat`
and open. `fd/` is root's (0:0 0500) while the process is not
dumpable, and its entries and `fdinfo/7` too, but `fdinfo/` keeps the
process's ids; a process not dumpable enters, opens and reads its own
all the same (`own_fd_dir`; `ptrace(2)`'s "the process itself"). A
zombie child's `fd/` is open with no entry (`fd/0` -ENOENT). PAX had
no `PR_SET_DUMPABLE` (-EINVAL): now 0 or 1 (`cred.set_dumpable`), 2
-EINVAL.

## D. /proc and /sys removed and renamed (pax#80, item 5)

`X:` of `fdtab`, `/` root's 0755 on the guest (vmjob's `chmod`), on PAX
and in the container: root `rmdir` of `/proc` and `/sys` -EBUSY,
`rename` of either to a new name -EBUSY, a directory renamed onto
either -EBUSY; a user -EACCES for each (the write and search of `/`
first: px47's order for `/dev`, `mount_root`); `rename("/proc",
"/proc")` 0 to anyone; `rename` of `/proc/self` out -EXDEV;
`rmdir("/proc/self/fd")` -EPERM to anyone. Trunk answered `rmdir` of
`/proc` -ENOENT (it looked the name up in the tree) and every `rename`
-EXDEV, to anyone (`notes/px50/pax-d0a48be-fds*.session`).

## E. cat's refusal on PAX (pax#78, item 4)

`tests/mpx3-tree`'s `shell-inout` (root, in `/w`) and
`shell-inout-user` (after `su pax`, in `~/w`): boreutils' 52 inout
shapes as far as PAX's shell image runs them (`read` and `echo -n`
where `tools/inouttest` uses `dd`; `f >> f`, `<`, `-`, `/dev/stdin`, a
hard and a symbolic link, an input part read, `f f`, `- -`, `a f b`, a
missing operand, a directory, `-n -A -s`-style options, `>`, `1<>`
behind, at and ahead, what was written counting, `/dev/stdin` afresh at
0, another file, `exec 3>>`, a pipe out, `/dev/null`): **35 shapes as
root, 21 refusals; 32 as `pax`, 20 refusals**, every line of both
byte-identical to the same session in the container
(`notes/px50/inout-*.txt`; `mpx3-tree` T1 and T6 on kasumi). bu25's
`cat` reads `/proc/self/fd/1` (followed: the output's `dev` and `ino`),
`/proc/self/fdinfo/1` (the append bit) and `/proc/self/fd/0` for `-`;
the shapes with `/dev/stdin` also need `stat("/dev/stdin")` to be the
descriptor's (§3a P3). On trunk every shape Linux refuses copies
without end (px49's `cat-dark`; plant A, §I).

## F. A row that is the host kernel's

CI's first run of the probe (plant A's dispatch, run 39076252598)
found the container's user row `P: its zombie child's fd/` answered
`0:0 0500; open EACCES … fd/0 EACCES` under the runner's kernel
(Ubuntu 24.04's), where Linux 7.2.8 — real root's guest and kasumi's
podman — answers the zombie's own ids and opens it. Linux changed this
between the two kernels; the recordings are 7.2.8's, so J8 holds PAX to
them, and `tests/mpx5-jobs` leaves that row out of the container's
comparisons (J0, J3), named, as px49 leaves out TIOCSTI's rows on a
host that allows them.

## G. nbprobe's race (pax#79, item 6)

`notes/px50/nbrace.c`, nbprobe's steps in a loop over the container's
loopback under `taskset -c 0-3` (`notes/px50/nbrace-kasumi.txt`): the
row at once after the -EAGAIN was taken 0 of 2,000 times on kasumi;
SIOCOUTQ first fell **30 to 49 ms** after it (75 and 225 of 300), the
receiver's delayed acknowledgement; POLLOUT came back 0 of 300 times at
once, 1, 10 and 100 ms (the free room stays below what POLLOUT asks
for) while a write of 1 after 100 ms was taken 300 of 300 times, then
95,231 bytes more; with the write 60 ms late, the old row was taken 300
of 300 times. So the row raced on a runner that took longer than about
30 ms between the fill's last -EAGAIN and its write (it prints a line
in between). The fix (`user/net/nbprobe.c`): wait 100 ms and send
again, until a send after the wait takes nothing — one more pass on
Linux, none on PAX — then the row; settled, the write was taken 0 of
300 times, also 60 ms late. The row's text is unchanged
(`-EAGAIN` on both sides), so no recording moved. Plant B (§I) is the
old row 60 ms late: red.

## H. Existing suites

On kasumi (native, BIOS; the build in `px13-ubuntu`, the Linux side in
podman, the boots under `taskset -c 0-3`): `mpx5-jobs` PASS, every J
(J8 fds and fds-user byte-identical to real root's recordings, J3 to
the container's); `mpx3-tree` PASS, every T for all thirteen sessions
(the two new ones T1, T3, T4, T6, T8); `mpx5-users` PASS (`rights` and
`sig` list and open `fd/` as before). `mpx3-shell`'s root sessions
need `tools/linux-tty` to bind `/dev` as root on the build host, which
kasumi's rootless build cannot (every S2 empty there, a harness
limit): CI's runs. `mpx4-ready` needs root for `tools/linux-net`:
CI's runs. Everything else: CI's (§J).

## I. Plants

Each a branch never to be merged, cut from the code head `7ee1a4c`,
one commit, run in CI by dispatch with one suite (`gh workflow run ci
-r <branch> -f suites=<job>`), every leg.

| plant | branch, commit | break | CI |
|---|---|---|---|
| A | `px50-plant-a` `56abe77` | `fd_follow` answers -ENOENT: an entry of `fd/` is never followed (trunk's answer, the listing and `readlink` kept) | `mpx5-jobs`: run 39076252598, job 117524002870: **J8 FAIL on all four legs** for fds and fds-user, first at line 3 (`S: a file opened O_RDONLY: … stat …`: `stat` through the entry no longer the file's), J4 FAIL (the witness rows), J1, J2, J5, J6, J7 PASS. `mpx3-tree`: run 39076260398, job 117524021537: **T1 FAIL** for shell-inout and shell-inout-user on native BIOS, release BIOS, native UEFI and release UEFI's root session, first at the first shape (`cat f >> f`: no `input file is output file`; the native legs copied until the 300 s prompt wait ran out, the release legs until the tree was full, `cat: write error: No space left on device`), T4 and T8 with them; every other session's T PASS; the job then met its 60-minute limit before the last leg's user session (GitHub cancelled it: no lane cancelled it) |
| B | `px50-plant-b` `24d354f` | nbprobe's row without the settling and 60 ms late | `mpx4-ready`: run 39076268588, job 117524015415: **T2 FAIL** `82c82 < a write of 1 then: 1 --- > a write of 1 then: -EAGAIN` (the Linux side took the byte; PAX's answer as every recording since px24), the same line as px49's sighting in run 39058414358 |

## J. CI

- The tiers: `kernel/files`, `kernel/procfs`, `kernel/cred` and
  `kernel/user` are `@user`, `user/net/*` `@net`, `tests/mpx5-jobs`,
  `tests/mpx3-tree` and `user/console/*` their suites', `notes/*`
  NONE: a pull request's push runs the user suites on the pr leg; the
  `full-matrix` label, added once the head is final, runs every suite
  on every leg. `tests/ci-plan`: 148 PASS on kasumi.
- Plant runs: §I.
- The final head's runs: named in the pull request (a commit naming
  them would move the head).

## 4. Evidence index

Shas are this branch's (`px50`). kasumi paths are under `~/lanes/px50/`.

### What was written

- The prediction: `a42b96d` (§1 to §3, before any change or
  measurement).
- The probe and its tools: `8cdd615`, `c340eda` (`user/elf/fdtab.c`),
  `341174a` (`tools/mkjobs`), `689dd3f` (`notes/px50/vmjob.c`,
  `vm-fds.sh`, `ct-fds.sh`), `115aba1`, `8c8b19e`, `fea7889` (the
  build, boot, inout and suite scripts).
- The kernel: `37435d1` (`kernel/procfs`), `21fd487` (`kernel/cred`,
  `kernel/user`: PR_SET_DUMPABLE), `e0f2a86` (`kernel/files`: the magic
  link, `readlink`, reopening, fdinfo, `/proc` and `/sys` removed and
  renamed), `41bc332` (`stat` of `/dev/std*`).
- The suites: `5072b76`, `ad2d690` (`tests/mpx5-jobs`), `e6a35b0`,
  `3db9bbc` (real root's recordings), `97b035d`
  (`user/console/shell-inout*.keys`), `67cf536` (`tests/mpx3-tree`).
- pax#79: `b9c01db` (`notes/px50/nbrace.c` and its run, committed
  before the fix), `7ee1a4c` (`user/net/nbprobe.c`).
- The words: `3cf2ba4` (`kernel/README.md`), `444997e`
  (`docs/SOURCES.md`), `b2fe889` (README), `1422293` (CHANGELOG).

### What was measured, and where it is

- **Real root's Linux** (kasumi's 7.2.8-1-cachyos `f4c00d5d…` under QEMU
  11.1.1, `notes/px50/vmjob.c` as pid 1, the suite's own archive
  `d4adeab9…`): `tests/mpx5-jobs.d/linux/fds.tty`, `fds-user.tty` and
  their `vm-*.meta`, recorded twice (`vm/rec1`, `vm/rec2`), the same
  bytes (`388bf653…`, `d16c3d7a…`). The first two measurements, by the
  probe as first written: `notes/px50/linux-first-fds*.txt`,
  `linux-2-fds*.txt` (§3a's P2).
- **The container** (podman, `px13-ubuntu`): `fdtab` as 1000:1000
  (`ct-fds.sh`; the suite's J0 on kasumi); the inout sessions
  (`notes/px50/inout-*-linux.txt`).
- **PAX at trunk `d0a48be`**: the fds image on trunk's kmain_session:
  `notes/px50/pax-d0a48be-fds.session`, `-fds-user.session`.
- **PAX, the branch** (kasumi, TCG, BIOS): `out/b2-pax` (fdtab, 0
  lines differ), `notes/px50/inout-*-pax.txt`; the three suite runs of
  §H (`notes/px50/suite.sh`; their logs went with the build
  directories when kasumi was pruned: §H keeps their verdicts, and
  CI's runs hold every suite again).
- **pax#79**: `notes/px50/nbrace-kasumi.txt`.
- **The kernel's cost**: `notes/px50/kasumi-kernel-cost.txt`.
- **The plants in CI**: §I.

### Measured, inferred, not verified

**Measured**: everything in §A to §I but what follows.

**Inferred**:
- A second hard link in the directory a file was opened in reads as
  the first name `name_of` finds there (Linux reads the name it was
  opened by); a file whose directory's own name is gone reads the
  path the walk up finds.
- The `fdinfo` lines of a TCP socket past the four (not asked of
  Linux; PAX prints none).
- `unlink` of an entry of `fd/` (-EROFS, by name, as before).

**Not verified**:
- Real root was one kernel build (7.2.8); §F shows another kernel
  answers a zombie's row otherwise, and others may differ elsewhere.
- More than one CPU, and a thread's `/proc/<tid>` (PAX has none).
- `mpx3-shell` and `mpx4-ready` on kasumi (CI's runs only).
- UEFI under KVM on hasu: no soak in this lane; UEFI on CI's full
  tier only.

### Issues

- **To close at merge**: pax#78 (`fdtab`'s L, S, O, D, I, P rows,
  `tests/mpx5-jobs.d/linux/fds*.tty`, and the shell-inout sessions:
  cat refuses on PAX as on Linux, as root and as `pax`; plant A),
  pax#80 (`fdtab`'s X rows, root and user, on real root's guest with
  `/` 0755 and `/sys`), pax#79 (§G; plant B).
- **Left open**: none of the three.
- **Would file (none filed)**:
  1. pax: EFD_SEMAPHORE is still refused by name (`kernel/ready`);
     Linux's fdinfo prints `eventfd-semaphore: 1` for one.
  2. pax: `readlink("/dev/stdin")` is -EINVAL and `lstat` of it a
     character device; Linux's is a link to `/proc/self/fd/0` (PAX
     follows it for `stat` only, §3a P3).
  3. pax: the fdinfo lines of inotify, signalfd and timerfd descriptors
     have nothing to describe (PAX has none of them); TCP's past four
     lines not measured.

## 5. Done-when

- Branch `px50` on origin; pax PR (number in the hand-back), open,
  unmerged.
- The five sections §1 to §5; the items §A to §J.
- The test checklist:
  - [x] `tests/mpx5-jobs` on kasumi, native, BIOS (every J; J8 fds and
        fds-user byte-identical to real root's recordings)
  - [x] `tests/mpx3-tree` on kasumi, native, BIOS (every T; shell-inout
        and shell-inout-user T1 byte-identical to the container)
  - [x] `tests/mpx5-users` on kasumi, native, BIOS
  - [x] `tests/ci-plan`, every case
  - [x] trunk's kernel red on the fds rows (117 and 112 lines)
  - [x] plants A and B red in CI (§I)
  - [ ] `tier full` at the final head: named in the PR
- `wolf/tools/lane-audit.sh pax px50 <PR>` exit status: named in the PR.
- Trees: kasumi `~/lanes/px50/` keeps `out/`, `vm/rec1`, `vm/rec2`,
  `bin/`, `cache/`; build directories removed at the end. Plant
  branches stay on origin, never to be merged.
