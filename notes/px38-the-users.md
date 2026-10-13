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

### Corrections to §2, found after it was committed

- "the prelude's 110 host builtins": **107** names match `os_`, `fs_`,
  `env_`, `net_`, `time_` in wolf-lang `b407c73b`'s
  `crates/wolf_sema/src/prelude.rs` (counted again). None reads or sets
  an id, as said.
- "`CapEff: 0000000000000000` … a drift nobody has named" (P1): it is
  named, in `kernel/procfs/procfs.lu`'s header ("no capability set: a
  process on PAX is root by rule, not by capability").

## 3a. The prediction, scored

"vm" and "ct" are the two Linux roots of §1; the files are under
`notes/px38/`. Every Linux line is from Linux 7.2.8-1-cachyos on
kasumi.

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | four zeros; twenty numbers -ENOSYS, none refused by name; nothing checks a mode or an owner but `execve` and `access(X_OK)`; `stat` says 0:0; the status lines; the auxiliary vector | all of it for the nineteen of the twenty that were asked (`pax/pax-ids.txt`, `pax/pax-ids.kernel.txt`; `chroot` from `pax/pax-priv.txt`; `capset` was not asked), and `setpriority` (141) is a twentieth -ENOSYS. **Not predicted:** `prctl(PR_GET_DUMPABLE)`, `(PR_GET_KEEPCAPS)`, `(PR_GET_NO_NEW_PRIVS)`, `(PR_GET_SECUREBITS)` are -EINVAL (Linux: 1, 0, 0, 0; `su`, `sg`, `passwd` and `login` ask the last two); `SO_PEERCRED` on a socketpair is refused by name, -EOPNOTSUPP | right; "nobody has named" the capability lines was wrong (above) |
| P2 | the four `set*uid` rules; 27 answers of 0 and 98 of -EPERM; `setfsuid` answers the previous id; `setgroups` -EPERM for a user; `fork` and `execve` keep the ids, the saved id becomes the effective one; ct differs only on an unmapped id | **the model of `check-cred.py`, written from the man pages before the run, fits all 2,640 rows on vm, ct and vm with the protected settings, with no correction**; 27 and 98, and 125 of 125 as root (`check-cred.py`'s output). ct: `setuid(70000)`, `setgid(70000)`, `setuid(4294967294)` -EINVAL where vm answers 0; no other answer or id differs. **Not predicted:** `setuid(-1)` and `setgid(-1)` are -EINVAL, not -EPERM, for root and user alike; `setgroups` keeps a repeat and sorts the list (`{2000, 2001, 2001, 0}` reads back `0 2000 2001 2001`); 65,536 groups are taken and 65,537 are -EINVAL; AT_SECURE is 1 after any `execve` by a process whose real and effective ids differ, with no set-ID file in sight; a process (0, 1000, 0) that calls `setfsuid(0)` has root's file rights back while its effective id is 1000 | right |
| P3 | one class, chosen once; root's three rules; sticky -EPERM; `chmod`, `chown`, `utimensat` ownership; a new file's owner and the set-group-ID directory; `access` real, AT_EACCESS effective; ct differs on two rows | `check-perm.py`'s rule fits all 210 rows of sections A and B on the three runs; the rest as predicted. **Not predicted:** an owner may `chown` a file to the group it already has without being in it, and `chown(-1, -1)` by the owner is 0 and **clears the set-ID bits**, by anyone else -EPERM; `utimensat` with `{UTIME_NOW, UTIME_OMIT}` counts as explicit times (-EPERM for a non-owner with write permission; only NULL and `{NOW, NOW}` are the lenient form) and `{OMIT, OMIT}` is 0 for anyone; a file made with S_ISGID in a set-group-ID directory by one who is not in the directory's group loses the bit; a set-group-ID bit without group execute survives `chown`, and a directory's bits survive it. **ct differs on six classes of row, not two** (§B, "The two roots") | right on the rules; wrong on the count of ct rows |
| P4 | set-ID `execve`; ignored on nosuid, for a `#!` script, under no_new_privs; the bits go on a write or truncation without CAP_FSETID and on any `chown`; vm keeps them, ct clears them | all of it (`setid` section). **Not predicted:** a write of no bytes keeps the bits and `fallocate` clears them; a set-group-ID bit without group execute is cleared by a writer who is not in the file's group and kept for one who is (`02767`); such a file is not honoured at `execve` either (`02745`: ids unchanged, AT_SECURE 0); root running a set-user-ID program of 1001 becomes (0, 1001, 1001) with no capability | right |
| P5 | the `kill` rule; -ESRCH; what `/proc/<pid>` shows | `check-sig.py`'s rule fits 102 of 102 sender rows on the three runs; `/proc` as predicted, plus `maps`, `auxv`, `io` and `root` refused and `limits` readable. **Not predicted:** the owner himself is refused `environ`, `fd/`, `exe` and the rest once the target is not dumpable — after any change of id without an `execve`, or an `execve` with real and effective ids apart — and those files are then root's (`environ is 0:0`); SIGCONT reaches every target (one session) | right |
| P6 | what `id`, `whoami`, `ls -l`, `chown`, `su`, `login`, `passwd` call and read | the calls and the order (`setgroups`, `setgid`, `setuid`, then `execve`) as predicted; `su` reads `/etc/shadow` itself (it is set-user-ID root: no helper ran). **"nothing else" was wrong:** `id` also opens `/proc/filesystems` and `/proc/sys/kernel/ngroups_max` and tries the name-service socket; `ls -l` also asks `lgetxattr` and `listxattr`; `login` moves the file-system ids back and forth five times (PAM), joins a keyring, and sets a process group | right on what matters; wrong on "nothing else" |
| P7 | 16 ± 3 new numbers; 6 ± 2 lanes; the six rulings and at most four more | **12** numbers (nine in the tools' traces, three more only in the probes; no tool needs a thirteenth: §C); 7 lanes in the first cut (and 3 outside pax, 2 deferred); 9 rulings | numbers wrong (one below the band); lanes and rulings right |

## A. PAX today (item 1)

Read from `kernel/` at `89f04a9`, then booted: the kernel built by the
tree's own tools at its own pin (wolf 0.2.28), `kmain_console`, native
tier, BIOS, QEMU 11.1.1 TCG on kasumi, the probe the first program
(`notes/px38/pax-boot.sh`; kernel `f095f5df…`; `pax/pax-ids.meta`,
`pax/pax-priv.meta`). The same binaries ran on Linux (`linux/vm.txt`).

**Where a process's identity could live.** Nowhere today. The process
area (`sched.PROC_AREA`, 40,960 bytes a slot, in `boot/sched.S`'s
`pax_procs`) is the place: a fork copies it whole, `execve` keeps it, a
process's threads share their leader's (`sched.proc_area`). It already
holds the working directory (word 12), the umask (word 254) and the
program's archive entry (word 255); no `A_` constant in `kernel/` names
a word between 148 and 253 (read, not proven free). A file's identity
has no room: all 16 words of an inode are taken (`kernel/tree`).

**What each call answers** (`ids`, as root; the kernel logs each
unknown number once a program):

| call | number | PAX `89f04a9` | Linux (vm) |
|---|---|---|---|
| `getuid`, `getgid`, `geteuid`, `getegid` | 102, 104, 107, 108 | 0 (one line of `kernel/user`) | 0 |
| `setuid`, `setgid` | 105, 106 | -ENOSYS | 0 |
| `setreuid`, `setregid` | 113, 114 | -ENOSYS | 0 |
| `setresuid`, `setresgid` | 117, 119 | -ENOSYS | 0 |
| `getresuid`, `getresgid` | 118, 120 | -ENOSYS | 0 (0 0 0) |
| `setfsuid`, `setfsgid` | 122, 123 | -ENOSYS | the previous id |
| `getgroups`, `setgroups` | 115, 116 | -ENOSYS | 0 |
| `capget` | 125 | -ENOSYS | 0, every capability |
| `getpgrp`, `getpgid`, `getsid`, `setpgid`, `setsid` | 111, 121, 124, 109, 112 | -ENOSYS (the job-control lane's) | answered |
| `chroot`, `setpriority` | 161, 141 | -ENOSYS | 0 |
| `prctl` PR_GET_DUMPABLE, _KEEPCAPS, _NO_NEW_PRIVS, _SECUREBITS | 157 | -EINVAL (PAX takes PR_GET_NAME and PR_SET_NAME) | 1, 0, 0, 0 |
| `chown(f, 1000, 1000)` | 92 | refused by name, -EINVAL (px36's `R_OWNER`) | 0, then owned 1000:1000 |
| `getsockopt(SO_PEERCRED)` on a socketpair | 55 | refused by name, -EOPNOTSUPP | 0 (uid 0 gid 0) |
| `mknod` of a device or a FIFO | 133 | refused by name, -EPERM | 0 |
| `socket(AF_INET, SOCK_RAW)` | 41 | refused by name, -ESOCKTNOSUPPORT | 0 |
| `prlimit64` setting a limit | 302 | -EPERM | 0 |

Twenty numbers were asked and are -ENOSYS — the twelve identity calls
after the getters, `capget`, the five process-group calls, `chroot`
and `setpriority` — and none is refused by name: nothing in PAX yet
knows these calls exist.

**What a process is told.** The auxiliary vector's AT_UID, AT_EUID,
AT_GID, AT_EGID and AT_SECURE are 0. `/proc/self/status` and
`/proc/<pid>/status` read `Uid: 0 0 0 0`, `Gid: 0 0 0 0`, `Groups:`
empty, and the five capability masks zero (Linux's root: `CapPrm`,
`CapEff` and `CapBnd` `000001ffffffffff`). `stat` says uid 0, gid 0 for
`/`, `/bin`, `/dev/null`, `/proc`, `/proc/self`, `/proc/1`. `/proc`
holds a process's `status` and nothing else of it (`self/exe` is a
link): no `environ`, `cmdline`, `fd/` or `maps` to guard yet.

**What is checked.** `tree.mode` is read in three places: `execve`
(`files.exec_lookup`: any of the three execute bits, else -EACCES),
`access(X_OK)` (the same), and `stat`. Booted: a file of mode 0000
opens for reading and for writing and `access(R_OK|W_OK)` is 0; a
directory of mode 0000 is searched, written and listed; `chmod 0644`
makes the probe's own file -EACCES to run and `chmod 0001` runs it;
`kill(1, 0)` is 0. These are also Linux's answers **for root** — the
whole `ids` section differs from Linux's in nothing but the calls PAX
lacks — which is why no test has ever seen the absence: every program
on PAX is root, and Linux lets root past every check but the execute
bit.

**What only root may do on Linux and anyone may do on PAX** (`priv`;
PAX has no one else, so these are checks that do not exist yet): bind
a port below 1024; `KIOCSOUND` and `KDMKTONE` on the console (the
speaker); open `/dev/console` and `/dev/tty0` (mode 0620 on PAX, never
read); signal pid 1.

**The accounts.** The shell image's `/etc/passwd` is one line,
`root:x:0:0:root:/:/bin/pelt`, and its `/etc/group` `root:x:0:`; there
is no `/etc/shadow`. `tools/mkinitramfs` writes uid and gid 0 for every
entry and `tree.adopt` reads neither field, so an image cannot carry a
file that is not root's.

## B. Linux, measured (item 2)

**The probes** (`notes/px38/probes/`, static, glibc 2.39, built in
`px13-ubuntu` by `probes/build.sh`; digests in `linux/build.txt`; every
call under test a raw `syscall`):

| probe | what it asks | lines a run |
|---|---|---|
| `ids` | every identity call once as root; what a process is told; whether anything checks (also the first program on PAX) | 71 |
| `cred` | every `set*id` call from six user-id states and four group-id states over six values each; groups; `fork` and `execve` | 2,684 |
| `perm` | five actors against a file and a directory of 21 modes each; the sticky bit; `chmod`, `chown`, `utimensat`; `access`; who owns what is made; an AF_UNIX name; a held descriptor | 382 |
| `setid` | nine set-ID files run by a user, three by root; where the bits are not honoured; thirteen changes that may take the bits away | 74 |
| `sig` | seventeen senders against six targets; five readers of each target's `/proc/<pid>` | 144 |
| `priv` | what else is root's: ports, the speaker, devices, the clock, `mknod`, `chroot` | 30 |

**The three runs** (`run-all.sh`): `linux/vm.txt` (`vm-run.sh`: kasumi's
own kernel image, `f4c00d5d…`, booted under QEMU with
`probes/vminit.c` as pid 1; root of the initial user namespace,
`CapEff 000001ffffffffff`; the kernel's default settings),
`linux/vm-protected.txt` (the same with `fs.protected_hardlinks`,
`_symlinks`, `_regular` and `_fifos` set to 1, as distributions set
them) and `linux/ct.txt` (`ct-run.sh`: root of a rootless podman
container, `CapEff 00000000800405fb`, uid map `0 1000 1; 1 100000
65536`, the host's settings: the four at 1, `fs.suid_dumpable` 2).
3,400 lines each (ct's has one more header line). `check-cred.py`, `check-perm.py` and `check-sig.py`
hold a written rule to 2,640, 210 and 102 of those lines a run and
find no exception on any of the three.

**The two roots.** Every table below is vm's unless it says ct. ct
differs from vm-protected in 99 lines (vm-protected from vm in 7:
the protected rows), of these classes and no other:

| class | vm (real root) | ct (root of a user namespace) |
|---|---|---|
| an id with no mapping (70000; 4294967294) | `setuid`, `setgid`, `chown` 0 | -EINVAL |
| a write, truncation, `O_TRUNC`, `pwrite`, `fallocate` or append **by root** to a set-ID file | the bits stay | cleared, as for a user (px36's row) |
| `/proc/<pid>/environ`, `maps`, `auxv`, `io`, `exe`, `cwd`, `root` of another user's process, read by root | 0 | -EACCES |
| `mknod` of a character device; a raw socket; `setpriority` below 0 | 0 | -EPERM, -EPERM, -EACCES |
| `dumpable` after an id change | 0 | 2 (the host's `fs.suid_dumpable`) |
| capability masks, `/dev/null`'s owner (65534), `/proc`'s mount options | | |

So a container's root is a sound reference for every rule below about
**users**, and an unsound one for what **root** may do to set-ID bits,
to other processes' `/proc` and to devices. A PAX test whose reference
is a rootless container must keep those rows out of the comparison (a
`~` line, held to vm's text), as `tests/mpx3-tree` already does for one
of them.

### (a) Credentials

A process has four user ids and four group ids — real, effective,
saved, file-system — and a list of supplementary groups. **Privileged**
below means effective user id 0; the capability mask in every row
agrees (2,640 of 2,640: non-file capabilities exactly when the
effective id is 0, file capabilities exactly when the file-system id
is 0 and some id is 0).

| call | rule, as measured | rows |
|---|---|---|
| `setuid(x)` | -EINVAL for -1. Privileged: real, effective, saved and file-system all become x. Otherwise: 0 only when x is the real or the saved id, and only the effective and file-system ids move; else -EPERM | 36 |
| `setreuid(r, e)` | -1 leaves one alone. Unprivileged: r must be the real or effective id, e the real, effective or saved; else -EPERM and nothing moves. The saved id becomes the new effective id when r is given, or e is given and is not the old real id. The file-system id follows the effective id | 216 |
| `setresuid(r, e, s)` | -1 leaves one alone. Unprivileged: each must be one of the three current ids; else -EPERM and nothing moves. The file-system id follows the effective id | 1,296 |
| `setfsuid(x)` | always answers the previous file-system id; it moves when the caller is privileged or x is one of the four current ids; -1 and a refused x change nothing and are not errors | 36 |
| the four group calls | the same rules on the group ids, **privilege still the effective user id** | 1,056 |
| `getgroups(n, list)` | n 0: the count; n below the count, or negative: -EINVAL; else the list | the `supplementary groups` lines |
| `setgroups(n, list)` | unprivileged: -EPERM (also for the list it already has, and for none). Privileged: the list is kept sorted, repeats and the effective group as given; n above 65,536 or negative -EINVAL; a bad pointer -EFAULT | the same |
| `fork` | the child has the four and four ids and the groups | 7 |
| `execve` | the saved ids become the effective ids; the rest is kept; AT_SECURE is 1 when real and effective differ (user or group) | 7 |

The order that works for dropping from root to a user is `setgroups`,
then the group ids, then the user ids: after the user ids are dropped,
`setgroups` and `setgid` to another group are -EPERM (the `u1000`
rows). `su`, `sg` and `login` all make them in that order (§(e)).

### (b) Permission checks

All on a tmpfs. The actors: **own** (uid 1000, not in the group),
**grp** (in the group by its group id), **sup** (in it by a
supplementary group), **oth**, **root**; the thing is owned 1000:2000.

| what | rule, as measured |
|---|---|
| the class | the caller's file-system user id picks one class — owner, else group (file-system group id or any supplementary group), else other — and only that class's bits are read: the owner of a 0077 file is refused what the others are allowed (105 file rows, 105 directory rows; grp and sup never differ) |
| a file | read needs r, write and `truncate` need w, `O_RDWR` both, `execve` x alone; the errno is -EACCES |
| root | reads and writes any file whatever the mode; executes a file only if some execute bit is set (0100, 0010 and 0001 run; 0000, 0400, 0644 are -EACCES); searches, lists and changes any directory |
| a directory | listing needs r; `stat` of a name in it and `chdir` need x; making, removing or renaming a name (`open(O_CREAT)`, `unlink`, `rename`, `mkdir`, `rmdir`) needs w **and** x; the file's own mode and owner are not asked (root's mode-0000 file is unlinked by anyone with w and x on the directory) |
| the sticky bit | in a 1777 directory of 1000's: a user who owns neither the directory nor the file gets **-EPERM** from `unlink`, from `rename` of it, from `rename` of his own file over it, and from `rmdir`; the directory's owner and root may do all of it; in a 0777 directory everyone may |
| `chmod`, `fchmod` | the owner and root: 0. Anyone else: -EPERM, whatever the file's mode or the descriptor's. The owner setting S_ISGID on a file or a directory whose group he is not in: 0 and the bit is silently dropped. S_ISUID and the sticky bit on a file are kept for an owner |
| `chown` | a user who is not the owner: -EPERM for every argument, `(-1, -1)` included. The owner: the user id may only be his own or -1; the group may be his file-system group, one of his supplementary groups, or the group the file already has; anything else -EPERM. Root: anything. **Every `chown` that succeeds, root's included and `(-1, -1)` included, clears S_ISUID and clears S_ISGID when the file is group-executable**; a directory's bits and the sticky bit stay |
| `utimensat` | times NULL or `{NOW, NOW}`: the owner, root, or anyone with write permission; otherwise **-EACCES**. Any other times (`{1, 2}`, `{NOW, OMIT}`, `{5, OMIT}`): the owner or root; otherwise **-EPERM**, write permission or not. `{OMIT, OMIT}`: 0 for anyone |
| `access`, `faccessat`, `faccessat2` | they ask for the **real** ids: (0, 1000, 0) is told 0 for root's 0600 file and then cannot open it; (1000, 0, 0) is told -EACCES and then opens it. `faccessat2(…, AT_EACCESS)` asks for the effective ids and agrees with `open` |
| `open` and the rest | the **file-system** ids: root after `setfsuid(1002)` cannot open root's 0600 file, opens 1002's, and makes files owned by 1002 — while `kill(1, 0)` is still 0 (signals ask the effective id) |
| who owns what is made | the file-system user id, and the file-system group id — unless the directory is set-group-ID: then the directory's group, a new directory there takes the bit too, and a file made there with S_ISGID by one who is not in that group loses the bit. A symbolic link is its maker's, mode 0777 |
| the umask | `mode & ~umask` for a file, a directory and a socket's name; with umask 0777 the file is 0000 and the descriptor that made it still writes |
| an AF_UNIX name | `connect` needs write permission on the socket's file by the same class rule (-EACCES); read and execute bits are not asked; root connects to a 0000 one (36 rows) |
| a descriptor already open | keeps reading and writing after the file is given to root at mode 0000; a new `open` is -EACCES, `fchmod` on the old one -EPERM |
| the four protected settings (vm-protected, ct) | at 1: opening **with O_CREAT** another's file in a sticky world-writable directory is -EACCES for all but the file's owner (without O_CREAT it opens); following another's symbolic link there is -EACCES unless the link is the follower's or the directory owner's; a hard link to a file one may not both read and write, or to a set-ID file, is -EPERM. At 0 (the kernel's own default, vm) all of these are 0 |

### (c) Set-ID execution, and what clears the bits

By 1000:2000 with groups {2999}, the files on a tmpfs mounted without
nosuid (`mount:` lines):

| file | ids after `execve` (real effective saved fs) | AT_SECURE |
|---|---|---|
| 0755 of 1001:2001 | 1000 1000 1000 1000 / 2000 2000 2000 2000 | 0 |
| 04755 of 1001:2001 | **1000 1001 1001 1001** / groups unchanged | 1 |
| 02755 of 1001:2001 | users unchanged / **2000 2001 2001 2001** | 1 |
| 06755 of 1001:2001 | both | 1 |
| 04755 of 0:0 | 1000 0 0 0, every capability | 1 |
| 04655 of 1001 (no owner execute bit) | honoured | 1 |
| 02745 of 1001:2001 (no group execute bit) | **not honoured** | 0 |
| 06755 of the caller's own | unchanged | 0 |
| 04755 of 1001, run by root | **0 1001 1001 1001, no capability** | 1 |

The supplementary groups never change. The ids stay through a further
`execve` of a plain program. **Not honoured** (ids unchanged, AT_SECURE
0, `execve` 0): on a mount with nosuid; for a `#!` script (the
interpreter runs as the caller); after `prctl(PR_SET_NO_NEW_PRIVS)`.

What takes the bits from a file 1000:2000 mode 6777:

| change | by its owner (in the group) | by another user | by root (vm) | by root (ct) |
|---|---|---|---|---|
| `write` of a byte, `pwrite`, append, `ftruncate`, `truncate`, `O_TRUNC`, `fallocate` | 0777 | 0777 | **6777** | 0777 |
| `write` of no bytes, an `O_RDWR` open, `utimensat`, `rename`, a new hard link; `chmod` to the same mode (owner and root) | 6777 | 6777 | 6777 | 6777 |
| any `chown` (§(b)) | 0777 | — | 0777 | 0777 |

A set-group-ID bit without group execute (`02767`, `06766`): a write by
one in the file's group keeps it, by one who is not clears it, and
S_ISUID goes either way.

### (d) Signals, and what `/proc/<pid>` shows

**`kill(pid, sig)`, `tgkill`, signal 0 included: 0 when the sender's
effective user id is 0, or the sender's real or effective user id
equals the target's real or saved user id; else -EPERM** (102 rows: a
sender whose only match is its saved id is refused; a sender
(0, 1003, 0) is refused every user's process and allowed root's; a
target's effective id is never asked). SIGCONT is 0 in every row (all
in one session; `kill(2)` gives that as the reason; a second session
was not measured). No such pid -ESRCH; a signal number of 65 -EINVAL;
a user's `kill(1, 0)` -EPERM.

`/proc/<pid>` (mounted with no `hidepid`): the directory is the
target's effective user and group, mode 0555. For any reader `status`,
`stat`, `cmdline` and `limits` read. `environ`, `maps`, `auxv`, `io`,
`fd/` and the links `exe`, `cwd` and `root` are for root, and for a
reader with the target's ids **only while the target is dumpable** —
which it stops being at any change of its ids, until an `execve` with
real and effective ids equal; those files are then owned 0:0. Everyone
else: -EACCES.

**Also root's** (`priv`, vm): `bind` to a TCP or UDP port below 1024
(-EACCES for a user; 1024 and up are anyone's; the setting
`net.ipv4.ip_unprivileged_port_start` 1024); a raw socket (-EPERM);
`setpriority` below the current value (-EACCES); raising a hard limit
(-EPERM); `mknod` of a device (-EPERM; a FIFO is anyone's); `chroot`
(-EPERM); `KIOCSOUND` and `KDMKTONE` on a virtual terminal that root opened
and the user inherited (-EPERM); `clock_settime`, `settimeofday`,
`sethostname`, `reboot`, `mount`, `umount2` (-EPERM); writing
`/dev/console`, `/dev/tty0`, `/dev/ttyS0` (0600 root, -EACCES).
`/dev/null`, `/dev/zero`, `/dev/full`, `/dev/random`, `/dev/urandom`
are 0666.

### (e) The userland

Ubuntu 24.04's own binaries (coreutils 9.4, util-linux 2.39.3's `su`,
shadow 4.13's `login`, `passwd`, `sg`, PAM 1.5.3), traced by strace 6.8
in a throwaway container as ct root, with accounts made there (alice
1000, bob 1001, group pack 2000): 37 runs, `straces/NN-*.strace` and
`.out`, read into `straces/summary.txt` by `strace-summary.py`. The
password hashes the tools read are cut from the kept traces.

| tool | identity calls, in order | files it reads | else |
|---|---|---|---|
| `id` | `geteuid`, `getuid`, `getegid`, `getgid`, `getgroups(0)`, `getgroups(n)` | `/etc/nsswitch.conf`, `/etc/passwd`, `/etc/group`, `/proc/sys/kernel/ngroups_max`, `/proc/filesystems` | tries `/var/run/nscd/socket`; `statfs` |
| `id alice`, `groups alice` | none | the same files | |
| `whoami`, `id -u` | `geteuid` | `/etc/passwd` (not for `-u`) | |
| `ls -l`, `stat` | none (`statx` per name) | `/etc/passwd`, `/etc/group`; an unknown id prints as its number (`ls`) or `UNKNOWN` (`stat`) | `lgetxattr`, `listxattr` |
| `chown`, `chgrp` | `fchownat(AT_FDCWD, f, uid, -1 \| gid, 0)`; -EPERM printed as "Operation not permitted" | `/etc/passwd` or `/etc/group` for a name | `-R`: `getdents64` |
| `su alice -c id` (root) | `setgroups(2, [1000, 2000])`, `setgid(1000)`, `setuid(1000)`, `setsid()` (no terminal), then `execve` of the shell | `/etc/passwd`, `/etc/group`, `/etc/shadow`, `/etc/login.defs`, `/etc/pam.d/su` and five more, `/etc/environment`, `/etc/security/limits.conf` | `setpriority`; eight PAM modules |
| `su root` (alice) | the same three with 0; the password read from standard input, checked against `/etc/shadow` by `su` itself (set-user-ID root, mode 4755) | the same | a wrong password: 1 after a delay, `/var/log/btmp` written |
| `sg pack -c id` (alice) | `getgroups`, `setgid(2000)`, `setuid(1000)` | `/etc/group`, `/etc/gshadow` | set-user-ID root |
| `passwd` | `fchown(4, 0, 42)` and `fchmod(4, 0640)` of the new file | `/etc/passwd`, `/etc/shadow`; writes `/etc/nshadow` under a lock on `/etc/.pwd.lock` (`fcntl(F_SETLKW)`), `fsync`, `rename` over `/etc/shadow` | set-user-ID root; `umask(077)` |
| `login` | `setsid`, `ioctl(TIOCSCTTY)`; then per PAM module `setgroups`, `setfsgid`, `setfsuid` there and back (five times); `setgid(1000)`, `setgroups`, `fchown(0, 1000, 5)` and `fchmod(0, 0600)` of the terminal, `setuid(1000)`, `setpgid`, `ioctl(TIOCSPGRP)`; then `execve` of the shell | `/etc/login.defs`, `/etc/pam.d/login`, `/etc/passwd`, `/etc/shadow`, `/etc/group`; looks for `/var/run/utmp`, `/etc/nologin`, `/etc/motd` | `keyctl`; fourteen PAM modules; `alarm` for the prompt |

`/etc/shadow` is `root:shadow` 0640 and its hashes are yescrypt
(`$y$j9T$…`); a locked account's field is `!`. `/etc/passwd` and
`/etc/group` are 0644. `su`, `passwd`, `newgrp`, `chsh`, `chfn`,
`gpasswd` and `mount` are 4755 root; `login` is 0755 (it is started by
root).

The calls in those 37 traces that PAX does not answer today, all 25:
`alarm` (37), `setuid` (105), `setgid` (106), `setpgid` (109),
`getpgrp` (111), `setsid` (112), `setreuid` (113), `setregid` (114),
`getgroups` (115), `setgroups` (116), `setresuid` (117), `setfsuid`
(122), `setfsgid` (123), `getsid` (124), `statfs` (137), `fstatfs`
(138), `getpriority` (140), `setpriority` (141), `lgetxattr` (192),
`listxattr` (194), `keyctl` (250), `pselect6` (270), `set_robust_list`
(273), `signalfd4` (289), `rseq` (334).

**What PAX's own userland does today** (read from their trunks):
boreutils' `ls -l` and `stat` already name owners from `/etc/passwd`
and `/etc/group` read as files (`src/bore/ids.lu`), with no
name-service file, socket or extended attribute; pelt reads its
effective ids from `/proc/self/status` because wolf has no call for
them.

## C. The gap, per stage (item 3)

**Numbers to add: twelve, all in the credentials stage.** Nine are in
the tools' traces — 105, 106, 113, 114, 115, 116, 117, 122, 123 — and
three only in this lane's probes (`linux/probe-calls.txt`): `getresuid`
(118), `setresgid` (119), `getresgid` (120), which the probes need to
set and read a state and which complete the family. No later stage
needs a new number: every path call, `kill`, `bind` and `ioctl` is
already answered and gains a check.

**Seen in a trace and left out**, each with its reason:

| call | who asked | why not |
|---|---|---|
| `setsid` 112, `setpgid` 109, `getpgrp` 111, `getsid` 124 | `su`, `login`, the shell | the job-control lane's (ruling #69 R8, after pelt's sh16) |
| `capget` 125, `capset` 126 | this lane's `setpriv` wrapper only | capabilities are out (§D); stay -ENOSYS |
| `keyctl` 250, `getpriority` 140, `setpriority` 141, `alarm` 37, `pselect6` 270, `signalfd4` 289 | PAM, `script(1)` | Ubuntu's PAM stack and harness, which PAX does not run |
| `statfs` 137, `fstatfs` 138, `lgetxattr` 192, `listxattr` 194 | glibc's and coreutils' SELinux and ACL lookups | PAX's tools are boreutils, which ask none of them |
| `set_robust_list` 273, `rseq` 334 | glibc | -ENOSYS already, tolerated (px26) |

| stage | PAX lacks | refused by name, and the errno | the test that holds it |
|---|---|---|---|
| **1. credentials** | the eight ids and the group list a process; the twelve calls by §B(a)'s rules; inheritance; real `Uid:`, `Gid:`, `Groups:` lines; AT_UID to AT_SECURE; `getuid` and its three from the record | more than 32 groups (if the lane bounds the list): -EINVAL, by name. `capget`, `capset` stay -ENOSYS | `cred` as the first program: its 2,684 lines byte-identical to `linux/vm.txt`'s (root can reach every state, so this needs no account). `check-cred.py` is the rule the kernel code is read against |
| **2. owners** | an owner and a group for an inode, set at creation from the file-system ids and the set-group-ID directory rule; `chown` keeping any id; `stat` and `statx` reporting them; owners in the initramfs (`tools/mkinitramfs` and `tree.adopt` read the cpio fields); `/proc/<pid>` owned by its process | px36's `R_OWNER` (-EINVAL for an id that is not root) **goes**; `/dev` stays fixed, -EROFS, until stage 5 gives the terminal an owner | `perm`'s root rows of sections E and H and `ids`'s `chown` line identical to vm's; `tests/mpx3-tree`'s `~owner` line retired and its refusal count 10 → 9; boreutils' `ls -l` of an image with a user's file prints the name |
| **3. checks on files** | the class rule on `open`, `execve`, `truncate`, `access` and its two (real ids, AT_EACCESS), every path walk's search bit, root's three rules, the descriptor that outlives a `chmod` | nothing new | `perm` sections A, B's first three columns, G and I's held rows as a user |
| **4. checks on names and metadata** | write-and-search to make, remove or rename a name; the sticky bit; the three protected rules (ruling R7); `chmod`, `chown`, `utimensat` by §B(b); the bits cleared by a write, a truncation and a `chown`; `connect` to an AF_UNIX name | nothing new | all of `perm` (382 lines) and `setid`'s `bits:` lines identical to the reference |
| **5. processes and root's things** | the `kill` rule in `kill`, `tgkill`, `tkill`; `bind` below 1024; `KIOCSOUND`, `KDMKTONE`; `/dev` nodes with a mode and owner that are checked, and a terminal that `login` can hand over (`fchown`, `fchmod` on it); `SO_PEERCRED` answered | `/proc/<pid>/environ` and its kin are not there to guard: nothing to refuse | `sig`'s 102 sender rows and `priv`'s user rows |
| **6. accounts** | `/etc/passwd`, `/etc/group` with more than root; a home directory that is its user's; `su` and `login` (ruling R8); `id`, `whoami`, `groups`, `chown`, `chgrp` | a password asked for where none is kept (ruling R1): by name | a typed session, below |
| **7. every suite as a user** | a non-root run of each suite whose calls now have a check | | below |

**The same non-root session on Linux and PAX, byte for byte.** PAX's
`su` and `login` are static Linux programs like pelt and boreutils, so
the reference side runs **the same binaries** in a container whose
`/etc/passwd` is the image's: root's shell, `su <user>`, then `id`,
`whoami`, `touch` and `ls -l` in the home directory, `cat /etc/shadow`
or a root 0600 file refused, `rm /bin/ls` refused, `chmod` of root's
file refused, `kill 1` refused, a file made in `/tmp` and another
user's left alone, `exit` back to root's `id`. `tools/linux-tree`
already runs a session this way as the container's root; on the CI
runner that root is the host's (px36 found the runner's root keeps
set-ID bits on a write, as vm does), on kasumi it is ct, where the six
classes of §B stay out of the comparison.

**Suites that must gain a non-root run**, so that a pass as root
cannot hide a missing or an over-eager check (root is let past all but
one, so a root-only suite sees neither): `tests/mpx3-tree` (its probe
and both typed sessions as a user in his own directory, and the
refusals in root's), `tests/mpx3-shell` and `tests/mpx3-boreutils`
(the run lists as a user: what reads `/bin` still works, what writes
`/etc` does not), `tests/mpx4-unix` (a socket's name by mode),
`tests/mpx4-tcp` and `tests/mpx4-udp` (a low port by a user),
`tests/mpx3-speaker` (the tone by a user), `tests/mpx4-lobo` (a server
that drops to a service account, once lobo can: lobo#52). Every check
lane adds, for each check, a row a user is **refused** and a row a
user is **allowed**: a kernel that refuses everyone passes the first
kind alone. And each plants its break — the check removed — in a
commit and CI run of its own, as the track's rule has it.

## D. The sequence (item 4)

Sizes are the board's: S half a lane or less, M one lane, L more.
"Needs" names what must exist first outside pax.

| lane | one deliverable | done-when | size | needs from wolf / wolf-std / pelt / boreutils |
|---|---|---|---|---|
| **px-U1** credentials | a process has the eight ids and a group list; the twelve calls; `/proc` and the auxiliary vector tell the truth | `cred`'s 2,684 lines byte-identical to Linux as the first program, both tiers, BIOS and UEFI; every existing suite unchanged; the break (a `setuid` by a user that succeeds) seen red | M | nothing: kernel only, at the current pin |
| **px-U2** owners | an inode has an owner and a group; `chown` keeps any id; the image carries owners | `ids` and `perm`'s root rows as vm's; `tests/mpx3-tree`'s refusals 10 → 9; an image with a user's home directory lists as his | M | nothing in the kernel; boreutils' `ls -l` and `stat` as they are |
| **px-U3** checks on files | the class rule where a file is opened, run, truncated or asked about, and on every path walk | `perm` sections A, B (list, stat, chdir), G and the held rows identical to Linux **run by a user** (the probe drops to each actor itself, so no account is needed yet); every existing suite unchanged as root; one break red | M | nothing |
| **px-U4** checks on names and metadata | the directory, sticky, protected, `chmod`, `chown`, `utimensat` and bit-clearing rules; AF_UNIX `connect` | all 382 lines of `perm` and `setid`'s `bits:` lines identical; one break red | L | nothing |
| **px-U5** processes and root's things | who may signal whom; low ports; the speaker; `/dev` with modes that count; `SO_PEERCRED` | `sig`'s 102 sender rows and `priv`'s rows identical for what PAX has; one break red | M | nothing |
| **s-U** (wolf-lang, with lupin's mirror and wolf-std) | wolf can read and set a process's ids and change a file's owner | on the four machines: `os_uid`, `os_euid`, `os_gid`, `os_egid`, `os_groups` (wolf-lang#633); `fs_chown(path, uid, gid, follow)` (wolf-lang#701); **`os_set_ids(uid, gid, groups)`**, one call that makes `setgroups`, then the group ids, then the user ids, and fails whole (no issue yet: to file). `std/os` and `std/fs` wrappers; a `passwd(5)`/`group(5)` reader in std (boreutils' `src/bore/ids.lu` is one) | M | a wolf release and pin bumps in boreutils, pelt and pax after it |
| **bu-U** (boreutils) | `id`, `whoami`, `groups`, `logname`, `chown`, `chgrp` | each differential against GNU as the suite's rule, **also run as a user** in the oracle container; `cp -p` keeps an owner where it may | M | s-U's release |
| **sh-U** (pelt) | the shell knows who it is without `/proc` | `test -r/-w/-x`, `~user` and `$HOME` from the builtins and the two files; its corpus unchanged; a user's session against dash | S | s-U's release |
| **px-U6** accounts | an image with a second account, `su` and `login` as wolf programs under `user/` (ruling R8), boreutils' six tools in it | the typed session of §C byte-identical to the same binaries on Linux, serial and PS/2, both tiers; root's existing sessions unchanged | M | s-U, bu-U, sh-U at their pins; rulings R1 to R3 and R5 |
| **px-U7** every suite as a user | the non-root runs of §C's list; the CI tier they sit in; the words in README and `docs/` (ruling R6) | each listed suite has its user run in CI; a table in `docs/` of every check, the probe line that holds it and the Linux row it was measured at | M | lobo's privilege drop for the lobo row (lobo#52), else that row is named as missing |
| *deferred* **px-U8** passwords and set-ID | a password file, a hash, set-ID honoured at `execve` | by ruling R1 and R5 | L | a password hash in `std/x/crypto` (none today) |
| *deferred* **px-U9** the login session | `login` makes a session and hands over the terminal | after the job-control lane | S | the job-control lane's `setsid`, `TIOCSCTTY`, `TIOCSPGRP` |

**Order.** px-U1 to px-U5 are a chain: each touches `kernel/files` or
`kernel/user`, so one at a time, U1 first. s-U starts beside px-U1 on
day one (it needs nothing of PAX: Linux and macOS answer the calls
already), because a release and three pin bumps stand between it and
px-U6. bu-U and sh-U follow s-U's release. px-U6 needs px-U3 at least
(a second account with no check is theatre) and reads best after
px-U5. px-U7 closes.

**Against job control.** Nothing in px-U1 to px-U6 needs a process
group or a session: the first `su` and `login` set ids and `execve` the
shell inside PAX's one session, which is a named limit (Ctrl-C reaches
both the user's shell and root's, as it reaches every process today).
The job-control lane and this sequence both edit `kernel/signal` and
`kernel/console`; px-U5 is the one that meets it, so px-U5 and the
job-control lane are not run at once. px-U9 is the join.

**Against the CI tiers (px37).** Each px-U lane adds its probe to one
new suite (`tests/mpx5-users` is the obvious name; px37's tiering
decides the spelling of its job), chosen on a PR by the paths
`kernel/files`, `kernel/tree`, `kernel/user`, `kernel/process`,
`kernel/signal`, `kernel/procfs`, `kernel/sched`, and run whole on
trunk. Its Linux reference needs a real root for the root rows: the
runner's is one. px-U7's user runs ride in the suites they belong to,
so they cost legs, not jobs.

**Explicitly out**, each because nothing above depends on it:

- **persistent storage**: accounts live in the boot image; a change to
  `/etc/passwd` lasts until the halt. So no `passwd`, `useradd`,
  `chsh`, and no lock file dance;
- **concurrent logins**: one console, one session; no second terminal,
  no `sshd`, no `utmp`;
- **capabilities**: root is effective user id 0 and nothing finer;
  `capget` and `capset` stay -ENOSYS; no file capabilities, no
  securebits, no ambient set, no `no_new_privs`;
- **namespaces**: no user namespace, so an id is itself and the ct
  rows of §B never arise on PAX;
- **ACLs and extended attributes**; **PAM and the name-service
  switch** (the tools read the two files, as boreutils does today);
- **quotas and limits**: any user can fill the tree to its cap (half
  of memory, 16,384 inodes), take the 64 process slots or the 1,024
  descriptors; `setrlimit` stays -EPERM;
- **set-ID execution and passwords** in the first cut (px-U8);
  **process groups** (the job-control lane); **real hardware**.

## E. Rulings owed, each with a recommendation (item 5)

**R1. Are there passwords at first? — No.** Root may `su` to anyone
without one, as on Linux; a user who asks to become someone else is
refused by name. An image is public and its accounts are in it, so a
password would be a hash anyone can take offline and a default
password would be a weak one by construction; and wolf-std has no
password hash (`std/x/crypto` holds sha2, chacha20, two curves). When
they come (px-U8): a memory-hard hash written in wolf with its
published test vectors (Ubuntu's own is yescrypt, measured), set by
whoever builds the image, **no account with a default password in any
image this project publishes** — a new account is locked (`!`, as
`useradd` left bob).

**R2. A `login` at boot, or a root shell? — The root shell, as
today.** Every existing image, session and test starts as pid 1 pelt,
root; nothing moves. `su <user>` is how a user's shell starts; `login`
exists as a program root may run, and an image may name it as its
first program. A login prompt with no passwords behind it would claim
a gate that is not there: whoever is at the console is root on any
Unix until the disk is theirs to lock.

**R3. The default account. — `pax`, uid 1000, gid 1000, group `pax`,
home `/home/pax`, shell `/bin/pelt`; and a service account `lobo`, uid
and gid 990, no shell, for the server to drop to.** 1000 is where
Ubuntu's `login.defs` starts users (`UID_MIN 1000`, measured) and what
every probe here used; the name is the system's own, with nothing to
explain. The maintainer may want another name; the ids should stay.
(Whether the default account may use the sound device is the same
question: recommend yes, by an `audio` group it is in. Linux has no
OSS device left to measure a mode from.)

**R4. Saved ids and supplementary groups in the first cut? — Both.**
`su`'s first identity call is `setgroups` (measured), and a process
that drops privilege without clearing root's groups keeps root's group
rights. The saved id is one word and is what makes every row of the
2,640 Linux's: without it PAX's `setuid` would follow a rule of its
own that no Linux run could check. Bound the list (32 is NGROUPS in
POSIX's sense; Linux takes 65,536) and refuse more by name.

**R5. Set-ID, given that PAX runs only the image's own programs. —
Not honoured in the first cut: `execve` ignores the bits, as Linux
does on a `nosuid` mount (measured: ids unchanged, AT_SECURE 0).** The
bits are still stored, listed and cleared by the measured rules, so
every listing matches. With no passwords there is no honest use for a
set-ID root program — `su` upward would be a door with no lock — so
privilege only ever drops, and the oldest way up in Unix is closed
rather than guarded. It also makes PAX's limit on running written
files irrelevant to safety instead of load-bearing for it. Honoured
set-ID arrives with passwords, in px-U8, as one decision.

**R6. The security claim. — "Enforced for honest programs; not a
boundary against an attacker", and the docs say both halves.** What
may be said: *PAX applies Linux's ownership and permission rules to
the calls it implements, checked line for line against Linux; a
program running as one user cannot, through those calls, read, change
or signal what belongs to another.* What must be said beside it:
*nobody has attacked this kernel on purpose. Its system calls have
not been fuzzed or audited; programs load at fixed addresses; there
are no quotas, so any user can exhaust memory, inodes or process
slots; it runs on one CPU in a virtual machine.* The claim can grow
only by a lane that tries to break it (a syscall fuzzer as a user, an
audit of every user pointer), which is not in this sequence.

**R7 (new). The protected settings. — On, all four, fixed.** Every
distribution sets them, the CI runner's reference will have them (not
measured here), and they are three rules whose rows are already taken
(`linux/vm-protected.txt`). Off would make PAX match a Linux nobody
runs.

**R8 (new). Where `su` and `login` live. — pax's `user/`, in wolf; the
six identity tools in boreutils.** `id`, `whoami`, `groups`,
`logname`, `chown` and `chgrp` are coreutils with a GNU oracle; `su`
and `login` are a system's own policy (PAM on Ubuntu) with no oracle
to match byte for byte, and are tested as PAX's own binaries on both
systems.

**R9 (new). What root is, without capabilities. — Effective user id 0
for everything but files, file-system user id 0 for files**: the rule
all 2,640 capability masks agree with. And the status lines: print
Linux's full masks for a process whose effective id is 0 and zeros
otherwise, so a program that reads `CapEff` (none of PAX's does) is
told the truth in Linux's words. `capget` stays -ENOSYS.

## 4. Evidence index

Shas are this branch's (`px38`). kasumi paths are under
`~/lanes/px38/`.

### What was written

- The prediction: `3f1c5d1` (§1 to §3, before any measurement).
- The probes: `2e7568d` (`ids`, `cred`, `perm`, `setid`, `sig`,
  `vminit`), `1c5e2ae` (`priv`), `d98aec7` (the AF_UNIX and held rows);
  the runs as they stand were taken with the probes of this note's
  own commit (`linux/build.txt`).
- The runners: `2ae3f83` (`vm-run.sh`, `ct-run.sh`, `pax-boot.sh`),
  `08c8a8c` (`run-all.sh`).
- The models: `963079c` (`check-cred.py`), `08c8a8c`
  (`check-perm.py`, `check-sig.py`).
- The tools' traces: `5cd2db2` (`strace-tools.sh`,
  `strace-tools-run.sh`, `pty-type.py`, `strace-summary.py`,
  `straces/`).

### What was measured, and where it is

- **PAX at `89f04a9`** (the tree of this branch, whose `kernel/`,
  `boot/`, `tools/` and `user/` are trunk's): `pax/pax-ids.txt` (71
  lines), `pax/pax-ids.kernel.txt` (the kernel's -ENOSYS and refusal
  lines), `pax/pax-priv.txt`, `pax/pax-priv.kernel.txt`; the kernel
  `f095f5df…`, wolf 0.2.28 pin `f71ece8`, QEMU TCG (`pax/*.meta`).
  `qemu-halt` exit 0 on both boots: the machine halted.
- **Linux 7.2.8-1-cachyos, three ways**: `linux/vm.txt`
  (`17227722…`), `linux/vm-protected.txt` (`0876f64d…`),
  `linux/ct.txt` (`3586b261…`), 3,400 lines each; `linux/*.meta` (the
  kernel image's digest, QEMU 11.1.1, podman 6.1.3, the image id);
  `linux/build.txt` (the seven binaries' digests; `ids` `a053d49e…`
  and `priv` `a3a24d21…` are the files PAX ran).
- **The rules held to the lines**: `check-cred.py` 2,640 rows a run,
  0 wrong, on all three; `check-perm.py` 210 rows a run, 0 wrong;
  `check-sig.py` 102 rows a run, 0 wrong. Each is a file to run:
  `python3 notes/px38/check-cred.py notes/px38/linux/vm.txt`.
- **The calls the probes make**: `linux/probe-calls.txt` (strace's
  count in ct; `capget` and `capset` there are the `setpriv` wrapper's).
- **The tools**: `straces/` (37 traces and outputs, `uname.txt`,
  `accounts.txt`, `summary.txt`).

### Measured, inferred, not verified

**Measured**: everything in §A's tables and §B; the twelve numbers.

**Inferred** (from a man page or from reading, not run): that a
process's threads should share one record of ids (`nptl(7)`: the
kernel keeps them per thread and glibc makes them one; a raw `setuid`
in one thread of two was not run); that SIGCONT is refused across
sessions (`kill(2)`); that the CI runner has the protected settings on
and its docker root is the host's (px36 measured the second on one
row); the sizes and the order of §D; that words 148 to 253 of the
process area are free; that an `audio` group is the right owner for
the sound device.

**Not verified**:

- No non-root process has ever run on PAX: there is nothing to make
  one with. Every PAX line here is root's.
- Real root was measured on one kernel build only (kasumi's CachyOS
  7.2.8 image under QEMU); the CI runner's kernel and its root were
  not measured by this lane.
- The tools were traced as ct root only, with Ubuntu's PAM stack;
  `login` on a pseudo-terminal inside a container, not on a console.
- `fs.protected_fifos` and `fs.protected_regular` at 2 were set or
  read, not probed (no FIFO row; value 1 only).
- GNU `ls -l` against a kernel that answers -ENOSYS to `lgetxattr`
  and `listxattr` was not run (PAX's `ls` is boreutils').
- Set-ID through a hard link or a rename made by a user, file
  capabilities, a set-ID file on a file system other than tmpfs.
- `kill(-1, sig)` and a process group; the `setpriority` and limit
  rows beyond the two taken.
- The wolf builtins of §D are proposed spellings; none was built, and
  `os_set_ids` has no issue yet.
- Nothing ran on hasu, under KVM, under UEFI, or on the release tier:
  the PAX boots are native, BIOS, TCG.

### Would file (none filed)

1. wolf-lang: no call sets a process's user id, group id or groups
   (`os_set_ids`): `su`, `login` and a server that drops privilege
   cannot be written in wolf. Witness: the 107-name prelude of
   `b407c73b`. Beside wolf-lang#633 and #701, which are open and are
   the other two thirds.
2. boreutils: `id`, `whoami`, `groups`, `logname`, `chown`, `chgrp`
   are missing (39 utilities at `2ab3651`).
3. pax: `tools/mkinitramfs` writes uid and gid 0 for every entry and
   `tree.adopt` reads neither: an image cannot carry a user's file.
4. pax: `prctl(PR_GET_NO_NEW_PRIVS)` and `(PR_GET_SECUREBITS)` are
   -EINVAL where Linux answers 0 (`pax/pax-ids.txt`); `su`, `sg`,
   `passwd` and `login` ask both.
5. pax: `/proc/<pid>/status` prints zero capability masks for root
   (named in `kernel/procfs`; ruling R9 decides it).

## 5. Done-when

- Branch `px38` on origin; a pax PR, open, unmerged; the diff is
  `notes/` only.
- The five items by name: §A (PAX today), §B (Linux, measured), §C
  (the gap), §D (the sequence), §E (the rulings); and the report's
  five sections §1 to §5.
- The probe checklist:
  - [x] `ids` on PAX at trunk and on Linux as vm and ct root
  - [x] `priv` on PAX at trunk and on Linux as vm and ct root
  - [x] `cred` on Linux, three runs; the model fits 2,640 of 2,640
  - [x] `perm` on Linux, three runs; the rule fits 210 of 210
  - [x] `setid` on Linux, three runs
  - [x] `sig` on Linux, three runs; the rule fits 102 of 102
  - [x] 37 traces of Ubuntu's identity tools
  - [ ] any probe on PAX as a user: cannot be run (§A)
- CI green at the head and `lane-audit.sh pax px38 <PR>` exit 0: named
  in the PR body.
- Close nothing; filed nothing (five listed above).
- Trees: kasumi `~/lanes/px38/` keeps `out/` (the runs) and `bin/`;
  its build directory was removed after each PAX boot. No worktree.
