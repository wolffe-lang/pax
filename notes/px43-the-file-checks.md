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
