# px43 — The file checks (P5 lane U3: who may open, run and walk)

Contract: px43's, `sprints/pax/43-the-file-checks/` in wolffe-lang/wolf
(planning commit `ded537f`, read 2026-10-14), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/wave-53.md` down to `wave-45.md`. Branch `px43` in
pax, cut from pax trunk `c81d464`. §1 to §3 are committed before the
first change to the kernel, a tool or a test.

One deliverable: **the class rule** — owner, group, other, chosen by
the file-system user id; "in the group" by `files.member` (the
file-system group id or a supplementary group); file-system user id 0
passes every read and write check, every search, and execute where any
execute bit is set — in one kernel function, called by `open` (read,
write, `O_TRUNC`, `O_CREAT` in a directory), `truncate`, the `access`
family (the real ids by default, the effective ones with
`AT_EACCESS`), `execve`, `chdir` and `fchdir`, and the search of every
directory of every path walk. A descriptor already open keeps the
access it was opened with.

**What this lane does not do.** Directory write for removing or
renaming a name, the sticky rule, the protected settings, `chmod`,
`chown` and `utimensat` ownership, set-ID clearing on a write (U4);
signals, ports, the speaker, `/dev` modes (U5). Set-ID execution stays
unhonoured (R5). The loader limit stays: PAX runs only the archive's
own bytes (px27). The ruled claim is R6's: the checks are **enforced
for honest programs; not a boundary against an attacker**.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read, nor that of
  `su`, `login`, shadow-utils, util-linux or coreutils (ruling #22).
  Facts come from the man pages (`path_resolution(7)`, `inode(7)`,
  `credentials(7)`, `open(2)`, `openat(2)`, `truncate(2)`,
  `access(2)` and `faccessat2`, `execve(2)`, `chdir(2)`, `fchdir`,
  `getcwd(3)`, `getdents64(2)`, `stat(2)`, `unix(7)`), POSIX.1-2024
  (XBD 4.5 file access permissions, 4.16 pathname resolution), the uapi
  headers the refs clone's sparse checkout holds, pax's own source,
  px38's, px39's and px42's recorded Linux answers, and black-box runs
  made the way px38 made them.
- No syscall number is added. No account is made on any host; no
  `sudo`. A Linux answer for root comes from kasumi's own kernel image
  booted under QEMU with a static program as pid 1 (**vm**); a
  rootless container's root is never a reference for what root may do.
  Each compared row names its reference. A test becomes a user through
  `user/elf/as.c`, or a probe drops to its actors itself.
- Refusal cases are built into the image with owners and modes
  (`tools/mkinitramfs` `:MODE:UID:GID`); the only run-time changes of
  mode are the ones a row is about (a descriptor held across a
  `chmod`).
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's
  own glibc.
- Set-ID execution is not honoured; the loader limit is not lifted.
  Nothing calls PAX secure. No word implying filming.
- No build on nomad-1. kasumi and hasu: commands under `bash`, long
  jobs under `setsid` with a pid file and ended by that pid only;
  work under `~/lanes/px43/`, pruned as I go; never `/tmp`. Host ports
  8080 and 8088 are not used. Nothing is installed anywhere.
- No `rm` outside `~/lanes/px43/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled.
- "Seen red" cites a run. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-14)

