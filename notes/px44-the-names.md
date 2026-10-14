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
