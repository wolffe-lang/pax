# px38 — The users (what multi-user PAX takes: measured, staged)

Contract: px38's, `sprints/pax/38-the-users/` in wolffe-lang/wolf
(planning commit `0e0c910`, read 2026-10-12), with the rules of
`sprints/wave-53.md` down to `wave-45.md`. Branch `px38` in pax, cut
from pax trunk `89f04a9`. §1 to §3 are committed before the first
measurement.

One deliverable: **a plan, not code.** This note says what PAX stores
and checks today, what Linux does at each stage (measured black-box),
what PAX lacks, a staged sequence of lanes with a done-when each, and
the rulings the maintainer owes, each with a recommendation. The PR
touches `notes/` only.

The five items of the contract are §A to §E below; the five sections
the audit asks of a report are §1 to §5.

## 1. Forbidden, absolutely

- No kernel's, libc's, shell's or file system's source is read
  (ruling #22), and none is searched for; the refs clone's sparse
  checkout is never widened. No GNU coreutils, shadow-utils, util-linux,
  PAM, busybox, toybox or uutils source, and no source of any `su`,
  `login`, `passwd`, `id` or `newgrp`. Facts come from the Linux man
  pages (`credentials(7)`, `capabilities(7)`, `path_resolution(7)`,
  `inode(7)`, `user_namespaces(7)`, `proc(5)`, `setuid(2)`,
  `setreuid(2)`, `setresuid(2)`, `setfsuid(2)`, `getgroups(2)`,
  `execve(2)`, `kill(2)`, `chmod(2)`, `chown(2)`, `utimensat(2)`,
  `access(2)`, `open(2)`, `mkdir(2)`, `umask(2)`, `unlink(2)`,
  `passwd(5)`, `group(5)`, `shadow(5)`, `crypt(5)`, `su(1)`,
  `login(1)`, `passwd(1)`, `id(1)`), POSIX.1-2024, the uapi headers the
  sparse checkout holds, pax's, pelt's and boreutils' own source, and
  black-box runs on Linux: static C programs that print what the
  kernel answers, and strace of the distribution's own binaries.
- No behaviour changes: nothing under `kernel/`, `user/`, `tests/`,
  `tools/`, `boot/`, `docs/` or `.github/` is touched. Probe programs
  and their recorded outputs live under `notes/px38/`; an image that
  boots PAX with a probe in it is built in the lane's scratch from
  trunk's kernel, unchanged, and is not committed.
- **No real account on any host.** A non-root process is made only
  inside a container, a user namespace or a QEMU guest that this lane
  made and removes; `useradd` runs only inside a throwaway container.
  No `sudo` anywhere.
- Each Linux row names the kind of root that produced it: **vm** (root
  of the initial user namespace of a Linux booted under QEMU: every
  capability) or **ct** (root of a rootless podman container: root in a
  user namespace). Where they differ the row says so; where only **ct**
  could run it and the difference may matter, the row is marked as
  owing a real-root witness. Nothing is guessed across the two.
- No syscall number is proposed for PAX that is not in a strace or a
  probe run this lane took.
- No word implying filming in pax. px35's files (`kernel/arp`,
  `kernel/net`, `kernel/virtio`, `tests/mpx4-*`) and px37's
  (`.github/`, the CI tiers) are not touched; no run of theirs is
  cancelled.
- Probe binaries are static and built in the Ubuntu 24.04 container on
  kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's own glibc.
- No `rm` outside `~/lanes/px38/` on any host; no scratch in `/tmp`; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag; no issue
  filed or closed (listed instead); no `2>/dev/null` on a checkout; no
  trailer of any kind on a commit or the PR. No build on nomad-1.
  Nothing is installed anywhere. Host ports 8080 and 8088 are not used.
- kasumi: remote commands under `bash`, jobs under `setsid` with a pid
  file, ended by that pid only; a container is stopped by its own id
  only; `/home` is at 97%, so build directories are pruned as I go.
- No "seen red" claim is made by this lane: it plants nothing and
  changes no test.
- If the harness refuses an action, I stop and report; I do not route
  around it.

## 2. Inputs, verified (2026-10-12)

