# px44 — The names (P5 lane U4: who may make, remove, rename, link and change)

Contract: px44's, `sprints/pax/44-the-names/` in wolffe-lang/wolf
(planning commit `3698346`, read 2026-10-14), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9; R7: the
four `fs.protected_*` settings on, fixed) and the rules of
`sprints/crawl-54.md` and `sprints/wave-53.md` down to `wave-45.md`.
Branch `px44` in pax, cut from pax trunk `e4755fd`. §1 to §3 are
committed before the first change to the kernel, a tool, a probe or a
test.

One deliverable: **the rules on names and metadata** — write and search
of the directory for every call that makes, removes, renames or links a
name (`mkdirat`, `unlinkat`, `renameat` on both directories, `linkat`,
`symlinkat`, `unix_bind`); write on an AF_UNIX socket's name for
`connect`; the sticky bit; the four protected settings, on and fixed;
who may `chmod` and set times; and when a write or a `chmod` takes the
set-ID bits away — all by px43's one class rule (`kernel/files`' `may`)
and px42's group test (`member`, `member_as`), never a second one.

**What this lane does not do.** Signals, ports, the speaker, `/dev`
modes, `SO_PEERCRED` (U5); job control (`perm`'s held rows need a
holder that stops itself with SIGSTOP, which PAX drops); the loader
limit (PAX runs only the archive's own bytes, px27: `perm` A's 43
`execve` rows). Set-ID execution stays unhonoured (R5). The ruled claim
is R6's: the checks are **enforced for honest programs; not a boundary
against an attacker**.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read, nor that of
  `su`, `login`, shadow-utils, util-linux or coreutils (ruling #22).
  Facts come from the man pages (`path_resolution(7)`, `inode(7)`,
  `credentials(7)`, `proc_sys_fs(5)` (the four protected settings),
  `mkdir(2)`, `unlink(2)`, `rmdir(2)`, `rename(2)`, `link(2)`,
  `symlink(2)`, `symlink(7)`, `chmod(2)`, `utimensat(2)`, `open(2)`,
  `write(2)`, `truncate(2)`, `fallocate(2)`, `copy_file_range(2)`,
  `sendfile(2)`, `splice(2)`, `unix(7)`, `bind(2)`, `connect(2)`),
  POSIX.1-2024 (XBD 4.5 file access permissions, XSH `rename()`,
  `unlink()`, `rmdir()`, `chmod()`, `futimens()`, `write()`), the uapi
  headers the refs clone's sparse checkout holds, pax's own source,
  px38's, px39's, px42's and px43's recorded Linux answers, and
  black-box runs made the way px38 and px43 made them.
- No account is made on any host; no `sudo`. A Linux answer for root
  comes from kasumi's own kernel image booted under QEMU with a static
  program as pid 1 (**vm**), here with the four protected settings
  written to 1 before the probe runs (**vm-protected**, px38's second
  run); a rootless container's root is never a reference for what root
  may do, and is not used. Each compared row names its reference. A
  test becomes a user through `user/elf/as.c`, or a probe drops to its
  actors itself.
- Refusal cases are built into the image with owners and modes
  (`tools/mkinitramfs` `:MODE:UID:GID`); the only run-time changes are
  the ones a row is about, and what the archive cannot carry (a
  symbolic link, a socket's name) is made at run time by the user who
  is to own it (a child that became that user), never by `chown`.
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's
  own glibc.
- Set-ID execution is not honoured; the loader limit is not lifted; no
  job control. Nothing calls PAX secure. No word implying filming.
- No build on nomad-1. kasumi and hasu: commands under `bash`, long
  jobs under `setsid` with a pid file and ended by that pid only; work
  under `~/lanes/px44/`, pruned as I go; never `/tmp`. Host ports 8080
  and 8088 are not used. Nothing is installed anywhere.
- No `rm` outside `~/lanes/px44/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR. No run
  of another lane is cancelled.
- "Seen red" cites a run. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-14)

| input | found |
|---|---|
| pax trunk | `e4755fd` (px43 merged), the contract's; `origin/trunk` the same at the start |
| planning repo | `3698346`: the contract, the campaign file with R1 to R9 |
| the kernel's pin | wolf 0.2.28 / lupin 0.1.51 (`kernel/wolf.pin`), unchanged |
| the class rule | `kernel/files`' `may(a, who, n, want)` (px43), nine call sites: the walk's search, `openat` (the access mode, O_TRUNC, O_CREAT's directory), `truncate`, `faccessat`, `exec_lookup`, `chdir`, `fchdir`; `member`/`member_as` the group test |
| what asks nothing today (read) | `mkdirat`, `unlinkat`, `renameat`, `linkat`, `symlinkat`, `unix_bind` ask only the walk's search; `unix_connect` asks nothing of the name; `fchmodat`/`fchmod` let anyone change any mode of the tree; `utimensat` lets anyone set any time; no write, truncation or `chmod` takes a set-ID bit (only `chown` does, px42); `mknodat` is refused by name (-EPERM) for everyone |
| the protected settings | not read anywhere; `/proc/sys/fs/` holds only `file-nr`, so `perm`'s first line reads `?` four times; `fallocate` (285) is -ENOSYS |
| `tests/mpx5-users` | `perm` against px38's **vm** recording (all four settings 0): 295 of 382 (`PERM_LINUX_LINES`); against **vm-protected** (R7's reference, `notes/px38/linux/vm-protected.txt`'s `perm` section, which differs from vm's in its settings line and the four `protected` lines): **291 of 382**. `chk` 264 of 264, `chk-user` 46 of 46 (recorded with the settings at the kernel's default 0) |
| `perm`'s non-Linux lines (px43's 87) | A 43 (`execve`, px27), B 14 (directory write), C 2 (sticky), D 4 (`chmod`), F 4 (`utimensat`), I 17 (`connect`) and 2 held (own's and oth's), the settings line; against vm-protected also the 4 `protected` lines |
| `setid` (px38's probe) | not run on PAX yet; its 50 `bits:` lines (vm-protected) are the campaign's other done-when for U4 |
| `tools/mkinitramfs` | files and directories with `:MODE:UID:GID`; no symbolic link, hard link or socket entry |
| `tools/ci-tiers.map` | `kernel/files`, `kernel/tree`, `kernel/procfs`, `kernel/cred` are `@user`'s (19 suites); `kernel/unix` is `@net`'s; `tools/mkcred` derives to `mpx5-users` |
| pax#60 | open: `faccessat2` refuses AT_SYMLINK_NOFOLLOW and AT_EMPTY_PATH (-EINVAL); "if in reach" |
| kasumi | Linux 7.2.8-1-cachyos, 16 cpus, QEMU 11.1.1, `px13-ubuntu`, `/home` 33 GB free (97%), load 21 to 38 |

## 3. Prediction (committed before the first change)

**P1. One rule, called; two ownership tests beside it.** Directory
write is `may(a, cred.FS, dir, MAY_W | MAY_X)` at every call that makes,
removes, renames or links a name; `connect` is `may(a, cred.FS, name,
MAY_W)`; `utimensat`'s writer is `may(…, MAY_W)`; the hard-link rule's
"may read and write" is `may(…, MAY_R | MAY_W)`; "in the group" is
`member` everywhere. What is not a class question is an ownership
question, asked by one helper each: **the sticky rule** (file-system
user id 0, the name's owner, or the directory's owner) and **the
owner-or-privileged test** (`chmod`, `utimensat`'s explicit times, the
protected rules' owner clauses). No other function reads a mode's
class bits to decide who may. Falsified if a call needs a second class
rule.

**P2. Linux's answers where nobody recorded them** (measured on
vm-protected by this lane's rows of `chk`, run as root dropping to
px38's five actors and to chosen id states, and again as 1000:1000
through `as`). I expect:

- *Directory write.* A name made (`mkdir`, `symlink`, `link`, `bind`)
  in a directory the class may search but not write: -EACCES; but a
  name that exists there: -EEXIST (`bind` -EADDRINUSE) — existence is
  answered first. A name removed or renamed (`unlink`, `rmdir`,
  `rename`) that is missing: -ENOENT; one that is there: -EACCES before
  what it is (`unlink` of a directory, `rmdir` of a file or of a full
  directory). `rename` asks write and search of both directories (from
  a 0555 one into a 0777 one, and the other way: -EACCES); a directory
  moved to another parent also needs write on itself (`rename(2)`: its
  `..`), but not when it stays in its parent. `rename` of a name onto
  itself in a 0555 directory: -EACCES.
- *Sticky.* In a sticky directory, `unlink`, `rmdir`, `rename` of a
  name and `rename` over a name by one who owns neither the name nor
  the directory and is not file-system user id 0: **-EPERM**, asked
  after write and search (-EACCES first); a sticky directory that is
  not world-writable (1771) is sticky too. Root after `setfsuid(1002)`
  is refused (-EPERM); (0, 1000, 0) after `setfsuid(0)` is not.
- *protected_symlinks.* Following a symbolic link in a sticky
  world-writable directory: -EACCES unless the follower's file-system
  user id is the link's owner or the directory's owner is; root
  included (px38 measured root refused 1002's link); for a link met
  in the middle of a path as for the last; never for `lstat` or
  `readlink`; not in a 1771 directory nor in a 0777 one.
- *protected_regular.* `open` with O_CREAT (without O_EXCL) of an
  existing regular file in a sticky world-writable directory: -EACCES
  unless the file is the opener's or the directory owner's, whatever
  the access mode; root included; O_CREAT|O_EXCL -EEXIST first; not in
  1771 or 0777 directories.
- *protected_hardlinks.* `link` to a file by one who is neither its
  owner nor file-system user id 0: -EPERM unless it is a regular file
  without S_ISUID, without S_ISGID together with group execute, which
  the caller may read and write by the class rule; a symbolic link
  linked itself: -EPERM; a directory -EPERM (as before). Root after
  `setfsuid(1002)`: -EPERM like a user.
- *protected_fifos* has nothing to act on (PAX makes no FIFO: `mknod`
  is refused by name); the four files under `/proc/sys/fs/` read `1`,
  mode 0600, root's.
- *`chmod`.* `chmod`, `fchmodat` and `fchmod` (any descriptor) by one
  who is not the owner and not file-system user id 0: -EPERM, after
  the path's errors (an unsearchable directory: -EACCES); root after
  `setfsuid(1002)` -EPERM on 1000's file and 0 on 1002's; S_ISGID set
  by an owner not in the file's group (its file-system group id nor a
  supplementary one) is dropped without an error, on a file and on a
  directory; kept for one in it by a supplementary group; S_ISUID and
  the sticky bit kept.
- *`utimensat`.* NULL and {NOW, NOW}: the owner, file-system user id 0,
  or one the class rule gives write, else -EACCES; any other times but
  {OMIT, OMIT}: the owner or file-system user id 0, else -EPERM;
  {OMIT, OMIT} 0. By descriptor (`futimens`) the same, write asked of
  the file by the class rule, not of the descriptor's access mode.
- *Set-ID bits.* A write of at least one byte (`write`, `writev`,
  `pwrite`, append), `truncate`, `ftruncate` (even to the same length),
  O_TRUNC (an empty file too), `fallocate`, and `copy_file_range`,
  `sendfile` and `splice` into the file, by one who is not file-system
  user id 0: S_ISUID goes, and S_ISGID when the file is group-executable
  or the writer is not in its group (px38's `setid`: 2767 kept by a
  member, cleared by another; root keeps all). The writer's ids at the
  write decide, not the opener's. Root after `setfsuid(1002)` clears.
- *`connect`.* Write on the socket's name by the class rule (-EACCES),
  asked before whether anything listens: a 0000 name whose socket has
  closed -EACCES to a user; a regular file's name -EACCES when the
  class may not write it, -ECONNREFUSED when it may. `bind` asks write
  and search of the directory after -EADDRINUSE; a socket already bound
  binding again into a directory it may not write: -EINVAL.

**P3. The counts.**

- `perm` (px38's probe, as root, dropping to its actors), against
  **vm-protected** (R7): **337 of 382 lines** (from 291; 295 of 382
  against vm before, which is no longer the reference). The 45 left:
  A's 43 `execve` rows (px27, held to Linux's text with that one field
  read as -13) and **two held rows** (own's and oth's: the holder does
  not stop, SIGSTOP being dropped, so the file is still 1000's and
  0666 when they ask; both become their own named text). B 105 of 105,
  C 12 of 12 (eight sticky and plain rows, the four `protected` rows),
  D 6 of 6, E 71, F 8 of 8, G 11, H 13, I's 36 `connect` rows and its
  bound line, root's held row, and the settings line Linux's. The
  class line becomes `E 71 71 H 13 13 ROOT 81 68 13 0 A 105 62 43 30 0
  B 105 105 105 G 11 11` and, new, `C`, `D`, `F`, `I` and `P` whole.
  `refused:` lines: 43 (px27) and 3 (SIGSTOP), as now.
- `setid` (px38's probe, new to the suite, as root dropping to its
  users): **its 50 `bits:` lines Linux's** (vm-protected), with
  `fallocate` (mode 0) added for its three rows; its `execve` rows stay
  PAX's (set-ID execution unhonoured, R5; copies written since boot,
  px27), held to PAX's text.
- `chk` as the first program in an image that carries the new cases:
  its first 264 lines unchanged (the settings change none of them),
  and **every new line Linux's** (vm-protected), as root dropping to
  the five actors and as 1000:1000 (`chk-user`), none by rule, at the
  first boot that runs to the end — falsified by any line PAX answers
  otherwise at that boot.
- Every other session of `tests/mpx5-users` keeps its numbers (`own`
  277 of 278 and `own-user` 9 of 9 against recordings with the settings
  at 0: no `own` row is in a sticky world-writable directory).

**P4. Existing suites.** Every existing suite runs as root and passes
unchanged: file-system user id 0 passes the directory, sticky,
`chmod`, `utimensat` and hard-link rules and keeps set-ID bits; the
protected symlink and regular rules apply to root too, but no existing
image has a link or a file of another owner in a sticky world-writable
directory. No file under `tests/` is edited but `tests/mpx5-users` and
its directory (and `tests/ci-plan` if a place is added). Falsified by
an edit to another suite or a red one.

**P5. The soak.** `chk soak 100000`, as root and as 1000:1000, with
the rows this lane adds in each round (a name made and removed in a
directory one may not write, a rename across two directories, a rename
in a sticky directory, a hard link to root's 0600 file, an O_CREAT
open in a sticky world-writable directory, a `chmod` and a time set on
root's file, a byte written to a set-ID file): 0 wrong answers,
`MemFree` one number at each quarter, the frames line flat.

**P6. Plants.** A, the sticky rule ignored: red first in `perm` at `sticky
1777 dir of 1000 grp` (its unlink of 1000's file 0 where Linux says
-1). B, a `rename` that asks write of the old name's directory only:
`perm` stays green (its renames stay in one directory) and `chk` goes
red first at its first row that renames from a writable directory into
a 0555 one. Each red in CI with `mpx5-users` the only suite.

**P7. What it costs.** The kernel's text grows by under 4 KiB; no
inode, area word or table changes; `/proc/sys/fs/` gains four fixed
files.

### Corrections to §2 and §3, found after they were committed

- §3 P2 named `chk`'s rows before they were written; they came out as
  eight sections (N, K, P, M, T, B, U, R): 75 lines as root dropping to
  the actors and two id states, 19 as 1000:1000 (§G).
- §3 P3 said the settings' files are mode 0600: measured 0644 (§C).
- The soak first failed its own free-memory check on every leg (one
  frame, 4 kB, gone before the first quarter and flat after: the
  set-ID file the archive carries takes a frame of its own at its first
  write). Not a leak: the soak now writes that file once before it
  counts (`c7e5c4a`), and was recorded again on Linux (`3f0c8b9`). The
  red run is kept on kasumi (`~/lanes/px44/keep/`).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | directory write, `connect`, the writer of `utimensat` and the hard-link rule's read and write all `may`; the group `member`; the rest two ownership tests | `may` gains seven call sites (§A); the ownership tests are `owns` and `sticky_ok`, plus the three protected helpers, which ask owners only; no other function reads a class's bits | right |
| P2 | Linux's unrecorded answers (§3 list) | right but for five: **`rename` of a name onto itself** in a 0555 directory is 0 (two names of one file: nothing asked), not -EACCES; **`link`** by a non-owner of a file it may not write, into a 0555 directory, is -EPERM (protected_hardlinks before the directory's -EACCES), which §3 did not order; **a bound socket's second `bind`** into a 0555 directory is -EACCES for a user (the directory before the -EINVAL); **protected_symlinks** acts only on a path's last component — a link in the middle of a path is followed by anyone; the settings' files are **0644**. The kernel was written before the measurement and corrected to it at these five places before its first boot (so P3's "first boot" is not a test of P2) | wrong (5) |
| P3 | `perm` 337 of 382 against vm-protected; `setid` 50 of 50 `bits:`; `chk` every new line Linux's, as root and as a user; other sessions unchanged | `perm` **337** (`ALL 337`; B 105, C 12, D 6, F 8, I 36 whole; the 43 `execve` rows and own's and oth's held rows left); `setid` **50 of 50**; `chk` **339 of 339**, `chk-user` **65 of 65** at the first boot of the corrected kernel; `own` 277 of 278, `own-user` 9 of 9, every other session as before | right |
| P4 | every existing suite green as root; no test edited but `tests/mpx5-users` | `git diff e4755fd --stat -- tests/` is `tests/mpx5-users` and its directory only; `mpx3-tree` and the CI tiers below | right |
| P5 | the soak: 0 wrong, `MemFree` one number, frames flat | 2,000,000 calls and 200 execs a soak, 0 wrong, as root and as 1000:1000, every leg; `MemFree` one number after the correction above | right after a correction to the probe |
| P6 | plant A red first in `perm` at `sticky … grp`; plant B `perm` green, `chk` red first at its first rename into a 0555 directory | both, at exactly those rows (§H) | right |
| P7 | under 4 KiB of text | **7,104 bytes** (852,155 to 859,259; rodata +144, data +56; `notes/px44/kasumi-kernel-cost.txt`) | wrong |

## A. One rule, called (P1, item 1)

`kernel/files`, every new call site of `may` (`git grep -n 'may(a' kernel/`):

| caller | asks | when |
|---|---|---|
| `unname` (behind `unlinkat`, a file and AT_REMOVEDIR) | MAY_W \| MAY_X of the directory, then `sticky_ok` | after the walk, the trailing-slash and `.`/`..`/`/` answers; before -EISDIR, -ENOTDIR, -ENOTEMPTY |
| `may_make` (`mkdirat`, `symlinkat`, `linkat`'s new directory, `unix_bind`) | MAY_W \| MAY_X of the directory | after -EEXIST (-EADDRINUSE), -ENOENT and /dev's and /proc's answers; `bind` before a bound socket's -EINVAL; `link` after the hard-link rule |
| `renameat` | MAY_W \| MAY_X of both directories; then `sticky_ok` for the old name and a name replaced; MAY_W of a directory that changes parent | after every structural answer and "two names of one file" (0) |
| `may_hardlink` (`linkat`) | MAY_R \| MAY_W of the file, for a non-owner who is not file-system user id 0 | after -EEXIST; before the directory |
| `utimensat` | MAY_W of the file, for NULL or {NOW, NOW} by one who does not own it | after the walk and {OMIT, OMIT} |
| `unix_connect` | MAY_W of the name | before whether anything listens |

Beside it: `owns` (file-system user id 0 or the owner: `chmod_as`,
`utimensat`, `may_hardlink`), `sticky_ok`, `may_follow`,
`may_creat_open`, and `wrote` (set-ID bits), which asks `member`.
Asked of the tree's directories only: `/dev`'s and `/proc`'s keep their
answers (-EROFS, -ENOENT) to making and removing names.

## B. Directory write (item 1) and the sticky bit (item 2)

Measured on vm-protected (`chk` N and K, `perm` B and C):

- a name made (`mkdir`, `symlink`, `link`, `bind`) in a directory the
  class may search but not write: -EACCES; an existing name there
  -EEXIST (`bind` -EADDRINUSE) first; a missing one -ENOENT; a name
  that is there -EACCES before what it is (`unlink` of a directory,
  `rmdir` of a file or a full one: root's -EISDIR, -ENOTDIR,
  -ENOTEMPTY);
- `rename` asks both directories (out of a 0555 one -EACCES, into one
  -EACCES); a directory moved to another parent needs write on itself
  (a 0555 one -EACCES to everyone but root, a 0755 one of 1000's moved
  by 1000 only), renamed in its own parent it does not; two names of
  one file: 0 with nothing asked;
- a bound socket binding again into a 0555 directory: -EACCES for a
  user, -EINVAL for root;
- sticky: in a 1777 directory of 1000's a name goes for its owner, the
  directory's owner and root (-EPERM otherwise: `unlink`, `rmdir`,
  `rename` away and `rename` over); in root's 1777 directory a user's
  own name only; in a 1771 one (not world-writable) the same rule; one
  who may not write the directory is told -EACCES first;
- root after `setfsuid(1002)` is refused (-EPERM) where 1002 would be;
  (0, 1000, 0) after `setfsuid(0)` is root again (R9).

## C. The protected settings, on and fixed (item 3, R7)

- `/proc/sys/fs/protected_hardlinks`, `_symlinks`, `_regular`,
  `_fifos`: `1`, mode 0644, root's (`perm`'s settings line Linux's at
  last);
- **symlinks**: a link that is a path's last component, in a sticky
  world-writable directory, is followed (stat, open, `access`, `chdir`)
  only by its owner, or by anyone when the directory's owner owns it —
  root included (refused 1002's link in 1000's directory); a link met
  in the middle of a path is followed by anyone; `lstat`, `readlink`
  and `utimensat(AT_SYMLINK_NOFOLLOW)` never follow; not in a 1771
  directory nor a 0777 one;
- **regular**: O_CREAT (any access mode, without O_EXCL) of an existing
  regular file in a sticky world-writable directory: -EACCES unless the
  opener or the directory's owner owns it — root included; without
  O_CREAT it opens; O_CREAT\|O_EXCL -EEXIST; a new name is made;
- **hardlinks**: a non-owner who is not file-system user id 0 links a
  regular file without S_ISUID and without S_ISGID with group execute
  that it may read and write (02767 yes; 04777, 02777, 0644, 0600 and a
  0660 file of a group it is not in, -EPERM); a symbolic link of
  another's -EPERM; root anything; root after `setfsuid(1002)` like
  1002;
- **fifos**: nothing to act on (PAX makes no FIFO: `mknod` -EPERM by
  name).

## D. `chmod` and `utimensat` (item 4)

- `chmod`, `fchmodat`, `fchmod` (on any descriptor): the owner or
  file-system user id 0, else -EPERM (also on root's file, also of a
  directory); S_ISGID asked by an owner outside the group is dropped
  without an error (file 02644 → 0644, directory 02755 → 0755), kept by
  one in it by a supplementary group; S_ISUID and the sticky bit kept;
  root after `setfsuid(1002)` -EPERM on 1000's file, 0 on 1002's;
  `perm` D 6 of 6;
- `utimensat`: the owner or file-system user id 0 any times; anyone else
  NULL or {NOW, NOW} when the class gives write — of the file, not the
  descriptor (`futimens` NULL on a read-only descriptor of a 0666 file
  0, of a 0644 one -EACCES) — else -EACCES; {1, 2}, {OMIT, NOW},
  {NOW, 5}: -EPERM; {OMIT, OMIT} 0; a symbolic link's own times
  (AT_SYMLINK_NOFOLLOW): NULL for anyone (a link is 0777), {1, 2} its
  owner's; `perm` F 8 of 8.

## E. Set-ID bits (item 5)

`chk` B and R, `setid`'s 50 `bits:` lines: a write of a byte or more
(`write`, `writev`, `pwrite`, append, `copy_file_range`, `sendfile`,
`splice`), O_TRUNC (of an empty file too), `ftruncate` (to any length),
`truncate` (to its own size too) and `fallocate` by one whose
file-system user id is not 0 take S_ISUID, and S_ISGID when the file is
group-executable or the writer is not in its group (02767 kept by a
member, 0767 for another); root keeps both. The writer's ids decide: a
descriptor root opened before the drop writes as the user (0777). A
write of no bytes, an O_RDWR open, `utimensat`, `rename`, a hard link
and `chmod` to the same mode keep the bits; `fallocate` of no bytes is
-EINVAL and keeps them. **`fallocate` (285) is new**, mode 0 only: the
file grows by a hole (no space set aside: named drift); -EBADF on a
read-only descriptor; other modes refused by name (-EOPNOTSUPP).

## F. AF_UNIX `connect` (item 6)

Write on the socket's name by the class rule, before whether anything
listens: root's 0775 and 0000 listeners -EACCES to a user, 0777 and
0772 0; a closed 0000 name -EACCES, a closed 0777 one -ECONNREFUSED; a
0000 regular file -EACCES, a 0666 one -ECONNREFUSED; a socket in root's
0700 directory -EACCES (the walk); root connects to all but the closed
and the files. `perm` I: 36 of 36.

## G. The probes against Linux; every existing suite (item 7)

Every Linux line is real root's: kasumi's own kernel image (Linux
7.2.8-1-cachyos, `f4c00d5d…`) under QEMU 11.1.1, the program a child
of pid 1, every capability, **the four protected settings written to 1
first** (`notes/px44/vminit.c`; `vm-chk.meta`: archive `d362a6a3…`, `chk`
`eef4c2df…`). `perm` and `setid` are px38's vm-protected recordings,
their sections to the byte (`tests/mpx5-users` U0 checks it; `perm` and
`setid` are the very binaries px38 recorded, digests `e75fe694…` and
`cfd6e650…`). A user's rows are an actor that dropped for good or the
whole program after `as 1000 1000`. No row is compared with a
container's root.

| session | run by | Linux lines | identical on PAX before (trunk `e4755fd`) | after | the rest |
|---|---|---:|---:|---:|---|
| perm | root, dropping to own, grp, sup, oth | 382 | 291 (vm-protected; 295 against vm) | **337** | 43 A rows Linux's but for `execve 0` → -13 (px27; 30 a user's); own's and oth's held rows (job control) |
| perm B / C / D / F / I `connect` | the actors | 105 / 12 / 6 / 8 / 36 | 91 / 6 / 2 / 4 / 19 | **105 / 12 / 6 / 8 / 36** | |
| setid `bits:` | its owner, another user, root | 50 | (not run) | **50** | its other 20 PAX lines held: `execve` refused (px27), not honoured (R5) |
| chk | root, dropping to the actors and two id states | 339 | 285 | **339** | |
| chk-user | 1000:1000 | 65 | 54 | **65** | |
| chk-soak, chk-soak-user | root; 1000:1000 | 2, 2 | | 1, 1 | `~soak` (free memory, PAX's one number) |
| own, own-user | root; 1000:1000 | 278, 9 | 277, 9 | 277, 9 | `~fixed` |

`chk`'s new rows as users: 65 actor rows of the 75 (own, grp, sup, oth
dropped for good; the R rows' two id states and the supplementary-group
owner) and all 19 of `chk-user`'s. `chk-user` cannot show
protected_symlinks refusing (a user alone can make only its own link);
the actors show it, in `chk` and in `perm` C.

**Existing suites as root.** `git diff e4755fd --stat -- tests/` is
`tests/mpx5-users` and `tests/mpx5-users.d/` only. On kasumi:
`tests/mpx5-users`, four legs, 76 boots (19 sessions a leg), **329
PASS, 0 FAIL, 0 SKIP** (`notes/px44/kasumi-mpx5-users-8f01cc9.out`);
the same images under `taskset -c 0-3`, 329 PASS, 0 FAIL;
`tests/mpx3-tree`, four legs, 134 PASS, 0 FAIL, 0 SKIP (px43's 134),
and under `taskset -c 0-3`, 133 (the build's T0 not repeated); hasu,
KVM, BIOS, both tiers, two rounds of 38 boots, 165 PASS each, 0 FAIL
(`notes/px44/hasu-kvm-8f01cc9.log`). In CI:
the `tier pr` run (the 19 `@user` suites on native BIOS) and the
labelled `tier full` run at the head, named in the PR.

## H. Soak and plants (item 7)

- **The soak**: `chk soak 100000`, as root and as 1000:1000, every leg:
  px43's ten calls a round and ten more — `mkdir` in a 0555 directory,
  `rename` from a 0777 one into it, `rename` of another's name in a
  sticky directory, a hard link to root's 0600 file, O_CREAT of root's
  file in a sticky world-writable directory, `chmod` and `utimensat
  {1, 2}` of root's file, `chmod 06777` of a set-ID file, a `pwrite` to
  it and its mode read back: **2,000,000 calls and 200 execs, 0 wrong
  answers**, `MemFree` one number at the start and every quarter on
  every leg (249,276 kB native BIOS).
- **The plants** (cut from `ff5f51e`, never to be merged):

  | plant | break | red on kasumi | red in CI |
  |---|---|---|---|
  | A, branch `px44-plant-a` `c4d28ad` | `sticky_ok` always yes | `notes/px44/kasumi-plant-a.mpx5-users.out`: U1 `perm` at its line 216, `sticky 1777 dir of 1000 grp` (unlink 1000's file 0 where Linux says -1) | run 38659145396, job 116179065212 (`mpx5-users` the only suite): `notes/px44/ci-38659145396-plant-a-mpx5-users.txt` |
  | B, branch `px44-plant-b` `438ca10` | `renameat` asks write of the old name's directory only | `notes/px44/kasumi-plant-b.mpx5-users.out`: `perm` passes; U1 `chk` at its line 267, own's `names … made` row (`into it 0` for -13) | run 38659148372, job 116178797870: `notes/px44/ci-38659148372-plant-b-mpx5-users.txt` |

## I. `perm`'s remaining lines, and what they need

- **The loader (px27)**: A's 43 `execve 0` rows (13 root's, 30 a
  user's): PAX runs only an archive file whole; `chk` X shows the class
  rule on archive files, 105 of 105 (px43). `setid`'s 14 refused
  `execve`s, the same.
- **Job control**: own's and oth's held rows: the holder stops itself
  with SIGSTOP, which PAX drops, so it asks while the file is still
  1000's at 0666 (own: new open 0, fchmod 0; oth: new open 0, fchmod
  -1). `chk` H holds the rule with a pipe; `fchmod` by a non-owner on a
  held descriptor is -EPERM on PAX now (oth's line).
- **U5**: none of `perm`'s lines; `/dev` and `/proc` names' answers to
  making and removing (-EROFS, -ENOENT) and their files' checks.

## What U5 (processes and root's things) should know

- The class rule is `kernel/files`' `may`; ownership is `owns`; root
  for files is file-system user id 0 everywhere (R9). Signals ask the
  effective id (px38 §(d)), not these.
- `/dev` keeps fixed modes and is not checked on `open` or `access`, and
  making or removing a name there is -EROFS by name before any
  permission; `/proc` the same with -ENOENT; U5's `/dev` modes will
  meet `may` at `openat`'s `named` test (`ty(n) == T_INO` today).
- `chk` (`user/elf/chk.c`) is the probe to extend; its recorder is
  `notes/px44/linux-vm.sh` (vm-protected). The suite's session
  extraction now matches a kernel line as `user: <name> pid <n> `, so a
  probe may print `user: ` itself (setid does).
- `perm`'s held rows wait for job control, not for U5.

## 4. Evidence index

Shas are this branch's (`px44`). kasumi paths are under
`~/lanes/px44/`; hasu's likewise.

### What was written

- The prediction: `7a53caa`.
- The programs: `be58c2e` (setid, `tools/mkcred`), `2d9844a` and
  `c7e5c4a` (`user/elf/chk.c`).
- The recorder: `76165f3` (`notes/px44/vminit.c`, `linux-vm.sh`,
  `build.sh`).
- The kernel: `378f22c` (`kernel/procfs`), `a270cef` (`kernel/files`),
  `1be1453` (`kernel/user`: `fallocate`), `348c17a`, `e52031f`
  (comments).
- The suite: `47ae40e`, `3f0c8b9` (chk recorded on vm-protected),
  `cc182ac` (perm and setid against vm-protected), `5ca1fb4`, `eb14dfe`
  (`tests/mpx5-users`).
- The words: `ce88d07` (`kernel/README.md`), `efadd0d`
  (`docs/SOURCES.md`), `ff5f51e` (CHANGELOG).

### What was measured, and where it is

- **Linux, vm-protected**: `tests/mpx5-users.d/linux/chk*.txt`,
  `vm-chk.meta`; `perm.txt`, `setid.txt` (px38's
  `notes/px38/linux/vm-protected.txt`, `vm-protected.meta`).
- **The kernel's cost**: `notes/px44/kasumi-kernel-cost.txt`.
- **PAX**: `notes/px44/kasumi-mpx5-users-8f01cc9.out` (four legs),
  `kasumi-taskset-0-3-mpx5-users-8f01cc9.out`,
  `kasumi-mpx3-tree-8f01cc9.out`,
  `kasumi-taskset-0-3-mpx3-tree-8f01cc9.out`, `hasu-kvm-8f01cc9.log`
  (all at `8f01cc9`; what follows it is notes and one message string of
  the suite).
- **The plants**: §H.
- **CI**: named in the PR (a commit naming the head's runs would move
  the head).

### Measured, inferred, not verified

**Measured**: everything in §A to §I.

**Inferred**: that `renameat`'s order between two refusals of its two
directories (the old one sticky, the new one unwritable) is Linux's
(not asked: PAX asks write of both, then the sticky rule); that a
`fallocate` by a user that changes nothing but the bits clears them
like a write (asked only with a growing length); that `ctime` moves when
a write takes the bits (`set_mode` moves it; not measured).

**Not verified**:

- Real root was one kernel build (kasumi's CachyOS 7.2.8).
- `mknod` of a FIFO (refused by name on PAX for everyone), so nothing
  of protected_fifos.
- More than one process naming in one directory at once (PAX runs one
  CPU; a call runs with interrupts off).
- UEFI under KVM on hasu (pax#56): BIOS only there.
- `mpx3-tree` as a user (U7's, as px43 said).

### Issues

- **To close at merge**: none.
- **Would file (none filed)**:
  1. pax: `fallocate` modes other than 0 (KEEP_SIZE, PUNCH_HOLE) are
     refused by name; tmpfs takes them.
  2. pax: `perm`'s held rows need a holder that can stop itself (as
     px43 listed).
- pax#58 and pax#60 not reached (AF_INET/eventfd owners;
  `faccessat2`'s flags).
- Not chased, did not occur in this lane's runs: pax#45, #47, #53.

## 5. Done-when

- Branch `px44` on origin; pax PR #61, open, unmerged.
- The five sections §1 to §5; the items §A to §I.
- The test checklist:
  - [x] `tests/mpx5-users`, native and release, BIOS and UEFI, kasumi (TCG)
  - [x] the same under `taskset -c 0-3`
  - [x] the same images under KVM on hasu (BIOS)
  - [x] `tests/mpx3-tree`, four legs, kasumi, and under `taskset -c 0-3`
  - [x] `tools/ci-plan` on the branch's paths (19 `@user` suites, pr tier; no map line needed)
  - [x] plant A red on kasumi and in CI; plant B the same
  - [ ] the pr tier at the final head, and all suites on every leg (`tier full`): named in the PR
- `wolf/tools/lane-audit.sh pax px44 61` exit 0: named in the PR.
- Trees: kasumi `~/lanes/px44/` keeps `out/`, `bin/`, `keep/`; build
  directories removed. hasu `~/lanes/px44/` keeps `out/`. Plant
  branches stay on origin, never to be merged.
