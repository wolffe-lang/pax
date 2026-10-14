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

### Corrections to §2 and §3, found after they were committed

- §2 counted `perm`'s root-actor rows as 81 and §3 P6 expected 80 of
  them to be Linux's. `perm` copies itself onto the tmpfs and runs the
  copy in every row of section A; PAX runs no program written since
  boot (px27's named limit, -EACCES, `tests/mpx3-tree`'s `~exec`), so
  the 13 root rows whose mode has an execute bit differ in that one
  field. I had not read what `perm` executes.
- P7 named `user/elf/tree.c` as the one program edited. `user/elf/
  ident.c` is edited in one line too (its `~owner` loses the `~`, as
  the contract says), so px39's seven recordings were taken again
  (§D).

## 3a. The prediction, scored

| # | predicted | measured | verdict |
|---|---|---|---|
| P1 | the owner and group are one word; `IWORDS` stays 16; 128 bytes an inode, 32 a frame, 16,384 at most; every suite's `tree: frames` and `user: frames free` lines the same numbers as at `d3f4aa9` | the first three exactly (§A). The same three images booted on trunk's kernel and on this one (`notes/px42/kasumi-inode-cost.txt`): the tree holds the same frames, the same inode-table frames and the same inodes (306 inodes: 10 frames of table, 18 held, on both). **`frames free` is 2 lower and the tree's cap 1 lower on every image**: the kernel's text grew by 3,728 bytes (845,051 to 848,779), which is two more frames of image, and the cap is half of what is free | right on the inode; wrong that no number moves |
| P2 | the file-system ids; a set-group-ID directory's group for a file, a directory, a link and a socket; a new directory there takes the bit; S_ISGID on a new file dropped for one outside the group; a hard link, a rename and a write change no owner; **a directory made with S_ISGID in a plain directory keeps the bit** | all but the last (§B). **Linux drops S_ISGID from `mkdir`'s mode for everyone, root included**: a directory has the bit exactly when its parent has. Not predicted: `mkdir` keeps a sticky bit (PAX dropped it: fixed here); S_ISGID on a new file goes only when the file is group-executable (`02666` by one outside the group stays `2644`) | right on the owner; wrong on one mode bit |
| P3 | privileged is file-system uid 0; the owner may name his own id and a group he is in or the file's; `(-1, -1)` by one who is not the owner -EPERM; every success clears S_ISUID and, when group-executable, S_ISGID; 32 bits; the four calls alike; a refusal moves no ctime; -ENOENT before -EPERM | the first, second, and the last five as predicted, and all 71 lines of `perm` E at the first boot. **Two things were wrong.** `chown(-1, -1)` by one who is not the owner is 0, and moves ctime, whenever there is no set-ID bit to take: px38's rows were -EPERM because its file was mode 6755. And S_ISGID *without* group execute also goes when the caller is not privileged and not in the group the file **had** (an owner outside the group turns 2644 into 0644 with `chown(-1, -1)`); one who is not the owner may make no call that would take a bit (§C) | half right |
| P4 | `st_uid`, `st_gid` at 28, 32; `stx_uid`, `stx_gid` at 20, 24; `/proc/<pid>` and its `status` the effective ids, dumpable or not; `setgroups` 0:0 once not dumpable; a pipe's and a socket's `fstat` the maker's file-system ids on Linux, 0:0 on PAX | the offsets, the directory and the descriptors as predicted. **`status` is root's too once the process is not dumpable** (both files follow one rule, the directory another) | right but for `status` |
| P5 | an archive with no owner given is the bytes it was; `ls -ln` of the image byte-identical to the same binary on a Linux that unpacked the same archive | both: trunk's and this lane's `tools/mkinitramfs` write one digest for px39's arguments (`notes/px42/mkinitramfs-same.txt`); `ls -ln` 18 of 18 lines, `ls -l` 18 of 18 | right |
| P6 | `ids` 60 of 71; `ident` 223 of 225 and 127 of 129; `mpx3-tree` refusals 10 → 9; `perm`: 80 of 81 root rows, 71 of E, 13 of H, about 250 of 382 | 60; 223 and 127; 9; E 71 of 71, H 13 of 13; **67 of 81 root rows** (13 by the loader's limit, 1 a check on `open`); **173 of 382** | right on six counts, wrong on two |
| P7 | no file under `tests/` edited but the rows P6 names and the new sessions; every existing suite passes with its numbers as they were | `git diff d3f4aa9 --stat -- tests/` is `tests/mpx3-tree` (15 lines: the tenth refusal and the `~owner` line) and `tests/mpx5-users` with its directory; every other suite ran unedited (§F) | right, but for the two numbers of P1 |
| P8 | the soak leaves the frames where they were | 1,200,000 calls that make, `chown` and remove, as root and as 1000:1000: 0 wrong answers, free memory one number at every quarter, the frames line the same before and after, every leg | right |
| P9 | A red at `perm`'s `after setfsuid(1002)` row; B red at `perm` E's first -EPERM row | both red at the same fact one session earlier: `own` runs first and holds both (A: its `made by uid 1001 1001 1002 1002` row, one line; B: `fchown own … (-1, 2001)`, from line 30 on) | right on what, wrong on where |

## A. How the owner fits the inode, and what it costs (item 1)

An inode was 16 words and stays 16 words. Its words before: mode,
links, size, holders, atime, mtime, ctime, root, depth, blocks, back,
backlen, parent, entries, btime, **next**. `next` is the free list's
link: `inode_free` wrote it and `inode_new` read it, both only for a
record whose mode is 0. A live inode never used the word. So:

- word 15 is now the owner: the user id in its low 32 bits, the group
  id in its high 32 (`I_OWNER`; `tree.uid`, `tree.gid`);
- a free record's link is in word 14, where a live inode keeps its
  birth time (`I_NEXT` = `I_BTIME`): `inode_new` reads the link, then
  zeroes all sixteen words, then stamps the times and the owner.

| | before (`d3f4aa9`) | after |
|---|---|---|
| an inode | 16 words, 128 bytes | 16 words, 128 bytes |
| inodes a frame | 32 | 32 |
| the most inodes | 16,384 (512 frames of table) | 16,384 |
| the tree's cap | half of the frames free when it is made | the same rule; the number is 1 lower on a 256 MiB machine (31,064 from 31,065) because the kernel's image is 2 frames longer |
| 306 inodes (`notes/px42/kasumi-inode-cost.txt`) | 18 frames held, 10 of them the table's | 18, 10 |
| 11 inodes (px39's `cred` and `ids` images) | 6 frames held, 1 the table's | 6, 1 |
| kernel text / data / bss | 845,051 / 76,536 / 4,395,104 | 848,779 / 76,520 / 4,395,104 |

The frame census of every suite is flat in the sense each suite
asserts it (as many frames free after init's end as before the first
program, but for the inode table's own growth): §F.

## B. The stamps (item 2)

`files.stamp` reads the maker's **file-system** user and group ids
(`cred.uid(a, cred.FS)`, `cred.gid(a, cred.FS)`) and the directory;
`tree.create`, `mkdir`, `symlink` and `mksock` are told the ids.

| what is made | owner | group | mode | reference |
|---|---|---|---|---|
| a file (`open` with O_CREAT) | file-system uid | file-system gid; the directory's under a set-group-ID directory | `mode & ~umask & 07777`, without S_ISGID when the result is group-executable and the maker is neither file-system uid 0 nor in the group it is given | vm: `perm` H (13 lines, px38's recording), `own` S |
| a directory | the same | the same | `mode & (0777 & ~umask \| 01000)`; S_ISGID exactly when the parent has it, whatever was asked | vm: `perm` H, `own` S |
| a symbolic link | the same | the same | 0777 | vm: `perm` H (plain directory), `own` S (set-group-ID directory) |
| a socket's name (`bind`) | the same | the same | `0777 & ~umask` | vm: `perm` I's first line (root), `own` S |
| a hard link, a `rename`, a write by another | unchanged | unchanged | unchanged | vm: `own`'s `kept` rows |
| an archive's entry (`tree.adopt`) | the header's uid | the header's gid | the header's | vm: `ls`, the same archive unpacked by Linux |
| `O_TMPFILE` | — | — | — | refused by name on PAX (-EOPNOTSUPP, px27): there is no such file |

**The set-group-ID directory rule, as measured** (a 2777 directory of
0:2000, umask 022; `own` S, vm):

| maker | a file | a directory | a link | a socket | a file asked 06777 | asked 02666 | a directory asked 02777 / 01777 |
|---|---|---|---|---|---|---|---|
| 1000:2999, not in 2000 | 1000:2000 0644 | 1000:2000 **2**755 | 1000:2000 | 1000:2000 0755 | **4**755 | **2**644 | 2755 / 3755 |
| 1000:2999 with groups {2000, 2001} | the same | the same | the same | the same | **6**755 | 2644 | the same |
| 1001:2000 | 1001:2000 | 1001:2000 2755 | 1001:2000 | 1001:2000 | 6755 | 2644 | the same |
| root | 0:2000 | 0:2000 2755 | 0:2000 | 0:2000 | 6755 | 2644 | the same |

In a plain 0777 directory the group is the maker's file-system group,
`06777` is `6755` for everyone, a directory asked `02777` is `0755` for
everyone and asked `01777` is `1755`. With the file-system ids moved
apart from the effective ones ((1001 1001 1002) and file-system 1002;
groups the same way) a directory, a link and a socket are 1002:2002.
All 24 lines of `own` S and all 13 of `perm` H are byte-identical on
PAX.

## C. The `chown` family (item 3)

One function, `files.fchownat`, serves `chown` (92), `fchown` (93),
`lchown` (94) and `fchownat` (260). `R_OWNER` and its -EINVAL are gone.

**The rule** (every row vm, real root's boot; the users are children
that dropped for good):

1. An id is the low 32 bits of its register; -1 leaves it alone
   (`width`: `0x1000003e9` is 1001; `0x1ffffffff` is -1; 4294967294 is
   kept as an owner).
2. **Privileged is file-system user id 0**, and may set anything.
   The effective id is not asked: root after `setfsuid(1002)` is
   refused what 1002 would be; (0 1002 0) after `setfsuid(0)` is not
   (`fsid` rows).
3. Anyone else naming an **owner** must be the file's owner (by
   file-system uid) and name that same id.
4. Anyone else naming a **group** must be the file's owner and name
   the group the file has, his file-system group id, or one of his
   supplementary groups. The real and effective group ids are not
   asked (`fsid`: real 2001 refused, then allowed after
   `setfsgid(2001)`, and effective 2999 then refused).
5. On a regular file a success takes S_ISUID, and takes S_ISGID when
   the file is group-executable **or** the caller is not privileged
   and not in the group the file had before the call. A directory's
   bits and the sticky bit stay.
6. One who is not the owner may make no call that would take a bit.
7. So `chown(-1, -1)` by anybody is 0 on a file with no bit to lose,
   and **every success moves ctime**, that one included; a refusal
   changes nothing.
8. `lchown` and `fchownat(AT_SYMLINK_NOFOLLOW)` change the link, and
   `chown` what it leads to; a link has no bit to lose, so `lchown(-1,
   -1)` of anyone's link is 0.
9. A missing name is -ENOENT, a name under a file -ENOTDIR, a bad
   pointer -EFAULT, a long name -ENAMETOOLONG, a closed descriptor
   -EBADF, a flag that is not one -EINVAL: each before the question of
   who asks.

| rows | what | lines | reference | identical on PAX |
|---|---|---:|---|---:|
| `perm` E | `chown` by five actors, ten targets; an owner with two groups; seven modes by owner and by root; a directory | 71 | vm, px38's recording | 71 |
| `own` C, the family | `fchown`, `lchown`, `fchownat(0)`, `(AT_SYMLINK_NOFOLLOW)`, `(AT_EMPTY_PATH)` × five actors × seven targets | 175 | vm, this lane | 175 |
| `own` C, a link's own owner | `lchown`, `fchownat(NOFOLLOW)` and `chown` through a link × five actors × six targets | 30 | vm, this lane | 30 |
| `own` C, what else | ctime (4), errors (3), a directory and a socket's name (4), nothing asked and what it has and a 2644 file (15), width (1), the file-system ids (4) | 31 | vm, this lane | 31 |
| `own-user` | 1000:1000 on its own file, link and directory, and on root's `/` and program | 9, one `~` | vm after `as 1000 1000` | 8 |
| `ids` | `chown: to 1000:1000 0, then owned 1000:1000` | 1 | vm, px38's and px39's | 1 |
| `tests/mpx3-tree` | `owner: chown 1000 1000 0: uid 1000` | 1 | a container's root, live at every run (CI: the runner's real root; kasumi: ct, where 1000 is a mapped id) | 1 |