| input | found |
|---|---|
| pax trunk | `89f04a9` (px36 merged), the contract's |
| the kernel's pin | wolf 0.2.28 (`3215f321…`, pin `f71ece8e`) / lupin 0.1.51 by archive digest (`kernel/wolf.pin`) |
| px36's note | `notes/px36-the-file-changes.md`: 13 numbers added; an owner that is not root refused by name, -EINVAL (`R_OWNER`, syscall 92 in the probe); the probe's ten refusal lines; drift 4, "a write keeps set-ID bits" (kasumi's container cleared them, the CI runner's root kept them) |
| px27's note | the tree: inodes of 16 words, a mode set at creation as `mode & ~umask`, no owner word |
| px25's, px34's and px26's notes | `/proc/<pid>/status` for every process (px25: `Uid` and `Gid` four zeros, `Groups` empty, the five capability masks zero); AF_UNIX path sockets (px34); `kill`, `tgkill`, `tkill` with no permission rule (px26) |
| **where identity could live** (read from `kernel/sched`, `kernel/files`, `kernel/tree` at `89f04a9`) | a process area of 40,960 bytes a slot (`sched.PROC_AREA`), copied whole by a fork and kept by `execve`, shared by a process's threads: the working directory (word 12), the umask (word 254) and the program's archive entry (word 255) already live there. An inode's 16 words are all taken (mode, links, size, holders, three times, root, depth, blocks, back, backlen, parent, entries, btime, next): **there is no word for an owner or a group** |
| **what the kernel checks today** (read) | `getuid`, `geteuid`, `getgid`, `getegid` answer 0 from one line of `kernel/user`; `tree.mode` is read in three places only: `execve` and `access(X_OK)` want any execute bit, and `stat`; no `open`, path walk, `unlink`, `chmod`, `kill` or `/proc` read looks at who asks |
| boreutils trunk | `2ab3651` (bu22), 39 utilities: **no `id`, `whoami`, `chown`, `chgrp`, `su`, `login`, `passwd`, `groups`, `logname`, `install`**. `ls -l` and `stat` print an owner's name from `/etc/passwd` and `/etc/group` read as files (`src/bore/ids.lu`); `cp -p` refuses an owner by name (wolf-lang#701) |
| pelt trunk | `1315587`: `umask` is a built-in over `os_umask`; the effective ids are read from `/proc/self/status`'s `Uid:`, `Gid:` and `Groups:` lines (`src/sh/util.lu`, for `test -r/-w/-x`), else from `id -u` and `id -G`; no `su`, no `login`, no `~user` |
| wolf trunk | wolf-lang `b407c73b` (0.2.29 + 50): the prelude's 110 host builtins hold **no** call that reads or sets a user or group id and none that changes an owner: wolf-lang#633 (no uid/euid surface) and #701 (no `fs_chown`) are open. `os_term_set_mode` (no-echo input) and `os_exec` exist. wolf-std `d7c2968` has `std/x/crypto/sha2` and no password hash |
| the track index | job control on PAX is a pax lane after pelt's sh16 (ruling #69 R8); px37 (CI tiers) is running |
| kasumi | Linux 7.2.8-1-cachyos, podman rootless (`mfwolffe:100000:65536` in `/etc/subuid`), QEMU 11.1.1 TCG only (no `/dev/kvm`), `px13-ubuntu` (`ad896450…`: Ubuntu 24.04.5, glibc 2.39, strace, cc, coreutils, util-linux's `su`, shadow's `login` and `passwd`); `/home` 97% (32 GB free); `/usr/lib/modules/7.2.8-1-cachyos/vmlinuz` is world-readable, so a real Linux boots under QEMU with a probe as its init: the **vm** root |

Drift from the contract's inputs line: none in the shas. One reading:
the contract names px25's and px34's notes "for processes and signals";
the signal rules are px26's, read as well.

## 3. Prediction (committed before the first measurement)

### P1. PAX today, number by number

- `getuid` (102), `getgid` (104), `geteuid` (107), `getegid` (108): 0.
- **-ENOSYS**, all twenty: `setuid` (105), `setgid` (106), `setpgid`
  (109), `getpgrp` (111), `setsid` (112), `setreuid` (113), `setregid`
  (114), `getgroups` (115), `setgroups` (116), `setresuid` (117),
  `getresuid` (118), `setresgid` (119), `getresgid` (120), `getpgid`
  (121), `setfsuid` (122), `setfsgid` (123), `getsid` (124), `capget`
  (125), `capset` (126), `chroot` (161). None is refused by name.
- `stat` reports owner 0 and group 0 for every node. A file of mode
  0000 opens for reading and writing; a directory of mode 0000 is
  searched and listed. `execve` wants any one execute bit. `kill`
  reaches any pid. `/proc/self/status` reads `Uid: 0 0 0 0`, `Gid: 0 0
  0 0`, `Groups:` empty, and `CapEff: 0000000000000000` (Linux's root
  reads `000001ffffffffff`: a drift nobody has named). The auxiliary
  vector's AT_UID, AT_EUID, AT_GID, AT_EGID and AT_SECURE are 0.

### P2. Linux, credentials

- `setuid(x)`: with effective id 0 it sets real, effective and saved;
  otherwise it sets the effective id alone and only to the real or the
  saved id, else -EPERM. The file-system id follows the effective id
  in every call that changes it.