| input | found |
|---|---|
| pax trunk | `c81d464` (px42 merged), the contract's; `origin/trunk` the same at the start |
| planning repo | `ded537f`: the contract, the campaign file with R1 to R9 |
| the kernel's pin | wolf 0.2.28 (`3215f321…`, pin `f71ece8e`) / lupin 0.1.51 (`kernel/wolf.pin`), unchanged |
| what checks today (read) | `files.exec_lookup` and `files.faccessat` ask "any execute bit" of a regular file; `fchownat` (px42) asks `chown`'s rule. **`walk_k` asks nothing of a directory it passes**; `openat`, `truncate`, `chdir`, `fchdir` ask nothing of who calls. `O_TRUNC` truncates whatever the access mode (`O_RDONLY` included) |
| the walk | `walk_k` in `kernel/files`: every path call goes through it (`walk`, `resolve`, `resolve_k`: 22 call sites, all in `kernel/files`; `unix_bind` and `unix_connect` through `walk_k`); `..` goes up, `.` stays, a symbolic link restarts from its directory or `/` |
| the caller's side | `cred.uid(a, cred.FS)`, `cred.uid(a, cred.REAL)`, `cred.gid(a, …)`, `cred.in_list(a, g)` (public since px42); `files.member(a, g)` asks the file-system group id and the list |
| a node's side | `n_mode(n)` and `n_owner(a, n, which)` (px42): an inode's own; a `/proc` node's by kernel/procfs's rule (directories 0555); `/dev` 0755 root's; the devices' fixed modes |
| `tests/mpx5-users` | `perm` (px38's probe, byte for byte) as the first program: `PERM_LINUX_LINES` 173 of 382; classes `E 71 71 H 13 13 ROOT 81 67 13 1`; 65 `refused:` lines for `execve` of a program written since boot and 3 for a dropped SIGSTOP (`PERM_REFUSED`); the whole text held to `tests/mpx5-users.d/perm.pax` |
| `perm`'s held rows | they cannot be Linux's in `perm` whatever this lane does: the holder stops itself with SIGSTOP, which PAX drops (no job control), so the row runs before root changes the file, and its last column is `fchmod` by one who is not the owner (U4). This lane holds the held-descriptor rows with a probe of its own (§3, P3) |
| px27's limit | `execve` runs a file only while it is the archive's bytes whole: `perm` A's `execve` column is -13 for every row on PAX; 43 of A's 105 rows are `execve 0` on Linux (13 root's, 30 users') |
| `tools/mkinitramfs` | `/PATH=FILE:MODE:UID:GID` and `/PATH/:MODE:UID:GID` (px42); no symbolic link or hard link entry |
| `tools/ci-tiers.map` | `kernel/files`, `kernel/tree`, `kernel/cred` are `@user`'s (19 suites on the pr leg); `tools/mkcred` is derived to `mpx5-users` |
| pax#58 | open: a pipe's and a socket's `fstat` say 0:0 (`~desc`); "in reach if small" |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, QEMU 11.1.1 (TCG), OVMF, `px13-ubuntu` `ad896450…`, `/home` 39 GB free (96%) |
| hasu | Linux 7.2.3, `/dev/kvm`, 171 GB free; BIOS only (pax#56) |

**Drift from the contract, found before any change.**

1. "`perm` … the held-descriptor rows byte-identical to Linux run by a
   user": not reachable in `perm` itself (above: SIGSTOP, and `fchmod`
   by a non-owner is U4's). Read as: the held-descriptor rule shown
   byte-identical by a user in a probe that waits on a pipe, and
   `perm`'s three held lines named.
2. "B (list, stat, chdir)": `perm`'s B line has eight columns. The
   first four (list, stat, chdir, **create**) are this lane's: the
   contract's own item 3 names `O_CREAT` in a directory. The other four
   (unlink, rename, mkdir, rmdir) need write on the directory (U4) and
   match only where the search alone decides.

## 3. Prediction (committed before the first change)

**P1. One rule, one place.** One function in `kernel/files`, `may(a,
who, n, want)`, holds the class rule; `who` says which ids ask (the
file-system ids, or the real ids for the access family). Its callers:
the walk (search of the directory each component is looked up in,
`.` and `..` included), `openat` (read, write, `O_TRUNC` asks write,
`O_CREAT` of a missing name asks write and search of the directory),
`truncate`, `faccessat` (all three numbers), `exec_lookup`, `chdir`,
`fchdir`. No other function reads a mode to decide who may. Files are
checked where they are inodes of the tree; `/dev`'s and `/proc`'s
files keep their present answers (U5 gives `/dev` modes that count);
every directory, synthetic or not, is searched by the rule (theirs are
0755 and 0555, so nothing moves for them). Falsified if a check needs a
second rule.

**P2. Linux's answers, where nobody recorded them** (measured on vm by
this lane's probe `chk`, run as root dropping to px38's five actors,
and again as 1000:1000 through `as`). I expect:
- the search of every directory a component is looked up in,
  including the directory of the last one: a missing name in a
  directory one may not search is -EACCES, not -ENOENT; a name under a
  file -ENOTDIR first; a too-long component there -EACCES;
- `.` alone, `D/.` and `D/..` ask search of the directory they are
  looked up in: -EACCES when it is not searchable (also for a working
  directory that has lost its search bit); `D/` (a trailing `/`)
  asks only what `D` asks, and `D`'s own bits are not read;
- `AT_EMPTY_PATH` on a directory one may not search: 0; `openat`
  relative to it: -EACCES; `fchdir` to it and `chdir` to it: -EACCES;
  `getdents64` on a descriptor opened before its mode changed: 0;
  `getcwd` in a working directory that lost its search bit: the path;
- `open(O_RDONLY | O_TRUNC)` of a file one may read and not write:
  -EACCES and the file untouched (an empty file too); `O_CREAT |
  O_EXCL` of an existing name in a directory without write: -EEXIST;
  `O_CREAT` without `O_EXCL` there: what the file's own mode says;
  `O_WRONLY` of a directory without write: -EISDIR; `truncate` of
  such a directory: -EISDIR; `open` of a socket's name of mode 0000 by
  a user: -EACCES;
- `access`, `faccessat`, `faccessat2(0)` walk and check with the real
  user and group ids (the real group id or a supplementary group);
  privileged when the real user id is 0; `faccessat2(AT_EACCESS)` with
  the **file-system** ids (root after `setfsuid(1002)` is refused
  root's 0600 file), privileged when the file-system user id is 0;
  root's `X_OK` is 0 for a directory of mode 0000 and -EACCES for a
  file with no execute bit;
- `execve` asks execute of the class the file-system ids choose; root
  runs a file with any execute bit; a directory -EACCES;
- a descriptor opened O_RDWR at 0666 keeps reading, writing and
  `ftruncate`ing after the file is made 0000 (by root, or by the user
  who owns it), while a new `open` is -EACCES; `fstat` on it 0.

**P3. The counts.**
- `perm` (px38's probe, as root, dropping to its actors): **295 of
  382 lines Linux's** (from 173): A 62 of 105 whole and the other 43
  Linux's but for the `execve` column (13 root's, 30 users': px27's
  limit, -13 where Linux runs it); B 91 of 105 whole, and its first
  four columns (list, stat, chdir, create) Linux's in all 105 (the 14
  others are rows where the class may search and not write: unlink,
  rename, mkdir and rmdir are U4's); G 11 of 11; C 10, D 2, E 71, F 4,
  H 13, I 22 as now, the nine headers and `perm: done`. The class
  line becomes `E 71 71 H 13 13 ROOT 81 68 13 0` (the root row that
  was a check on `open` is Linux's). `refused:` lines: **43** `execve`
  of a program written since boot (from 65: a refusal by name only
  where the class allows execute) and the three SIGSTOP. `D`'s line
  for `oth` changes text and still differs (its `chmod 0640` is let
  through, U4, and its read-only `open` is now refused).
- `chk` (this lane's probe) as the first program in an image that
  carries its cases (`/k`, owners and modes in the archive; the same
  archive as Linux's root on vm): **every line Linux's, as root
  dropping to the five actors and as 1000:1000**, none by rule, at the
  first boot that runs to the end. That includes the `execve` class
  rows: 21 modes × 5 actors of a program that is an archive file
  (`user/elf/seven.S`, exit 7), which `perm` cannot show.
- Every other session of `tests/mpx5-users` keeps its numbers (`own`
  275 of 278, `ids` 60, `cred` 2,683, `ident` 223, the soaks, `ls`).

**P4. Existing suites.** Every existing suite runs as root and passes
unchanged: no file under `tests/` is edited but `tests/mpx5-users`
and its directory (and `tests/ci-plan` if a place is added). Root's
answers do not move anywhere (file-system uid 0 passes every check
but execute without any execute bit, which is today's answer).
Falsified by an edit to another suite or a red one.

**P5. The soak.** `chk soak 100000`, as root and as 1000:1000: each
round opens, is refused, truncates, asks `access`, walks through a
directory it may and one it may not search, makes and removes a file
in a directory it may write: 0 wrong answers, `MemFree` one number at
each quarter, the frames line flat.

**P6. Plants.** A, a class rule that ignores the group (a member is
asked the others' bits): red first in `perm` at `file 0040 grp`. B, a
walk that skips the search of the last component's directory: red
first in `perm` at `dir 0000 own` (its `stat of a name` 0 where Linux
says -13). Each red in CI with `mpx5-users` the only suite.

**P7. What it costs.** The kernel's text grows by under 2 KiB; no
inode, area word or table changes.

### Corrections to §2 and §3, found after they were committed

- §2 counted 22 call sites of the walk; counted again, 20 calls in 18
  functions (the 22 included two of the wrappers calling each other).
- §2 said `perm`'s held rows cannot match in `perm`; true, and the
  contract's held-descriptor rows are held by `chk` (§F).
- §3 P3 counted `chk` before it was written. It came out at 264 lines
  as root and 46 as 1000:1000 (§G).
- The lane also took pax#58 (the contract: "in reach if small"), which
  §3 did not predict: a pipe's, a socketpair's and an AF_UNIX socket's
  `fstat` owner (§I).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | one function, `may`, called by the walk, `openat`, `truncate`, `faccessat`, `exec_lookup`, `chdir`, `fchdir`; nothing else reads a mode to decide who may | `kernel/files`' `may` (§A), nine call sites, no other permission test in the kernel; the old "any execute bit" tests in `exec_lookup` and `faccessat` are gone into it | right |
| P2 | Linux's unrecorded answers (search of every lookup directory; `.`, `..`; a trailing `/`; AT_EMPTY_PATH; `fchdir`; `getcwd`; O_TRUNC with O_RDONLY; O_CREAT\|O_EXCL -EEXIST; -EISDIR before -EACCES; a socket's name -EACCES; AT_EACCESS the file-system ids; `execve` by class; a held descriptor) | **every one as predicted**, on vm (`tests/mpx5-users.d/linux/chk.txt`); and the PAX kernel written before the measurement answered 260 of `chk`'s 264 lines at its first boot — the four others were the socket's name (PAX said -ENXIO before asking the class), fixed in `openat` | right |
| P3 | `perm` 295 of 382; A 62 + 43 execve-only (30 users'); B 91 whole, four columns 105; G 11; class line `ROOT 81 68 13 0`; 43 `execve` refusals; `chk` every line Linux's as root and as a user | all of it, at the first boot: `E 71 71 H 13 13 ROOT 81 68 13 0 A 105 62 43 30 0 B 105 105 91 G 11 11`, 43 and 3 refusals; `chk` 264 of 264 and 46 of 46 | right |
| P4 | every existing suite green as root, no test edited but `tests/mpx5-users` | `git diff c81d464 --stat -- tests/` is `tests/mpx5-users` and its directory only; `tests/mpx3-tree` four legs green on kasumi (the same 134 assertions as px42's run); the 19 `@user` suites green in CI's pr tier (run 38535304785); every suite on every leg in the labelled full run (the PR) | right |
| P5 | the soak: 0 wrong answers, `MemFree` one number, frames flat | 1,000,000 calls and 200 execs a soak, 0 wrong, one `MemFree` a leg, as root and as 1000:1000, four legs on kasumi and two tiers under KVM | right |
| P6 | plant A red first at `perm`'s `file 0040 grp`; plant B at `dir 0000 own` | both, at exactly those rows, on kasumi and in CI (runs 38535190221, 38535194251) | right |
| P7 | the kernel's text grows by under 2 KiB | **3,376 bytes** (848,779 to 852,155; data +16; `notes/px43/kasumi-kernel-cost.txt`), with pax#58's twenty lines in it | wrong |

## A. The rule, in one place (item 1)

`kernel/files`' `may(a, who, n, want) -> bool`:

- `who` is `cred.FS` (every call but the access family) or `cred.REAL`
  (`access`, `faccessat`, `faccessat2` without AT_EACCESS);
- privileged is `cred.uid(a, who) == 0` (R9): every read, write and
  search; execute of what is not a directory only where some execute
  bit is set;
- anyone else gets ONE class: the owner's bits when that user id is the
  node's owner (`n_owner`, px42), else the group's when
  `member_as(a, who, group)` (that group id or a supplementary group,
  `cred.in_list`), else the others'; `want & 7 & !bits == 0`.

The node's side comes from px42's `n_mode` and `n_owner`, so the rule
reads an inode, a `/proc` directory (0555, its process's ids) and
`/dev` (0755, root's) the same way. `files.member` (px42's, used by
`chown` and the set-group-ID stamp) is now `member_as(a, cred.FS, g)`:
one membership test.

**Every call site** (`git grep -n 'may(a' kernel/`):

| caller | asks | with |
|---|---|---|
| `walk_as` (behind `walk`, `walk_k`, `walk_who`, `resolve`, `resolve_k`, `resolve_who`: all 20 path calls, `bind` and `connect` among them) | MAY_X of every directory a component is looked up in, `.` `..` and the last's included, after -ENOTDIR and before the name's length or existence | `who` |
| `openat`, a name O_CREAT makes | MAY_W \| MAY_X of its directory, before -EMFILE | FS |
| `openat`, a socket's name | the access mode's bits, before its -ENXIO | FS |
| `openat`, a file or directory of the tree | read for O_RDONLY, write for O_WRONLY, both for O_RDWR, write for O_TRUNC of a file; not for a file the call made | FS |
| `truncate` | MAY_W, after -EISDIR and -EINVAL | FS |
| `faccessat` (21, 269, 439) | the mode, of a node of the tree | REAL, or FS with AT_EACCESS |
| `exec_lookup` (`execve`) | MAY_X, after "a directory or no file: -EACCES" | FS |
| `chdir`, `fchdir` | MAY_X of the directory itself, after -ENOTDIR | FS |

Not checked, by design and named: `read`, `write`, `pread`,
`pwrite`, `ftruncate` (which asks only that its descriptor was opened
for writing), `getdents64`, `fstat` — a descriptor keeps what it was
opened with; `/dev`'s devices, `/proc`'s and `/sys`'s files and what
`/dev/std*` reopens keep their present answers (U5 gives `/dev` modes
that count; the reopen was not measured).

## B. The walk (item 2)

Measured on vm (`chk`'s W rows: five directories of 1000:2000 at 0100,
0010, 0001, 0000 and 0444, each actor; a 0700 directory of 1001 in the
middle of a path; the working directory and a directory descriptor root
opened before the actor dropped; four symbolic links through them):

- the directory each component is looked up in is searched: a file, a
  name under a subdirectory, a missing name, `.`, `..`, a name under a
  file and a 256-byte name in a directory one may not search are all
  -EACCES (not -ENOENT, -ENOTDIR or -ENAMETOOLONG); in one he may
  search they are 0, 0, -2, 0, 0, -20, -36;
- the directory itself is not searched to be named: `stat D` and `stat
  D/` are 0 for everyone (its parent is searchable);
- a working directory that lost search: `stat f`, `.`, `..`, `s/f` and
  `chdir s` -EACCES; `getcwd` still answers the path;
- a directory descriptor: `fstatat(fd, "")` with AT_EMPTY_PATH is 0,
  `fstatat`, `openat`, `faccessat` of a name in it and `fstatat(fd,
  "..")` -EACCES, `getdents64` 0, `fchdir` -EACCES;
- a symbolic link is read without asking anything (`lstat`,
  `readlink`); following it asks the search of every directory its
  target passes, from `/` or from the link's own directory;
- the class is chosen once, for directories as for files: the owner of
  a 0010 directory, who is not in its group, may not search it.

PAX's walk answers every one of these rows as Linux does (§G).

## C. `open` and `truncate` (item 3)

`chk`'s O and C rows, and `perm` A and B:

- read, write and both by the class; O_TRUNC asks write whatever the
  access mode (O_RDONLY|O_TRUNC of a 0444 file by a user: -EACCES and
  the file keeps its 7 bytes; an empty file too); root truncates;
- O_CREAT of an existing file asks only the file's own bits; of a
  missing name, write and search of its directory (-EACCES); O_CREAT
  \| O_EXCL of an existing name in a 0555 directory is -EEXIST, not
  -EACCES; a file the call made opens for what was asked whatever its
  mode (px38's umask 0777 row);
- a directory: O_WRONLY -EISDIR before any permission; O_RDONLY asks
  read (list);
- a socket's name of mode 0000: -EACCES to a user, -ENXIO to root
  (PAX's -ENXIO came first before this lane: fixed);
- `truncate` of a directory -EISDIR whatever its mode; of a file, write;
  `ftruncate` -EINVAL on a read-only descriptor, 0 on a write one.

## D. The access family, real against effective (item 4)

`chk`'s A rows: twelve states of real, effective and file-system user
and group ids set by root, and px38's G section:

- `access`, `faccessat`, `faccessat2(…, 0)`: the **real** user id and
  the **real** group id or a supplementary group, for the walk as for
  the file; privileged when the real user id is 0;
- `faccessat2(…, AT_EACCESS)`: the **file-system** ids (the man page
  says "effective"; the effective and the file-system ids apart decide
  it: (1000 0 0) with file-system id 1000 is refused root's 0600 file;
  root after `setfsuid(1002)` is refused it; real, effective 2000 and
  file-system group 2999 is refused a 0040 file of group 2000), which
  is what `open` asks;
- root's X_OK: -EACCES for a file with no execute bit, 0 for a 0100
  file and a 0000 directory.

## E. `execve` (item 5)

`execve` asks execute of the class the file-system ids choose; root
runs a file with any execute bit; a directory is -EACCES; the walk
asks the search of every directory on the way.

**What `perm` cannot show, and `chk` does.** `perm` copies itself to
the tmpfs and runs the copy; PAX runs only an archive file whole
(px27), so **43 of `perm` A's 105 rows remain unmatched in one column**
— every row where Linux runs the copy (`execve 0`): 13 root's, 30 a
user's — and they are held to Linux's text with that one field read as
-13 (`tests/mpx5-users`' class line, `A 105 62 43 30 0`). The loader
limit is not lifted. `chk`'s X rows are the same matrix on archive
files: `user/elf/seven.S` (exit 7) at all 21 of `perm` A's modes, owned
1000:2000 in the image, by all five actors: **105 of 105 rows Linux's**,
`execve`, `access(X_OK)` and `faccessat2(X_OK, AT_EACCESS)` in each;
plus a directory, a program in a 0000 directory and one in a 0100
directory of 1000's, and root after `setfsuid(1002)` (the class is the
file-system id's: 0700 and 0070 refused, 0007 and 0001 run).

## F. Descriptors that outlive a change (item 6)

`chk`'s H rows: each actor opens a 0666 file O_RDWR and O_RDONLY and a
0755 directory, and makes the directory its working directory; root
(waiting on a pipe, not on SIGSTOP) makes both 0000; then the actor:
read on the old read descriptor 0, write and `ftruncate` on the old
O_RDWR one 0, write on the read one -EBADF, `fstat` 0 (mode 0000), a
new open -EACCES both ways, `getdents64` on the old directory
descriptor 0, `fstatat` in it and `fchdir` to it -EACCES, `stat f` in
the working directory -EACCES, `getcwd` 0. Root's row: everything 0.
And `chk user`: 1000:1000 makes its own file and directory 0000 while
holding them (its own `chmod`, allowed to an owner) — the same
answers. **Byte-identical to Linux, run by a user, in both sessions.**
`perm`'s own three held lines stay PAX's text: its holder stops with
SIGSTOP, which PAX drops (no job control), and its last column is
`fchmod` by one who is not the owner (U4).

## G. The probes against Linux; every existing suite (item 7)

Every Linux line is real root's: kasumi's own kernel image (Linux
7.2.8-1-cachyos, `f4c00d5d…`) under QEMU 11.1.1, the program a child
of pid 1, every capability. `chk`'s sessions boot with PAX's own `chk`
archive as their root (`notes/px43/linux-vm.sh`,
`tests/mpx5-users.d/linux/vm-chk.meta`); `own`'s and `perm`'s with
px42's recorder (`vm-own.meta`; `perm` came out byte-identical to
px38's recording for the third time). A user's rows are an actor that
dropped for good (`perm`, `chk`) or the whole program after `as 1000
1000` (`chk-user`, `own-user`, the soaks). No row is compared with a
container's root.

| session | run by | Linux lines | identical on PAX | the rest |
|---|---|---:|---:|---|
| perm | root, dropping to own, grp, sup, oth | 382 | **295** (173 before) | 43 A rows Linux's but for `execve 0` → -13 (px27; 30 a user's), 43 U4 rows (§ What U4 should know), the settings line |
| perm A (a file) | the five actors | 105 | 62 | the 43 `execve` rows |
| perm B, list, stat of a name, chdir, create | the five actors | 105 | 105 (91 whole lines) | 14 rows' unlink, rename, mkdir, rmdir: U4 |
| perm G (real against file-system ids) | five id states and root after `setfsuid` | 11 | 11 | |
| perm held | own, oth, root | 3 | 1 (root's) | SIGSTOP dropped; `fchmod` U4: held by `chk` |
| chk | root, dropping to the five actors and to twelve id states | 264 | **264** | |
| chk-user | 1000:1000 | 46 | **46** | |
| chk-soak, chk-soak-user | root; 1000:1000 | 2, 2 | 1, 1 | `~soak` (free memory, U4 holds PAX's one number) |
| own, own-user (px42's) | root; 1000:1000 | 278, 9 | **277, 9** (275, 8 before) | `~fixed` |
| cred, cred-user, ident, ident-user, ids, soak, soak-user, own-soak, own-soak-user, ls, ls-names | px39's and px42's | | as before: 2,683, 3,983, 223, 127, 60, 1, 1, 1, 1, 18, 18 | unchanged |

`chk`'s first boot on PAX answered 260 of 264 (the socket rows, §C);
every boot since, on every leg, 264.

**Every existing suite ran as root and stayed green.** No file under
`tests/` changed but `tests/mpx5-users` and `tests/mpx5-users.d/`
(`git diff c81d464 --stat -- tests/`). Root's answers moved nowhere: a
file-system user id 0 passes every check this lane adds but execute
without any execute bit, which was already PAX's answer. On kasumi:
`tests/mpx5-users`, all four legs, 72 boots (18 sessions a leg), 313 PASS, 0 FAIL, 0 SKIP;
the same images under `taskset -c 0-3`, 313 PASS, 0 FAIL; `tests/mpx3-tree`,
four legs, 134 PASS, 0 FAIL, 0 SKIP, and under `taskset -c 0-3`, 133
(the build's T0 not repeated); hasu, KVM, BIOS, both tiers, two rounds
of 36 boots, 157 PASS each, 0 FAIL. In CI: the `tier pr` run (19
`@user` suites on native BIOS, every one green) and the labelled `tier
full` run (every suite, every leg) at the head, named in the PR. The
other 17 `@user` suites and the rest are CI's: their programs are not
built with kasumi's glibc (px36, px39).

**A non-root run of an existing suite**: `tests/mpx5-users`' px39 and
px42 user sessions (`cred-user`, `ident-user`, `own-user`, the user
soaks) ran under the checks, unchanged and green. `mpx3-tree`'s session
as a user was not reached (what U7 must add: below).

## H. Soak and plants (item 8)

- **The soak**: `chk soak 100000`, as root and as 1000:1000, on every
  leg: each round opens a file its class refuses and one it allows,
  stats through a directory it may not and one it may search, asks
  `access` and `faccessat2(AT_EACCESS)`, makes and removes a file in a
  0777 directory, truncates a 0444 file, `chdir`s into a 0000
  directory; every 1,000th round runs two archive files (one its class
  may run, one not): 1,000,000 calls and 200 execs, **0 wrong
  answers**, `MemFree` one number at the start and every quarter on
  every leg (249,780 kB native BIOS; the frames line flat, U3).
- **The plants** (each cut from `30eb8cb`, never to be merged):

  | plant | break | red on kasumi | red in CI |
  |---|---|---|---|
  | A, branch `px43-plant-a` `b636d10` | `may` never chooses the group class (a member is asked the others' bits) | `notes/px43/kasumi-plant-a.mpx5-users.out`: U1 `perm` at its line 24, `file 0040 grp : open r 0` where PAX now says -13, and U2 39 `execve` refusals for 43 | run 38535190221, job 115756402367 (`mpx5-users` the only suite; `tier full` red after it): `notes/px43/ci-38535190221-plant-a-mpx5-users.txt` |
  | B, branch `px43-plant-b` `001ac9b` | the walk skips the search of the last component's directory | `notes/px43/kasumi-plant-b.mpx5-users.out`: U1 `perm` at its line 109, `dir 0000 own` (stat of a name 0 for -13) | run 38535194251, job 115756422128: `notes/px43/ci-38535194251-plant-b-mpx5-users.txt` |

  Both stop at the first boot (`stopped early`) after `own` passed in
  it: each plant reddens the row that names its break and nothing
  before it.

## I. pax#58: a pipe's and a socket's owner

Taken because it was small: a pipe (both ends), a socketpair (both
ends) and an AF_UNIX socket are their maker's file-system ids to
`fstat`, as Linux's are (`own`'s `desc` rows, measured by px42: 1000:2999
for `own`, 1000:1000 for `own-user`). The pipe record keeps them in its
word 24 (`P_OWNER`: the frames use words 8 to 23), the socket record in
its word 30 (`U_OWNER`, after the name's 14 words); neither record
grows. `own.c`'s line lost its `~` and `own` was recorded again on real
root: `own` 277 of 278, `own-user` 9 of 9. **Not done, named**: an
AF_INET or TCP socket, an eventfd, an epoll object and an end `accept`
made still say 0:0 (none is measured; `ident`/`own` do not ask).

## What U4 (names and metadata) should know

- **`may` is the rule; call it, do not write a second one.** Directory
  write is `may(a, cred.FS, dir, MAY_W | MAY_X)` — `openat`'s O_CREAT
  already asks exactly that of the directory a name is made in; U4 adds
  it to `mkdirat`, `unlinkat`, `renameat` (both directories),
  `linkat`, `symlinkat`, `mknodat` and `unix_bind` (a socket's name),
  then the sticky rule after it. AF_UNIX `connect` is `may(…, sock's
  inode, MAY_W)` (px38's I rows: read and execute are not asked).
- **What `perm` will move.** At this lane's head `perm` is 295 of 382
  (`tests/mpx5-users`' `PERM_LINUX_LINES`; class line `E 71 71 H 13 13
  ROOT 81 68 13 0 A 105 62 43 30 0 B 105 105 91 G 11 11`). U4's lines:
  B's 14 rows where the class may search and not write (unlink, rename,
  mkdir, rmdir), C's two sticky rows, D's four `chmod` rows (one of
  them, `oth`'s, now carries 7013: its `chmod 0640` is let through and
  its read-only `open` is then refused by this lane's check), F's four
  `utimensat` rows, I's 17 `connect` rows and its two held rows'
  `fchmod` (which also need SIGSTOP: see below), and the settings line:
  with A's 43 `execve` rows, the 87 lines PAX does not yet write as
  Linux does.
- **The settings line and R7.** px38's `perm` recording is the kernel's
  default (all four `protected_*` 0); ruling R7 turns them on in PAX,
  so U4's protected rows compare with `notes/px38/linux/vm-protected.txt`,
  not with `perm.txt` (7 lines differ between the two).
- **`perm`'s held rows cannot match in `perm` until a holder can stop
  itself**: SIGSTOP is dropped (no job control). `chk`'s H rows hold the
  held-descriptor rule with a pipe; U4's `fchmod` by a non-owner can be
  held in the same way.
- **43 of A's rows never match while the loader runs only archive
  files** (`execve 0` read as -13). `chk`'s X rows show `execve`'s rule
  on archive files: 105 of 105.
- `chk` (`user/elf/chk.c`) is this lane's; extend it with U4's rows
  (it runs from an image whose `/k` carries every case with owners and
  modes, recorded with `notes/px43/linux-vm.sh`). Its socket row shows
  `open` of a socket's name asks the class before -ENXIO.
- **Kept answers to watch**: `/dev`'s devices, `/proc` files and what
  `/dev/std*` reopens are not checked on `open` or `access` (U5's
  `/dev` modes); `faccessat2`'s AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH
  are still -EINVAL on PAX (Linux takes them; not this lane's).
- **What U7 must add for `mpx3-tree`** (not reached here): its probe
  `tree` works at `/t` from `/` and does root's things (a `chown` to
  1000, `/dev`, renaming its own archive file), and its Linux side is a
  container's root. A user run needs `tree` (or a part of it) taking a
  base directory, an image with that directory a user's (or `/t/` 0777,
  which `tree soak` would use as is: it only `mkdir`s `/t` and works
  under `/t/s`), `as` in the image, and `tools/linux-tree` running `as
  1000 1000 /bin/tree …` in the container (a rootless container is a
  sound reference for a user's rows). The typed sessions need U6's
  `su`.

## 4. Evidence index

Shas are this branch's (`px43`). kasumi paths are under
`~/lanes/px43/`; hasu's likewise.

### What was written

- The prediction: `41b1220` (§1 to §3, before any change).
- The programs: `c06abb8` (`user/elf/chk.c`, `user/elf/seven.S`,
  `tools/mkcred` builds both).
- The recorder: `91db220` (`notes/px43/vminit.c`, `linux-vm.sh`,
  `build.sh`).
- The kernel: `40cc79e` (`kernel/files`: `may`, `member_as`, the walk,
  `openat`, `truncate`, `faccessat`, `exec_lookup`, `chdir`, `fchdir`;
  the socket-name ordering was folded in before the commit), `4d82d7b`
  (`kernel/files`, `kernel/unix`: pax#58).
- The suite: `08b6115` (real root's `chk` recordings), `30eb8cb`
  (`tests/mpx5-users`: `chk`'s four sessions, `perm.pax`, the counts
  and classes), `6595c69` (`user/elf/own.c`'s `desc` line and `own`
  re-recorded), `00a2689` (the suite's words; `~desc` gone).
- The words: `dc168fb` (`kernel/README.md`), `3a6c841`
  (`docs/SOURCES.md`), `8a289aa` (CHANGELOG).

### What was measured, and where it is

- **Linux, real root**: `tests/mpx5-users.d/linux/chk.txt`,
  `chk-user.txt`, `chk-soak.txt`, `chk-soak-user.txt` with
  `vm-chk.meta` (the kernel image's digest, QEMU's, the `chk` archive's
  `74d65b00…`, `chk` `75b1e8a7…`, `seven` `beddda7c…`, `as`, `vminit`);
  `own.txt`, `own-user.txt`, `own-soak*.txt` again with `vm-own.meta`
  (`own` `9228e95e…`; `perm` `e75fe694…`, px38's digest, its section
  the same bytes).
- **The kernel's cost**: `notes/px43/kasumi-kernel-cost.txt`.
- **PAX**: `notes/px43/kasumi-mpx5-users-00a2689.out` (four legs),
  `notes/px43/kasumi-taskset-0-3-mpx5-users-00a2689.out`,
  `notes/px43/kasumi-mpx3-tree-00a2689.out`,
  `notes/px43/kasumi-taskset-0-3-mpx3-tree-00a2689.out`,
  `notes/px43/hasu-kvm-00a2689.log`.
- **The plants**: §H.
- **CI**: run 38535304785 (`tier pr` at `00a2689`, 32 jobs, every one
  green). The pull request's own runs at its final head (the pr tier,
  then the labelled full run) are named in the PR: a commit naming
  them would move the head.

### Measured, inferred, not verified

**Measured**: everything in §A to §I.

**Inferred**: that `/dev/std*`'s reopen of a file asks the class on
Linux (it reopens through `/proc/self/fd`; not measured, so PAX leaves
it unchecked); that an AF_INET socket's and an eventfd's `fstat` owner
are their maker's on Linux (not asked); that every other kernel path
that names a file goes through `walk_as` (read: every `walk`/`resolve`
caller in `kernel/files`, and nothing outside `kernel/files` resolves a
user's path — `process` calls `exec_lookup`).

**Not verified**:

- Real root was one kernel build (kasumi's CachyOS 7.2.8); the CI
  runner's Linux was not asked.
- The other 17 `@user` suites did not run on kasumi or under KVM: CI
  only (their programs must not be built with kasumi's glibc).
- UEFI under KVM on hasu (pax#56): BIOS only there.
- `faccessat2` with AT_SYMLINK_NOFOLLOW or AT_EMPTY_PATH (-EINVAL on
  PAX before and after this lane).
- More than one process changing a mode while another walks (PAX runs
  one CPU; a system call runs with interrupts off).
- `execve` of a file written since boot by its class: PAX refuses it by
  name whatever its mode (px27), so the class decides only for archive
  files.

### Issues

- **To close at merge**: pax#58 (a pipe's, a socketpair's and an AF_UNIX
  socket's owner; an AF_INET socket, an eventfd and an epoll object
  still 0:0 and unmeasured — the orchestrator may prefer to narrow it
  rather than close it).
- **Would file (none filed)**:
  1. pax: `faccessat2` refuses AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH
     (-EINVAL); Linux takes both.
  2. pax: `perm`'s held rows need a holder that can stop itself
     (SIGSTOP is dropped: job control).
- Not chased, did not occur in this lane's runs: pax#45, #47, #53.

## 5. Done-when

- Branch `px43` on origin; pax PR #59, open, unmerged.
- The five sections §1 to §5; the eight items §A to §H (and §I,
  pax#58).
- The test checklist:
  - [x] `tests/mpx5-users`, native and release, BIOS and UEFI, kasumi (TCG)
  - [x] the same under `taskset -c 0-3`
  - [x] the same images under KVM on hasu (BIOS)
  - [x] `tests/mpx3-tree`, four legs, kasumi, and under `taskset -c 0-3`
  - [x] `tools/ci-plan` on the branch's paths (19 `@user` suites, pr tier; no map line needed)
  - [x] plant A red on kasumi and in CI; plant B the same
  - [x] the 19 suites of the pr tier: run 38535304785
  - [ ] the pr tier at the final head, and all suites on every leg (`tier full`): named in the PR
- `wolf/tools/lane-audit.sh pax px43 59` exit 0: named in the PR.
- Close pax#58 at merge; nothing filed.
- Trees: kasumi `~/lanes/px43/` keeps `out/`, `bin/`; build
  directories removed. hasu `~/lanes/px43/` keeps `out/`. Plant
  branches `px43-plant-a` and `px43-plant-b` stay on origin, never to
  be merged; their local worktrees are removed.