**What the man page does not say, and Linux does** (measured, not
explained): rule 7's first half (`chown(2)` says only an owner or a
privileged process may change a group); rule 5's second condition; and
that the ctime of anybody's plain file can be moved by anybody.

**What PAX refuses that Linux allows** (`~fixed`): a `chown` of
`/dev/null` and of `/proc/self/status` is -EROFS, by name (px36's
`R_FIXED`); `O_TMPFILE` is -EOPNOTSUPP.

## D. What is reported; images (items 4 and 5)

- `stat`, `fstat`, `lstat`, `newfstatat` write `st_uid` and `st_gid`;
  `statx` writes `stx_uid` and `stx_gid` (its mask already said so).
  `own`'s `report` rows: five calls, one answer, a link's own owner
  from `lstat`.
- **`getdents64` has no owner to report** (`struct linux_dirent64`
  holds an inode number, an offset, a length, a type and a name). A
  listing learns each name's owner from `statx`, which is what `ls`
  does: the `ls` sessions are that path.
- `/proc` (`procfs.owner`; `own`'s seven `proc` rows, vm):

  | node | owner |
  |---|---|
  | `/proc/<pid>`, `/proc/self` | the process's effective user and group, dumpable or not |
  | `/proc/<pid>/status`, `setgroups` | the same while the process is dumpable; 0:0 once it is not (after any change of id, until an `execve` with ids equal) |
  | everything else in `/proc`, `/sys`, `/dev` | 0:0 |

  `ident`'s line `owner: /proc/self/setgroups is owned 0:0` (root) and
  `1000:1000` (after `as 1000 1000`, which execs) is compared now.
- **Not reported** (`~desc`): a pipe, a socketpair and a socket made by
  1000:2999 are 1000:2999 to `fstat` on Linux and 0:0 on PAX. They are
  descriptors, not names, and no test reads the field (it said 0:0
  before this lane too).

**Images.** `tools/mkinitramfs` takes `/PATH=FILE:MODE:UID:GID` and a
directory of its own, `/PATH/:MODE:UID:GID`; `kernel/initramfs` reads
the header's uid and gid; `tree.adopt` gives them to the inode (a
directory made only because a path passes through it is root's, 0755).
The owners image of `tests/mpx5-users` holds R3's two accounts as lines
of `/etc/passwd` and `/etc/group` (text for `ls -l`; nobody logs in),
`/home/pax` 0755 1000:1000 with a file of his, a file of root's, a file
of group 990 and a 0700 directory, and `/srv/lobo` 0750 990:990.

`/bin/ls -ln /home /home/pax /home/pax/notes /srv` (boreutils `2ab3651`,
pax's build), on PAX and on Linux 7.2.8 booted with **the same archive**
as its initramfs (a second archive after it holds only `/init`; the
root is Linux's `rootfs`, a tmpfs):

    /home:
    total 0
    drwxr-xr-x 3 1000 1000 120 Jan  1  1970 pax

    /home/pax:
    total 12
    -rw-r--r-- 1    0    0 18 Jan  1  1970 from-root
    -rw-r--r-- 1 1000 1000 15 Jan  1  1970 hello.txt
    drwx------ 2 1000 1000 60 Jan  1  1970 notes
    -rw-rw-r-- 1 1000  990 15 Jan  1  1970 shared

    /home/pax/notes:
    total 4
    -rw------- 1 1000 1000 35 Jan  1  1970 todo

    /srv:
    total 0
    drwxr-x--- 2 990 990 60 Jan  1  1970 lobo

18 of 18 lines byte-identical; `ls -l` (names from the image's own
`/etc/passwd` and `/etc/group`: `pax pax`, `root root`, `pax lobo`,
`lobo lobo`) 18 of 18.

## E. The probes' counts (item 6)

Every reference is the **vm** root (kasumi's kernel image `f4c00d5d…`,
Linux 7.2.8-1-cachyos, under QEMU 11.1.1, the program a child of pid 1,
`CapEff 000001ffffffffff`); `-user` rows are the same boot after `as
1000 1000`. No row is compared with a container's root but
`tests/mpx3-tree`'s, which is that suite's standing reference.

| session | first program on PAX | lines on Linux | identical on PAX | the rest |
|---|---|---:|---:|---|
| own | `/bin/own /t/ownw` | 278 | 275 | 3 `~` lines: `~desc` twice, `~fixed` |
| own-user | `/bin/as 1000 1000 /bin/own /t/ownu` | 9 | 8 | `~desc` |
| perm | `/bin/perm /t/perm` (px38's source, `e75fe694…`, the digest px38 recorded) | 382 | 173 | below |
| ids | `/bin/ids /px38w` | 71 | **60** (59 before) | 11 in `ids.pax`: five process-group calls and `capget` (-ENOSYS), SO_PEERCRED, four that are the machine's |
| ident, ident-user | px39's | 225, 129 | **223**, **127** (222, 126 before) | `~thread`, `~bound` |
| cred, cred-user | px39's | 2,684, 3,983 | 2,683, 3,983 | unchanged |
| own-soak, own-soak-user | `/bin/own soak 100000 /t/soak` | 2 | 1 | `~soak` (free memory) |
| ls, ls-names | `/bin/ls -ln …`, `/bin/ls -l …` | 18, 18 | 18, 18 | none |

**`perm` by class** (PAX has the stamps and `chown`'s rule and no
other check, so a user's rows differ wherever Linux refuses him):

| class | rows | identical | the rest |
|---|---:|---:|---|
| section E, `chown`, every actor | 71 | 71 | |
| section H, who owns what is made, every actor | 13 | 13 | |
| the root actor's rows, all sections | 81 | 67 | 13 are section A rows whose only difference is `execve 0` → `execve -13`: PAX runs no program written since boot (px27; `refused:` by name, 65 times in the session). 1 is `root after setfsuid(1002)`: Linux refuses root's 0600 file to file-system uid 1002, which is a check on `open` (U3) |
| every line | 382 | 173 | 209 held to `tests/mpx5-users.d/perm.pax` (PAX's whole text, 385 lines: three more are `! the holder did not stop`, a SIGSTOP PAX drops by name, no job control) |

`tests/mpx3-tree`: nine `refused:` lines where there were ten (syscall
92's is gone), `NREF` counted by the kernel as 9.

## F. Existing suites, the soak, the plants (item 6)

- **No permission check changed but `chown`'s.** `git diff d3f4aa9 --
  kernel/` touches `tree`, `files`, `procfs`, `initramfs`, `cred` (one
  word: `pub`), a comment in `user`, and `README.md`. `kernel/signal`, `kernel/sched`,
  `kernel/socket`, `kernel/console`, `kernel/process` and
  `kernel/speaker` have no diff; in `kernel/files` no `open`,
  `execve`, walk, `access`, `chmod`, `utimensat`, `unlink` or `rename`
  path changed. A process that is 1000 still opens, removes and
  renames what root does: `perm`'s users' rows show it line by line
  (209 of them differ from Linux, all of them a check that does not
  exist yet).
- **No test edited but the rows the contract names.** `git diff
  d3f4aa9 --stat -- tests/` is `tests/mpx3-tree` (the tenth refusal
  and the `~owner` line: 15 lines), `tests/mpx5-users` and its
  directory (the new sessions, `ids.pax`'s one line, px39's seven
  recordings taken again for `ident`'s one line). `user/elf/tree.c`
  changes its `~owner` line and a comment, `user/elf/ident.c` its
  `~owner` line. No expect file, key
  file or transcript of any other suite moves; `tools/mkinitramfs`
  writes px39's archives (and every other suite's, whose arguments
  name no owner) to the byte as before.
- **What an existing program can see move**: `st_uid`/`st_gid` of a
  file a process that is not root made (0 before); `/proc/<pid>`'s
  owner for a process that is not root; a new directory asked with the
  sticky bit keeps it; `chown` by root to any id is 0 where it was
  -EINVAL. No existing suite runs a process that is not root but
  `mpx5-users`, so their files are all 0:0 as before.
- **Ran**: `tests/mpx5-users` on kasumi, four legs (native and
  release, BIOS and UEFI), 56 boots, 242 PASS, 0 FAIL, 0 SKIP
  (`notes/px42/kasumi-mpx5-users-7e96721.out`), and the same images
  again under `taskset -c 0-3`; hasu, KVM, kasumi's images, BIOS, both
  tiers, two rounds of 28 boots, 121 PASS each
  (`notes/px42/hasu-kvm-7e96721.log`); `tests/mpx3-tree` on kasumi, four
  legs, 28 boots, 135 PASS, 0 FAIL, 0 SKIP, T2's nine refusals on every
  leg (`notes/px42/kasumi-mpx3-tree-7e96721.out`), and again under
  `taskset -c 0-3` from the same images, 134 PASS (the build's T0 is not
  repeated) (its Linux side in throwaway `px13-ubuntu` containers both
  times). CI's `tier pr` run 38504776952 at `7e96721` ran the 19
  `@user` suites on native BIOS, every one green at the first attempt. The other 17 suites `tools/ci-plan` picks
  for these paths, and all 30 in the labelled full run, are CI's: their
  programs must not be built with kasumi's glibc (px36, px39).
- **The soak**: `own soak 100000`, as root and as 1000:1000: each round
  makes a file (mode 04755) and `fchown`s it, makes a directory and
  `chown`s its group, makes a link and `lchown`s it, `fchownat`s the
  file to root (0 for root, -EPERM for the user), and removes all
  three: 1,200,000 calls, 0 wrong answers, `MemFree` one number at the
  start and at every quarter (236,124 kB native, 236,696 kB release),
  the frames line the same before the first program and after the
  last, on every leg and on hasu.
- **The plants** (each cut from `7e96721`, never to be merged):

  | plant | break | red on kasumi | red in CI |
  |---|---|---|---|
  | A, branch `px42-plant-a` `9b791ce` | a new name stamped with the effective ids, not the file-system ids | `notes/px42/kasumi-plant-a.mpx5-users.out`: U1 `own`, one line, `made by uid 1001 1001 1002 1002 gid 2001 2001 2002 2002: a directory 1001:2001 …` | run 38504814748, job 115660866793 (`mpx5-users` the only suite): `notes/px42/ci-38504814748-plant-a-mpx5-users.txt` |
  | B, branch `px42-plant-b` `761156a` | `chown`'s rule for a user removed (anyone may name any id) | `notes/px42/kasumi-plant-b.mpx5-users.out`: U1 `own` from line 30, `fchown own … (-1, 2001) = 0` where Linux says -1 | run 38504817333, job 115660031455: `notes/px42/ci-38504817333-plant-b-mpx5-users.txt` |

  Both stop at the first boot (`stopped early`); U2, U3 and U5 of that
  boot stay green, so each plant reddens the assertion that names its
  break and no other.

## What U3 (checks on files) should know

- **An inode's owner is `tree.uid(i)` and its group `tree.gid(i)`**;
  the caller's side is `cred.uid(a, cred.FS)`, `cred.gid(a, cred.FS)`
  and `cred.in_list(a, g)` (public now). `files.member(a, g)` is the
  class rule's "in the group" (file-system group id or a supplementary
  group), already used by `chown` and by the S_ISGID stamp. The class
  is chosen by the **file-system** user id; privilege for a file is
  file-system user id 0 (R9), as `fchownat` reads it.
- **`perm` already runs as the first program** in `tests/mpx5-users`,
  and every line it writes is held to `tests/mpx5-users.d/perm.pax`
  (385 lines). A check that lands moves lines of that file to Linux's
  text: the counts to move with them are `PERM_LINUX_LINES` (173) and
  the class line (`E 71 71 H 13 13 ROOT 81 67 13 1`). U3's done-when
  (sections A, B's first three columns, G, the held rows) is exactly
  lines that will leave `perm.pax`.
- **13 of the root actor's rows will never match while PAX cannot run
  a program written since boot** (px27): `perm` section A copies itself
  and runs the copy. The same refusal makes every user's `execve`
  column -13 whatever the mode, so the class rule for `execve` cannot
  be shown by `perm` on PAX until the loader can run a written file.
  Either the loader learns that, or U3 holds the execute rule with its
  own probe on an archive file (the archive can now carry any owner and
  mode: `tools/mkinitramfs /bin/x=FILE:0710:1000:2000`).
- **The row `root after setfsuid(1002)`** is the first root row U3
  turns into Linux's (root's 0600 file refused to file-system uid
  1002).
- `perm`'s `settings:` line reads `/proc/sys/fs/protected_*`, which
  PAX does not have (R7: on, fixed; U4's). Its three `! the holder did
  not stop` lines are a SIGSTOP PAX drops (no job control); the held
  rows after them are what U3's done-when names.
- **A file's owner can now be anyone at boot**: an image can hold
  `/home/pax` 1000:1000 and a root 0600 file beside it, which is the
  shape U3's refusals need without a `chown` in the test.
- `~desc`: a pipe's and a socket's `fstat` owner is 0:0 on PAX and the
  maker's file-system ids on Linux; nothing checks it, but `SO_PEERCRED`
  (U5) will want the socket's maker anyway.
- `chown` of `/dev` and `/proc` stays -EROFS by name; U5 gives the
  terminal an owner (`login`'s `fchown` of the tty).

## 4. Evidence index

Shas are this branch's (`px42`). kasumi paths are under
`~/lanes/px42/`; hasu's likewise.

**The rebase.** Trunk moved to `35660af` (px41 merged: the runner
flakes, in the harness, `user/play`, three other suites' scripts and
`docs/SOURCES.md`; nothing under `kernel/`) when the work was otherwise
ready, and the branch was rebased onto it once; the one conflict was
`docs/SOURCES.md`, both sections kept. The shas in this note are the
rebased ones. The history before it is kept on origin as
`px42-prerebase` (head `4286b3e`, the code at `7e96721`): the kasumi
and hasu logs (`*-7e96721.*`), CI run 38504776952 and the two plant
branches name that history. The rebase changed no file under `kernel/`
(`git diff 4286b3e 65ab5a7 -- kernel/` is empty) and none of this
lane's suites or tools: `kmain_console` built from the two trees, at
the same path on kasumi, is the same bytes (native `0ac7fd21…`, release
`e85bd036…`; a native build at another path differs only by the path
it records).

### What was written

- The prediction: `c9805de` (§1 to §3, before any change).
- The programs: `24b1660` (`user/elf/own.c`; px38's `perm.c` copied to
  `user/elf/`, held to `notes/px38/probes/perm.c` by U0;
  `tools/mkcred` builds both), `14e72b5` (the rows the first Linux run
  asked for).
- The recorder: `fb632b4`, `3861b35` (`notes/px42/vminit.c`,
  `linux-vm.sh`, `build.sh`).
- The kernel: `c03c02a` (`kernel/cred`: `in_list` public), `dfa1a52`
  (`kernel/initramfs`: uid, gid), `b68c667` (`kernel/procfs`:
  `owner`), `1e30611` (`kernel/tree` and `kernel/files`: the owner
  word, the stamps, `chown`'s rule, `stat`), `1f5d6e6` (comments).
- The image tool: `a8d55c3` (`tools/mkinitramfs`).
- The suites: `7502f98` (`tests/mpx3-tree`, `user/elf/tree.c`),
  `57da6ba` (`user/elf/ident.c` and px39's recordings taken again),
  `dbe829d` (real root's recordings of the new sessions), `1a27569`
  (`tests/mpx5-users`, `perm.pax`, `ids.pax`).
- The words: `ed714c6` (`kernel/README.md`), `5291315`
  (`docs/SOURCES.md`), `f456fc8` (CHANGELOG).

### What was measured, and where it is

- **Linux, real root**: `tests/mpx5-users.d/linux/` — `own.txt`,
  `own-user.txt`, `perm.txt` (px38's recorded section to the byte; U0
  checks it; re-taken here twice and the same bytes), `own-soak*.txt`
  with `vm-own.meta` (the kernel image's digest, QEMU's version, each
  program's digest); `ls.txt`, `ls-names.txt` with `vm-image.meta` (the
  image archive's digest); px39's seven taken again with `vm.meta`:
  only `ident`'s and `ident-user`'s `owner:` line, `ids`' `setsid()`
  pid and the soaks' `~soak` free memory differ from px39's.
- **The inode's cost**: `notes/px42/kasumi-inode-cost.txt` (trunk's and
  this branch's kernel, the same three images).
- **The archive tool**: `notes/px42/mkinitramfs-same.txt`.
- **PAX**: `notes/px42/kasumi-mpx5-users-7e96721.out`,
  `notes/px42/kasumi-taskset-0-3-mpx5-users-7e96721.out`,
  `notes/px42/kasumi-mpx3-tree-7e96721.out`,
  `notes/px42/kasumi-taskset-0-3-mpx3-tree-7e96721.out`,
  `notes/px42/hasu-kvm-7e96721.log`.
- **The plants**: §F.
- **CI**: run 38504776952 (`tier pr` at `7e96721`, 19 suites green).
- The pull request's own runs at its head (the pr tier, then the
  labelled full run) are named in the PR: a commit naming them would
  move the head.

### Measured, inferred, not verified

**Measured**: everything in §A to §F.

**Inferred**: that the free list's link is safe in a free record's
birth-time word (every read of `I_BTIME` in `kernel/tree` is of a live
inode, read; nothing mechanical holds it, but every suite that frees
and makes inodes, the soak's 300,000 makings included, would see a
corrupt free list); that `/proc/self/cgroup` follows `status`'s owner
rule (Linux was not asked by name); that the set-group-ID strip at
creation asks the same "in the group" as `chown` (measured for the
file-system group id and a supplementary group, not for a group that is
only the real or effective one).

**Not verified**:

- Real root was one kernel build (kasumi's CachyOS 7.2.8); the CI
  runner's Linux was not asked (`tests/mpx3-tree`'s owner line is, at
  every run).
- The other 17 `@user` suites did not run on kasumi or under KVM: CI
  only.
- UEFI under KVM on hasu (pax#56): BIOS only there.
- `chown` of a socket's name by its owner was measured; `connect` to
  it after a `chown` was not (U4).
- More than one process changing one file's owner at once (PAX runs
  one CPU; a system call runs with interrupts off).
- An image entry's owner for a symbolic link or a device: `tree.adopt`
  leaves both out, as before.

### Issues

- **To close at merge**: pax#48 (an image can carry owners; the tree
  adopts them).
- **Would file (none filed)**:
  1. pax: a pipe's and a socket's `fstat` say 0:0; Linux says the
     maker's file-system ids (`~desc`).
  2. pax: `perm` cannot show `execve`'s class rule on PAX while the
     loader runs only archive files (px27's limit meets U3).
- Not chased, did not occur in this lane's runs: pax#45, #47, #53.

## 5. Done-when

- Branch `px42` on origin; pax PR #57, open, unmerged.
- The five sections §1 to §5; the six items §A to §F.
- The test checklist:
  - [x] `tests/mpx5-users`, native and release, BIOS and UEFI, kasumi (TCG)
  - [x] the same under `taskset -c 0-3`
  - [x] the same images under KVM on hasu (BIOS), two rounds
  - [x] `tests/mpx3-tree`, four legs, kasumi, and under `taskset -c 0-3`
  - [x] `tests/ci-plan` (on kasumi; P5 needs a git checkout: CI's)
  - [x] plant A red on kasumi and in CI; plant B the same
  - [ ] the 19 suites of the pr tier at the head: named in the PR
  - [ ] all suites on every leg (`tier full`) at the head: named in the PR
- `wolf/tools/lane-audit.sh pax px42 57` exit 0: named in the PR.
- Close pax#48 at merge; nothing filed.
- Trees: kasumi `~/lanes/px42/` keeps `out/` and `bin/`; build
  directories removed. hasu `~/lanes/px42/` keeps `out/`. Plant
  branches `px42-plant-a` and `px42-plant-b` stay on origin, never to
  be merged; their local worktrees are removed.