- `setreuid(r, e)`: an unprivileged caller may set the real id to the
  real or the effective id and the effective id to the real, effective
  or saved id; the saved id becomes the new effective id when the real
  id is set or the effective id is set to something other than the old
  real id.
- `setresuid(r, e, s)` as (1000, 1001, 1002): 0 exactly when each
  argument is -1 or one of the three current ids; of the 125 rows over
  {-1, 0, 1000, 1001, 1003} that is 3 × 3 × 3 = 27 answers of 0 and 98
  of -EPERM. As (0, 0, 0): all 125 are 0 on **vm**.
- `setfsuid(x)` answers the previous file-system id whether or not it
  changed anything.
- `setgroups` by a caller whose effective id is not 0: -EPERM.
  `getgroups(0, NULL)` answers the count. A child keeps all of it over
  `fork` and `execve`; the saved id becomes the effective id at
  `execve`.
- **ct against vm**: an id with no mapping in the container's user
  namespace is -EINVAL in **ct** where **vm** answers 0. No other
  credential row differs.

### P3. Linux, permission checks

- The class is chosen once: the owner's bits for the owner, even when
  they deny what the group's or the others' would allow (0077 owned by
  the caller: -EACCES); then the group's (the effective group or any
  supplementary one); then the others'.
- Root reads and writes whatever the mode; root executes a file only
  if some execute bit is set; root searches any directory.
- A sticky directory: `unlink` or `rename` of another's file by one who
  owns neither the file nor the directory is **-EPERM**, not -EACCES.
- `chmod` by one who is not the owner: -EPERM. An owner who is not in
  the file's group and sets S_ISGID gets 0 with the bit silently
  cleared.
- `chown` to another user by the owner: -EPERM; the owner may give the
  file to a group it is in (0) and not to another (-EPERM); a
  successful `chown` by a non-root caller clears set-user-ID and
  set-group-ID.
- `utimensat` with `times` NULL: 0 for the owner or for anyone with
  write permission, else -EACCES; with explicit times by a non-owner
  -EPERM even with write permission.
- A new file's owner is the caller's file-system user id and its group
  the file-system group id, unless the directory is set-group-ID: then
  the directory's group, and a new directory inherits the bit.
- `access` uses the real ids; `faccessat2(AT_EACCESS)` the effective.
- **ct against vm**: only the write-by-root row (px36's) and ids with
  no mapping.

### P4. Linux, set-ID

- `execve` of a file with set-user-ID owned by 1001, by a process
  (1000, 1000, 1000): the ids become (1000, 1001, 1001) and AT_SECURE
  is 1; set-group-ID the same for groups. Ignored (the ids stay, 0
  returned, AT_SECURE 0): on a mount with `nosuid`, for a `#!` script,
  and under `PR_SET_NO_NEW_PRIVS`.
- The bits go: on a write or a truncation by a caller without
  CAP_FSETID (set-group-ID only when group-executable); on any
  `chown`. **vm** root's write keeps them, **ct** root's clears them.

### P5. Linux, signals and `/proc`

- `kill(pid, sig)`, signal 0 included: 0 when the sender's real or
  effective id equals the target's real or saved id, or the sender's
  effective id is 0; else -EPERM; -ESRCH for no such process.
- `/proc/<pid>` of another user's process: `status`, `stat`, `cmdline`
  read; `environ`, `mem`, `fd/`, `exe`, `cwd` are -EACCES. The
  directory's owner is the process's effective id.

### P6. Linux, the userland

- `id` and `whoami`: the four `get*id` calls and `getgroups`, then
  `/etc/passwd` and `/etc/group` opened and read (after
  `/etc/nsswitch.conf`); nothing else.
- `ls -l`: `statx` or `lstat`, then the same two files.
- `chown` and `chgrp`: the two files for a name, then `fchownat`.
- `su`: PAM's files, `/etc/shadow` through a helper or directly as
  root, then `setgroups`, `setgid`, `setuid` in that order, then
  `execve` of the account's shell.
- `login`: the same three calls after `setsid` and a `TIOCSCTTY`, and
  an `fchown` and `fchmod` of the terminal.
- `passwd`: a lock file, a new file written beside `/etc/shadow` and
  renamed over it.

### P7. The count

- New numbers PAX needs for every stage, each seen in a strace or the
  probes: **16 ± 3** (the twelve `set*id`/`get*id`/groups calls of P1
  that are not process-group calls, `setfsuid`, `setfsgid`, and at
  most four more that the tools ask and cannot do without).
- Lanes in the sequence: **6 ± 2**. Rulings owed: the contract's six
  and at most four more.
