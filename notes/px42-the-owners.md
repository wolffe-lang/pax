# px42 — The owners (P5 lane U2: a file has an owner)

Contract: px42's, `sprints/pax/42-the-owners/` in wolffe-lang/wolf
(planning commit `e8fed02`, read 2026-10-13), under
`sprints/pax/p5-the-users-campaign.md` (ruling #75, R1 to R9) and the
rules of `sprints/wave-53.md` down to `wave-45.md`. Branch `px42` in
pax, cut from pax trunk `d3f4aa9`. §1 to §3 are committed before the
first change to the kernel, a tool or a test.

One deliverable: an inode has an owner and a group. A new file,
directory, symbolic link or socket name is stamped with its maker's
**file-system** ids (and its directory's group under a set-group-ID
directory); `chown`, `fchown`, `lchown` and `fchownat` keep any id for
root and follow Linux's rule for a user; `stat`, `statx` and `/proc`
report owners; an image carries them (pax#48).

**What this lane does not do.** No permission check on `open`,
`execve`, a path walk, a signal, a port or a device changes: a process
that is 1000 still opens, removes and signals what root does. That is
U3 to U5. The one rule implemented is `chown`'s own (who may change an
owner or a group, the `-1` fields, the set-ID bits it clears), because
a process that is not root can now call it. The ruled claim for the
campaign is "enforced for honest programs; not a boundary against an
attacker" (R6), and this lane enforces nothing but that one rule.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read, nor that of
  `su`, `login`, shadow-utils, util-linux or coreutils (ruling #22).
  Facts come from the man pages (`chown(2)`, `fchownat(2)`, `stat(2)`,
  `statx(2)`, `inode(7)`, `mkdir(2)`, `open(2)`, `symlink(2)`,
  `link(2)`, `bind(2)`, `unix(7)`, `credentials(7)`,
  `capabilities(7)`, `proc(5)`, `cpio(5)`), POSIX.1-2024, the uapi
  headers the refs clone's sparse checkout holds, the initramfs buffer
  format (`Documentation/driver-api/early-userspace/`), pax's own
  source, px38's and px39's recorded Linux answers, and black-box runs
  made the way px38 made them.
- No syscall number is added that is not in a trace or a probe. None is
  expected: 92, 93, 94 and 260 are answered since px36.
- No permission check is added or changed but `chown`'s own. Set-ID
  execution is not honoured (R5).
- No account is made on any host; no `sudo`. A Linux answer for
  **root** comes from kasumi's own kernel image booted under QEMU with
  a static program as pid 1 (**vm**); a rootless container's root
  (**ct**) is a reference for users' rules only. Each compared row
  names its reference. A test becomes a user with `user/elf/as.c`.
- Probe and test binaries are static and built in the Ubuntu 24.04
  container on kasumi (`px13-ubuntu`, glibc 2.39), never with kasumi's
  own glibc.
- No word implying filming. Nothing calls PAX secure.
- No build on nomad-1. kasumi and hasu: commands under `bash`, long
  jobs under `setsid` with a pid file and ended by that pid only; work
  under `~/lanes/px42/`, pruned as I go; never `/tmp`. Host ports 8080
  and 8088 are not used. Nothing is installed anywhere.
- No `rm` outside `~/lanes/px42/`; no `git add -A`; nothing under
  `~/.claude`; no merge, no tag; no issue filed or closed (listed); no
  `2>/dev/null` on a checkout; no trailer on a commit or the PR.
- px41 is in flight in the test harness and possibly `kernel/files`'
  open-files census: its files are not touched, `kernel/files` changes
  only where an owner is stamped, changed or reported, and no run of
  another lane is cancelled.
- "Seen red" cites a run. If the harness refuses an action I stop and
  report.

## 2. Inputs, verified (2026-10-13)

| input | found |
|---|---|
| pax trunk | `d3f4aa9` (px39 merged), the contract's |
| planning repo | `e8fed02`: the contract, the campaign file with R1 to R9 |
| the kernel's pin | wolf 0.2.28 / lupin 0.1.51 (`kernel/wolf.pin`), unchanged |
| the inode | `kernel/tree`: `IWORDS` 16, 32 inodes a frame, at most 16,384 (`MAX_INODES`); the words are mode, links, size, holders, three times, root, depth, blocks, back, backlen, parent, entries, btime, next. **All sixteen have a name, as the contract says, but one is not used by a live inode**: word 15, `I_NEXT`, is written by `inode_free` and read by `inode_new` only, for a record whose mode is 0 |
| what stamps | `tree.create` (from `files.open` with O_CREAT), `tree.mkdir`, `tree.symlink`, `tree.mksock` (AF_UNIX `bind`), `tree.adopt` (the archive); `tree.link` makes no inode. `O_TMPFILE` is refused by name (-EOPNOTSUPP, px27): there is no such file to stamp |
| the `chown` family | `files.fchownat` serves 92, 93, 94 and 260: an id that is neither 0 nor -1 is refused by name, -EINVAL (`R_OWNER`, code 23); `tree.owned` clears S_ISUID, and S_ISGID when group-executable, on a regular file, and moves ctime |
| `stat`, `statx` | `files.put_stat` and `put_statx` write no uid or gid (the zeroed buffer answers 0:0 for every node) |
| `getdents64` | `struct linux_dirent64` has no owner field (`getdents(2)`): a listing learns an owner from `stat` or `statx` of each name. **The contract's "`getdents64` reports owners" is read as that**: `ls -ln` of a directory shows each name's owner |
| `/proc` | `kernel/procfs`: `mode` and `size` a reference; no owner; `/proc/<pid>` holds `status` and `setgroups` |
| images | `tools/mkinitramfs` writes uid and gid 0 and takes no directory of its own (only a file's parents, 0755); `kernel/initramfs` names fields 0, 1, 4, 5, 6 and 11 and reads neither uid (2) nor gid (3); `tree.adopt` reads mode, mtime, size (pax#48, open) |
| px39's note | "what U2 should know": stamp with `cred.uid(a, cred.FS)` and `cred.gid(a, cred.FS)`; `cred.in_list` is private; file privilege is file-system uid 0; `IDS_LINUX_LINES` 59; `ident`'s `~owner` |
| px38's recordings | `notes/px38/linux/vm.txt`: `perm` is 382 lines (sections A 105 rows, B 105, C 12, D 6, E 71, F 8, G 11, H 13, I 42, with nine headers, a settings line and `perm: done`); 81 of them are a root actor's. `perm` has never run on PAX (px38 booted `ids` and `priv` only) |
| `tests/mpx3-tree` | T2 holds ten `refused:` lines (`NREF`), one of them syscall 92's `R_OWNER`, and `~owner: chown 1000 1000 -22: uid 0`; its Linux side is a live container (`tools/linux-tree`) |
| `tests/mpx5-users` | `ids` 59 of 71 lines Linux's, the `chown: to 1000:1000 -22, then owned 0:0` line and the `R_OWNER` refusal in `ids.pax` and `IDS_REFUSED`; `ident`'s `~owner: /proc/self/setgroups is owned 0:0` in both `ident` sessions |
| `tools/ci-tiers.map` | `kernel/tree`, `kernel/files`, `kernel/procfs`, `kernel/initramfs` and `tools/mkinitramfs` are read when the work touches them (§4) |
| kasumi | Linux 7.2.8-1-cachyos, QEMU 11.1.1 (TCG), `px13-ubuntu` `ad896450…`, `/home` 32 GB free, load 25 on 16 cpus (other lanes) |

**Drift from the contract, found before any change.**

1. "An inode's 16 words are all taken" is true of names and false of
   use: the free list's link lives in a record that is free. So the
   owner needs no seventeenth word (P1). The contract asks for the
   growth measured; the measurement I expect to report is that there
   is none.
2. `getdents64` cannot report an owner (above).
3. "Root rows of `perm` match": `perm` has not run on PAX at all, so
   the number of its lines PAX gets is not known. I expect one root
   row not to match, by rule: `root after setfsuid(1002)` is told
   -EACCES for root's 0600 file on Linux, which is a permission check
   on `open` (U3).

## 3. Prediction (committed before the first change)

**P1. The inode does not grow.** The owner and the group are one word
(the user id in the low 32 bits, the group id in the high 32), word
15; the free list's link moves into a word a free record does not
otherwise need. `IWORDS` stays 16: 128 bytes an inode, 32 a frame,
`MAX_INODES` 16,384, the tree's cap (half of the frames free when it
is made) the same number on every image; every suite's `tree: frames`
and `user: frames free` lines are the same numbers as at `d3f4aa9`.
Falsified if `IWORDS` or any constant of the table must change, or by
a census line that moves.

**P2. The stamps.** A file, a directory, a symbolic link and a
socket's name are their maker's file-system user id and file-system
group id; in a set-group-ID directory the group is the directory's, a
new directory there takes the bit, and a file made there with S_ISGID
by one who is not in that group (file-system group id or supplementary
list) loses the bit. A hard link changes no owner. All 13 lines of
`perm`'s section H are Linux's on PAX, for every actor (nothing
refuses the making). Not in px38's recording, measured on vm first,
with what I expect:
- a symbolic link and a socket's name made in a set-group-ID directory
  take the directory's group;
- a directory made with S_ISGID in its mode, in a plain directory, by
  one not in the group it gets, keeps the bit;
- a hard link, a `rename` and a write change no owner.

**P3. The `chown` family.** `kernel/files`' `R_OWNER` goes. The rule,
for the four calls alike: privileged is file-system user id 0 and may
set anything; anyone else must have the file's owner as file-system
user id, may name as owner only that id or -1, and as group only -1,
the group the file has, the file-system group id or one of the
supplementary groups; otherwise -EPERM, also for `(-1, -1)` by one who
is not the owner. An id is 32 bits. Every success, `(-1, -1)`
included, clears S_ISUID and (when group-executable) S_ISGID on a
regular file, leaves a directory's bits and the sticky bit, and moves
ctime. All 71 lines of `perm`'s section E are Linux's on PAX, the
users' rows too. Not recorded, measured on vm first: `fchown`,
`lchown` and `fchownat` by a user follow the same rule (`lchown`
changes the link, `chown` what it leads to); a refusal moves no ctime;
a missing name is -ENOENT before -EPERM; root with file-system user id
1002 is refused as 1002 would be, and (0, 1000, 0) after `setfsuid(0)`
is not.

**P4. What is reported.** `stat`, `fstat`, `lstat`, `newfstatat`:
`st_uid` and `st_gid` (bytes 28 and 32); `statx`: `stx_uid` and
`stx_gid` (bytes 20 and 24). `/proc/<pid>`, `/proc/self` and their
`status` are the process's effective user and group ids, whether or
not it is dumpable; `setgroups` I expect to be 0:0 once the process is
not dumpable (px38 saw `environ` so) and the effective ids while it
is. `/dev`, `/proc`'s fixed files and `/sys` stay 0:0. A pipe's and a
socket's `fstat` on Linux I expect to say the maker's file-system ids;
PAX will say 0:0 for them and the row is named (they are descriptors,
not names: U5 gives a socket its peer's ids).

**P5. Images.** `tools/mkinitramfs` writes an owner where one is
given and takes a directory entry of its own; with no owner given the
archive is the same bytes as before (every existing image's digest
unchanged). `tree.adopt` gives the inode the archive's owner. An image
with `/home/pax` 0755 1000:1000 and a file of his in it: boreutils'
`ls -ln /home /home/pax` on PAX is byte-identical to the same binary's
on a Linux that unpacked the same archive as its root (vm).

**P6. The counts.**
- `ids`: 60 of 71 lines Linux's (from 59): `chown: to 1000:1000 0,
  then owned 1000:1000`; `IDS_REFUSED` loses syscall 92.
- `ident`, `ident-user`: `~owner` loses its `~`: 223 of 225 and 127 of
  129 (from 222 and 126).
- `tests/mpx3-tree`: refusals 10 → 9; `~owner` retired, the line
  compared with Linux's (`owner: chown 1000 1000 0: uid 1000`).
- `perm` as the first program: 80 of the 81 root-actor rows Linux's
  (the one above by rule), all 71 of E and all 13 of H; of the 382
  lines I expect about 250 identical (the users' rows of A, B, C, D,
  F, G and I differ wherever Linux refuses: U3 and U4), each differing
  line held to PAX's own text in a file the test names.
Falsified by any other count.

**P7. Existing suites.** No file under `tests/` is edited but the rows
P6 names, the new sessions of `tests/mpx5-users`, and `tests/ci-plan`
if a place is added. `user/elf/tree.c` changes in one line (`~owner`).
Every existing suite passes with its numbers as they were.

**P8. The soak.** 100,000 rounds of making, `chown`ing and removing,
as root and as a user: the frames-free count ends where it started,
and free memory read at each quarter is one number.

**P9. Plants.** A: stamped with the effective ids instead of the
file-system ids: red at `perm`'s `after setfsuid(1002) … 1002:2002`
row (section H's last) and nowhere before it. B: `chown`'s rule for a
user removed: red at the first of section E's -EPERM rows, `chown own
… chown(-1, 2001) = -1`. Each red in CI, one suite.
