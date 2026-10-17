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
