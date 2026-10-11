# px27 — The writable tree (files that can be made, changed and removed)

Contract: px27's, `sprints/pax/27-the-writable-tree/` in wolffe-lang/wolf
(read 2026-10-11). Branch `px27` in pax, cut from pax trunk `5afb903`
(px26 merged). §1–§3 are committed before the first change to the
kernel or the tests; §2's straces were taken first, as the contract's
first act, and the boreutils pin moved in a commit of its own
(`911233e`).

One deliverable: PAX's file tree is writable, in memory. The boreutils
file changers (`mkdir`, `rmdir`, `rm`, `mv`, `cp`) and pelt's `>` and
`>>` run unmodified with sessions byte-identical to Linux, and every
file call lobo makes for its logs and its pid file is answered as
Linux answers it. No disk: the tree lives in frames and is gone at
halt.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read (ruling #22), and
  none is searched for; the refs clone's sparse checkout is never
  widened. Facts come from the Linux man pages (`open(2)`, `openat(2)`,
  `write(2)`, `pwrite(2)`, `lseek(2)`, `truncate(2)`, `mkdir(2)`,
  `rmdir(2)`, `unlink(2)`, `rename(2)`, `link(2)`, `symlink(2)`,
  `readlink(2)`, `chmod(2)`, `chown(2)`, `utimensat(2)`, `stat(2)`,
  `statx(2)`, `getdents64(2)`, `fsync(2)`, `umask(2)`, `access(2)`,
  `copy_file_range(2)`, `sendfile(2)`, `path_resolution(7)`,
  `inode(7)`, `tmpfs(5)`), POSIX, the uapi headers the sparse checkout
  holds, and black-box runs on Linux's tmpfs: strace of the real
  binaries, and static C programs that print what Linux answers.
  boreutils, pelt and lobo are used as built from their own
  repositories at their pins, never read for how they work; no GNU,
  busybox, uutils or toybox source.
- No block device, no on-disk format, no page cache, no `mmap` of a
  file. No AF_UNIX path sockets, no readiness, no SMP. `kernel/socket`,
  `kernel/tcp`, `kernel/udp`, the readiness calls and their tests are
  px24's: not touched; what changes in `kernel/files` and `kernel/user`
  is kept small, the tree itself in a module of its own.
- No system call and no flag is added on a guess: each is in a strace
  this lane took, of a binary in an image or of lobo. Anything else is
  refused with Linux's errno, by name, and the refusals are counted.
- The tree's memory is bounded and accounted: a stated cap, `ENOSPC` at
  it, every frame given back when a file's last name and last
  descriptor are gone and when it is truncated; a write never takes the
  kernel's last frames.
- **The utilities under test delete.** `rm`, `rmdir` and `mv` run only
  inside PAX guests and inside throwaway containers in which nothing of
  the host is mounted but a scratch directory under `~/lanes/px27/` (and
  the programs, read-only); never against a host path.
- Test binaries for PAX are built in the Ubuntu 24.04 container on
  kasumi (`px13-ubuntu`) or on the CI runner, never with kasumi's own
  glibc. A toolchain pin comes from the release archives by digest.
- No `rm` outside `~/lanes/px27/` on any host; no scratch in `/tmp`; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag; no
  `2>/dev/null` on a checkout; no trailer of any kind on a commit or
  the PR. No build on nomad-1. Nothing is installed anywhere.
- No "seen red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, `WOLF_PAIRING_REQUIRE_SIBLING=1`,
  full output kept, SKIP counted; `wolf build` exit 2 is a compile
  error; the rows with two processes also under `taskset -c 0-3`.
- kasumi and hasu: remote commands wrapped in `bash`, jobs under
  `setsid` with a pid file, ended by that pid only; a container is
  stopped by its own id only.
- A planted break fails fast: the suite it reddens has a deadline
  before the break is planted.

## 2. Inputs, verified (2026-10-11)

| input | found |
|---|---|
| pax trunk | `5afb903` (px26 merged, PR #28), as the contract says |
| the kernel's pin | wolf 0.2.27 (`5e17eebe…`) / lupin 0.1.50 by archive digest (`kernel/wolf.pin`) |
| `user/boreutils.pin` | was `870815c` (bu20); moved to `abc59f5bc3ff832aad8bd819017bf6cdae3df9a3` (bu21, boreutils trunk on origin) in `911233e`. It pins the same toolchain (wolf 0.2.27, wolf-std `87ba162`) |
| `user/pelt.pin` | `b32bebc` (sh05), pelt trunk on origin: not moved |
| lobo | trunk `b256d2e0f496b7b30bdb3454753154d7da920c70` on origin; built static here (wolf 0.2.27 archive `5e17eebe…`, wolf-std `14f0ab2`, as its `wolf-toolchain.toml` names): `bf1f6c6f…`, 14,697,920 bytes |
| the binaries the straces ran | built by pax's own `tools/mkboreutils` and `tools/mkpelt` at the pins, in `px13-ubuntu` on kasumi (glibc 2.39 static): `mkdir` `1dd84e0f…`, `rmdir` `fd6ae2ff…`, `rm` `85a8aff9…`, `mv` `90969f59…`, `cp` `01571ffc…`, `cat` `c19a5579…`, `ls` `08d01221…`, `stat` `3b20e3ea…`, pelt `0f82c5e6…` (px26's digest again: the build repeats). Each is about 12.9 MB: the shell's image gains 65 MB with the five |
| **how files work today** (read from `kernel/files` at `5afb903`) | the tree is the initramfs, looked up by whole path after the path is made canonical as a string, plus a synthetic `/dev`; nothing is an inode. `openat` with `O_CREAT` on a missing name, or with `O_WRONLY`, `O_RDWR` or `O_TRUNC` on a file or directory, is refused by name, -EROFS; `O_CREAT\|O_EXCL` on a name that exists is -EEXIST; `O_APPEND` is only a status flag; `O_DIRECTORY` on a file is -ENOTDIR; every other flag is ignored silently. `write` reaches the console, `/dev/null`, a pipe or a socket; a file's descriptor cannot be open for writing at all. 32 descriptors a process (words in its area), 64 open files in the machine (`pax_ofiles`), 16 pipe buffers. `statx` and `fstat`: mode, size and link count from the archive's header, every directory 0755 with size 0 and 2 links, uid, gid and every time 0, blocks eight a page, one device number (0:1) for everything, `/dev` included. `getdents64`: the archive's order, a walk of the whole archive per entry. `readlink` answers `/proc/self/exe` alone. `..`, `.` and `//` are folded as text before the lookup, so `a/../b` never asks whether `a` exists; a trailing slash on what is no directory is -ENOTDIR; there is no symbolic link to follow. `sendfile` takes an initramfs file to the console, `/dev/null`, a pipe or a socketpair; `copy_file_range` is -EINVAL always; `splice` needs a pipe |
| **the list, re-taken** | `notes/px27/straces/` (strace 6.8 on Linux 7.2.8, each program on a tmpfs inside a throwaway container; `strace-changers.sh`, `strace-lobo.sh`): 50 runs of the file changers, `ls`, `stat` and pelt's redirections (`bu21-NN-*.strace` with what each printed), and lobo serving, reloading, reopening its logs and stopping, with one worker and two (`lobo-b256d2e-files.txt`, its file-side lines by line number; the whole straces stay on kasumi, `serve.strace` `eb9e93e0…` and `f7b048c4…`). The marked list is below |
| bu21's `tools/roottest` | read as a tool, not for how `rm` works: it copies `rm`, `mv` and `cp` into an image, runs each case in a container with no mount and no network, as a user and as the container's root, and holds exit status, standard error and a sum of a sentinel tree to what GNU 9.11 answered in the same image. What the guard asks of a kernel, from the strace (`bu21-42-rm-rf-root`, `bu21-41-rm-r`): `rm` asks `statx("/", AT_SYMLINK_NOFOLLOW)` and `statx` of the operand, and of every directory it is about to descend into, and refuses when they are the same file. `.` and `..` as a last component are refused from the text alone, with no call. So PAX must answer one device and inode for `/` however it is reached, and a different pair for every other directory |
| kasumi | QEMU 11.1.1, TCG only; `px13-ubuntu` (`ad896450…`); `/home` 96% (45 GB free) |
| hasu | KVM through `nix-shell -p qemu` |

### The marked list

What each call is on PAX at `5afb903`: **right** (present and Linux's
answer), **wrong** (present, another answer), **absent** (-ENOSYS).

| call, as straced | who | at `5afb903` |
|---|---|---|
| `mkdir(path, 0777)` (83): 0, -EEXIST, -ENOENT, -ENOTDIR | `mkdir`, `cp -r`, lobo (`./logs`) | absent |
| `rmdir(path)` (84): 0, -ENOENT, -ENOTEMPTY, -ENOTDIR | `rmdir`, `rm -r` | absent |
| `unlink(path)` (87) | `rm`, lobo (its pid file) | absent |
| `rename(old, new)` (82): 0 (a file, a file over a file, a directory), -EINVAL (a directory into itself), -EXDEV (onto another file system), -ENOTDIR (`f1` to `nodir/`) | `mv`, lobo (`lobo.pid.new` to `lobo.pid`) | absent |
| `openat(…, O_WRONLY\|O_CREAT\|O_TRUNC\|O_CLOEXEC, 0666)` | pelt `>`, `>\|`, `cp` over a file, lobo's pid file | wrong (-EROFS) |
| `openat(…, O_WRONLY\|O_CREAT\|O_APPEND\|O_CLOEXEC, 0666)` | pelt `>>`, lobo's access log | wrong (-EROFS) |
| `openat(…, O_RDWR\|O_CREAT\|O_EXCL\|O_CLOEXEC, 0666)` | `cp` to a new name | wrong (-EROFS) |
| `openat(…, O_RDWR\|O_CREAT\|O_CLOEXEC, 0666)` | pelt `<>` | wrong (-EROFS) |
| `openat` of a directory for writing: -EISDIR; in a directory that is gone: -ENOENT | pelt | -EISDIR right; the other cannot arise |
| `openat(…, O_RDONLY\|O_CLOEXEC)`, `O_RDONLY\|O_NONBLOCK\|O_CLOEXEC[\|O_DIRECTORY]` | all | right |
| `write(fd, …)` to a file, at its offset or (`O_APPEND`) its end | pelt's built-ins, lobo's log lines | wrong (no such descriptor can exist) |
| `copy_file_range(in, NULL, out, NULL, n, 0)` file to file: the count, 0 at the end; -EBADF when `out` has `O_APPEND`; -EXDEV across file systems; -EINVAL when one end is no regular file | `cp`, `cat` | wrong but for the last |
| `sendfile(out, in, NULL, n)` into a file; -EINVAL when `out` has `O_APPEND` or `in` is a pipe | `cat` | wrong (-EBADF) |
| `splice` between two files: -EINVAL | `cat` | right |
| `read`/`write` in 262144-byte pieces after those refusals | `cat >>` | wrong (the write) |
| `statx(dirfd, path, AT_STATX_SYNC_AS_STAT[\|AT_SYMLINK_NOFOLLOW][\|AT_EMPTY_PATH], STATX_ALL)` | all | right for an initramfs file; wrong for a directory (size, links, times), and nothing reflects a change |
| `fstat`, `getdents64`, `lseek(fd, 0, SEEK_CUR)`, `getcwd`, `chdir`, `fcntl(F_DUPFD_CLOEXEC)`, `dup2`, `readlink("/proc/self/exe")`, `ioctl(TCGETS)` | all | right, as far as a read-only tree goes; `getdents64` of a directory that is gone (-ENOENT) cannot arise |
| `openat("/proc/self/status")`, `/proc/self/cgroup`, `/sys/fs/cgroup/cpu.max`, `/sys/devices/system/cpu/online`; `unlink` and `bind` of `logs/control.sock` | lobo | -ENOENT here; not this lane's (no `/proc`, no `/sys`, no AF_UNIX path socket) |

Not in any strace, so **not added** unless the probe (below) is what
asks: `mkdirat`, `unlinkat`, `renameat`, `renameat2`, `link`/`linkat`,
`symlink`/`symlinkat`, `chmod`/`fchmod`/`fchmodat`, `chown`/`fchown`,
`utimensat`, `truncate`/`ftruncate`, `pwrite64`, `fsync`/`fdatasync`,
`access`/`faccessat`, `umask`, `O_NOFOLLOW`, `O_SYNC`, `O_DIRECT`,
`O_TMPFILE`, `O_PATH`. bu21 leaves `touch`, `ln` and `chmod` out and
refuses `mkdir -m`, `cp -p` and a move across file systems itself, by
name, before any call. **How this lane reads the contract here**: its
item 2 names some calls outright (`pwrite64`, `ftruncate`/`truncate`,
`mkdirat`, `unlinkat`, `renameat`/`renameat2`, `fsync`/`fdatasync`,
`faccessat`, `umask`, `O_NOFOLLOW`) and others "as shown" (`linkat`,
`symlinkat`, `fchmod`, `fchown`, `utimensat`). The first group is
added and held to Linux by the probe, a static binary in an image
whose strace on Linux is kept, so each is in a strace this lane took
and none rests on a guess; the second group is in no strace and is
refused by name.

A finding on the way, not PAX's: boreutils' `cat < f >> f` never ends
(it reads what it appends; GNU `cat` refuses "input file is output
file"). The first strace run filled 264 MB before it was stopped.

## 3. Prediction (committed before the first change)

### P1. The tree's shape

- A new module, `kernel/tree`: **inodes** in a table that grows a frame
  at a time (128 bytes each, 32 a frame, at most 16,384), each with its
  mode, link count, size, three times, how many descriptors and working
  directories hold it, and where its bytes are. `kernel/files` keeps the
  descriptors and asks the tree by inode number; a node is an inode
  where it was an archive offset.
- **A file's bytes** are 4096-byte frames under a small index: none for
  an empty file, the one frame alone up to 4096 bytes, one index frame
  of 512 pointers up to 2 MiB, two levels up to 1 GiB (a larger offset
  is -EFBIG). A page never written holds no frame and reads as zeros,
  as tmpfs keeps a hole (`lseek` past the end and a write there:
  `st_blocks` counts the pages written, to be measured on tmpfs). A
  file shrinks by `O_TRUNC` or `ftruncate`, which give back every frame
  past the new size at once and zero the tail of the last page.
- **A directory** is a file of records (inode, record length, name
  length, name; at most 255 bytes a name), a removed entry's record
  reused by the next name that fits. Each directory inode knows its
  parent, so `..` and `getcwd` walk up. `getdents64`'s position is a
  record's offset: an entry present for the whole of a read of the
  directory is returned exactly once whatever is added or removed
  meanwhile. The order is the records' (oldest first, but for reused
  records): tmpfs on 7.2.8 lists newest first; POSIX leaves it open and
  the sessions never depend on it.
- **The cap**: the tree may hold half of the frames that were free when
  it was made (as tmpfs defaults to half of memory), and no allocation
  is made when fewer than 2,048 frames (8 MiB) would be left free in
  the machine: -ENOSPC either way, with nothing half-written (a write
  that cannot have all its frames writes the part that fits and
  answers that count, as `write(2)` allows; one that can have none is
  -ENOSPC). **What a file costs**: 128 bytes of an inode frame, a record
  in its directory (16 bytes and the name), and for its bytes one frame
  up to 4096, n + 1 up to 2 MiB, n + 1 + ceil(n / 512) beyond.
- Every frame is counted: `tree: frames <held>, inodes <live>` beside
  the frames line a kernel prints after init's end, and in the soak.

### P2. The initramfs

- **A read-only layer under the writable one, per file.** When the tree
  is made (at boot, before the first program), every archive entry
  becomes an inode: a directory a real directory (a missing parent made,
  0755), a file an inode whose bytes are *the archive's own*, in place,
  with no frame. A read comes from the archive where no page has been
  written; the first write to a page copies that page (4096 bytes) into
  a frame; a truncation cuts how much of the archive the file still
  reads. So every initramfs file is writable, removable and renamable
  like any other (`echo x >> /etc/motd`, `rm /bin/true`, `mv`), and
  nothing is copied at boot. The archive's pages are Limine's module
  and are never given back: unlinking `/bin/pelt` frees no frame.
- **Cost at boot**: the shell's image (three directories, about thirty
  entries) takes 5 frames ± 2 (the table's root, one frame of inodes, a
  frame of records for `/`, `/bin` and `/etc`).
- `execve` runs a file only while it is still the archive's bytes
  whole (the loader reads one contiguous image): a program written or
  copied since boot is refused by name, -EACCES. `/proc/self/exe`
  keeps answering the path the program was loaded by.
- `/dev` stays synthetic, a second file system in every answer: its
  own device number, `rename` across it -EXDEV, making or removing a
  name in it refused by name -EROFS (Linux's `/dev` is writable: named
  drift); `mkdir /dev` -EEXIST, `rmdir /dev` and `rename` of it -EBUSY.
  `/proc` is still only `readlink("/proc/self/exe")`.

### P3. Link counts, and a file that is unlinked while open

- A file's link count is 1 (hard links are in no strace: `link` and
  `linkat` are refused by name, -EPERM, as `link(2)` words a file system
  that makes none); a directory's is 2 plus its subdirectories, and its
  size 40 plus 20 an entry, tmpfs's numbers (measured: 40, 60, 80, 100,
  120, 160, 320 for 0 to 14 entries), since `ls -l` prints them.
- `unlink` removes the name and drops the count; the inode and its
  frames live on while any descriptor holds it (reads, writes, `fstat`
  with `st_nlink` 0 all still answer) and go back at the last close:
  the frame count returns exactly.
- `rmdir` of a directory that is some process's working directory, or
  open, succeeds (measured on Linux: `rmdir ../w` from inside `w`): the
  inode stays, empty, until the last holder leaves; in it `getdents64`
  and a create are -ENOENT, `stat(".")` answers with 0 links
  (predicted), `getcwd` is -ENOENT (predicted), `..` still leads to
  where it was.
- `rmdir` of a directory with an entry is -ENOTEMPTY; of a file
  -ENOTDIR; of `.` -EINVAL; of `..` -ENOTEMPTY; of `/` -EBUSY
  (predicted from `rmdir(2)`).

### P4. `rename`

- All or nothing: every refusal is decided, and the room for the new
  name found, before the first change; then the change is made with no
  call between (one CPU, interrupts off from `syscall` to `sysret`), so
  no process ever sees both names or neither.
- Over an existing file: the name now leads to the moved inode and the
  old target loses a link (and lives on while open). The same inode
  under both names: 0 and nothing changes. A file onto a directory
  -EISDIR; a directory onto a file -ENOTDIR; a directory onto an empty
  directory replaces it, onto one with an entry -ENOTEMPTY; **a
  directory into itself or below itself -EINVAL** (measured: `mv tree5
  tree5/sub`); a last component `.` or `..` -EBUSY (predicted; -EINVAL
  possible); a trailing slash on what is not a directory -ENOTDIR
  (measured for the target); a missing source -ENOENT; across `/dev`
  -EXDEV.
- A directory that moves takes its subtree, its open descriptors and
  any process working in it with it (`getcwd` answers the new path),
  and its `..` is the new parent; both parents' link counts follow.
- `renameat2`: flags 0 only; `RENAME_NOREPLACE`, `RENAME_EXCHANGE` and
  `RENAME_WHITEOUT` are refused by name, -EINVAL.

### P5. Metadata: what is real, what is fixed

- **Real**: the type; the permission bits given at creation, `mode &
  ~umask & 07777` (so 0644 and 0755 under 022); size; link count;
  blocks (eight for each frame held, and for an initramfs file's
  untouched pages); the inode number (unique, stable for the inode's
  life, never 0, `/`'s its own); **mtime and ctime**, from
  CLOCK_REALTIME (the CMOS clock at boot plus 10 ms ticks, so times
  step by 10 ms), set at creation, mtime and ctime by a write or a
  truncation that changes something, a directory's by an entry made,
  removed or renamed, ctime by a rename or a link count's change;
  **atime** set at creation and by a read when it is not later than
  mtime (relatime's rule; what tmpfs in the container does is to be
  measured, and a session never prints an access time).
- **Fixed**: uid and gid 0 (every process is root); an initramfs
  entry's three times are its header's mtime (0 in every image made by
  `tools/mkinitramfs`) until something changes it; `st_blksize` 4096;
  no extended attributes.
- **Refused by name**: `chmod`, `fchmod`, `fchmodat`, `chown`, `fchown`,
  `lchown`, `fchownat`, `utimensat`, `utimes`, `utime` -EOPNOTSUPP (in no
  strace: bu21 has no `chmod` or `touch`); `link`, `linkat`, `symlink`,
  `symlinkat`, `mknod`, `mknodat` -EPERM.
- Permission checks: none can fail, since every process is root
  (`access` and `faccessat` answer 0 for what exists, but X_OK on a
  file with no execute bit, -EACCES, as root gets on Linux).

### P6. `umask`

- One per process, in its area: 022 for the first program (what a
  process on Linux is started with in the reference container and on
  the runner, measured before it is relied on), inherited by a child,
  kept across `execve`; `umask(2)` (95) sets it and answers the old
  one. It masks `openat`'s and `mkdir`'s mode.

### P7. Calls added, and each refusal's errno

- **New numbers, from the straces**: `rename` (82), `mkdir` (83),
  `rmdir` (84), `unlink` (87). **From the contract's list, held by the
  probe's strace**: `pwrite64` (18), `fsync` (74), `fdatasync` (75),
  `truncate` (76), `ftruncate` (77), `umask` (95), `mkdirat` (258),
  `unlinkat` (263, with and without `AT_REMOVEDIR`), `renameat` (264),
  `renameat2` (316), `faccessat` (269) and `access` (21), `faccessat2`
  (439) if glibc 2.39 asks it first. 16 numbers ± 2.
- **Changed**: `openat` and `open` take `O_CREAT`, `O_EXCL`, `O_TRUNC`,
  `O_APPEND`, `O_WRONLY`, `O_RDWR` and `O_NOFOLLOW` on the tree (-ELOOP
  for `/proc/self/exe` with `O_NOFOLLOW`, the one link there is; a path
  component longer than 255 bytes -ENAMETOOLONG); `write` writes a
  file; `lseek` past the end is allowed and a write there leaves a
  hole; `copy_file_range` copies between two files (-EBADF for an
  `O_APPEND` target, -EXDEV never: one file system holds every regular
  file; -EINVAL for the same file with overlapping ranges);
  `sendfile` takes any file to any file (-EINVAL for an `O_APPEND`
  target); `statx`, `fstat` and `getdents64` answer from the inodes.
- **Refused by name, counted** (`tree: refusals <n>` with the frames
  line): on `openat`, `O_DIRECT`, `O_SYNC`, `O_DSYNC`, `O_NOATIME`,
  `O_PATH` -EINVAL and `O_TMPFILE` -EOPNOTSUPP; `renameat2` with a
  flag -EINVAL; `unlinkat` with a flag but `AT_REMOVEDIR` -EINVAL; the
  metadata calls and the link calls as P5; anything made or removed
  under `/dev` -EROFS; `execve` of a file written since boot -EACCES;
  `fallocate` stays -ENOSYS.
- Errnos a probe will hold to tmpfs: EEXIST, ENOENT, ENOTDIR, EISDIR,
  ENOTEMPTY, EINVAL, ENAMETOOLONG (a 256-byte component; a 4096-byte
  path), ELOOP (as above; Linux's `/proc/self/exe` answers the same),
  EXDEV (`/dev`), EBUSY, EFBIG, ENOSPC, EBADF (a write to a descriptor
  opened to read, and the reverse), and EACCES/EPERM as root sees them
  (almost never: root passes every permission check on a file).

### P8. Numbers

- **Frames at the prompt**, the shell's image with the same programs,
  trunk's kernel against this one: 5 ± 2 fewer free (the tree as made
  at boot), and the same after `exit` as before the first program once
  a session has removed what it made. The five new programs cost
  about 16,000 frames of initramfs on top (65 MB), which is the
  image's, not the kernel's. (Trunk's count is read from a baseline
  boot before the first change and written here beside the result.)
- **16 MiB**, one `write` of 1 MiB at a time, then read back the same
  way, timed with CLOCK_MONOTONIC in the guest (10 ms steps): under TCG
  on kasumi write 30 MiB/s and read 40 MiB/s, under KVM on hasu write
  400 MiB/s and read 500 MiB/s, each within a factor of three (a
  byte-at-a-time copy through the HHDM is what `kernel/uaccess` does
  today; the tree adds an index walk per page).
- **The soak**: 10,000 rounds of create, write, rename, unlink with the
  frames free, the inodes live and the heap the same after as before;
  a fill to -ENOSPC and back with the same three numbers; under TCG in
  under 180 s a boot.
- At least 100 KVM boots on hasu for the lane's suites, all green.

### P9. What moves

- **Every kernel's bytes** (each links `kernel/files`), so every ISO.
- `tests/mpx3-shell`: its image gains the five programs, so `ls /bin`
  and `ls -l /bin` grow in the transcripts kept beside the keys, and
  the shell's image needs more than 256 MiB under BIOS too (the
  initramfs alone is about 235 MB); S4's -ENOSYS set stays `273 334`.
- `tests/mpx3-boreutils`, `mpx3-loader`, `mpx3-console`, `mpx3-user`,
  `mpx3-threads`, `mpx3-speaker`, `mpx3-screen`, `tour`, `mpx4-*`: the
  verdicts do not move. Their "every frame back" lines hold, since the
  tree is made before the count is first taken; the frame counts
  themselves drop by the tree's few frames wherever an initramfs is
  loaded, and by 1 or 2 where there is none.
- A new suite, `tests/mpx3-tree`, with its own CI job and deadline:
  the probe (one static C file, on Linux's tmpfs and on PAX, compared
  byte for byte), the typed sessions, the soak and the fill.
- No downstream repo moves: pax consumes pelt and boreutils at pins.

### P10. What fails first

- bu21's five on trunk's kernel: `mkdir d` prints `mkdir: cannot
  create directory 'd': Function not implemented` (83 is -ENOSYS) and a
  line `syscall 83: -ENOSYS`; `echo hi > f` in pelt fails with pelt's
  own `cannot create f:` and the kernel's `refused: the initramfs is
  read-only, -30`.
- Planted breaks: an `unlink` that keeps the frames reddens the soak's
  flat-frames assertion and the probe's frame line, nothing else; a
  `rename` that leaves both names reddens the probe and the session
  that moves a file, nothing else; each within one boot's deadline.

### §3 against what was measured

| predicted | measured |
|---|---|
| P1: a module of its own, `kernel/tree`: inodes of 128 bytes in a table that grows a frame at a time; a file's bytes frames under an index of depth 0, 1 or 2; a hole holds no frame | as built. A hole's blocks are tmpfs's (the probe's `hole:` lines, on both: a byte written at 1 MiB costs 8 blocks, a file cut inside a hole 0, a cut tail reads zero when the file grows again). Not predicted: the inode table's frames are never given back (they hold the most inodes there were at once), so the kernel's line counts them apart |
| P1: a directory is a file of records; a position is a record's offset; an entry there for the whole of a reading is returned exactly once | **right** (`dir: read while it changes: every name that stayed was returned exactly once 1, a name returned twice 0, a removed name returned after its removal 0`, on both); a record's header is 8 bytes, not the 16 the cost line said |
| P1: the cap is half the frames free when the tree is made, and never below 2,048 free in the machine: -ENOSPC | **right, both measured** in the soak: `tree: full: frames held 32038 of 32038, frames free 31491` (the cap, 125 files of 1 MiB), and with 120 MiB of the program's own memory held `frames held 30699 of 32038, frames free 2048, reserve 2048` (the reserve, 120 files), after which the program could still have 64 KiB of memory of its own |
| P2: the initramfs a read-only layer per file, a page copied at its first write; 5 frames ± 2 at boot | **right: 6** in the shell's image (the table's root, the page of zeros, one frame of inodes, a frame of records each for `/`, `/bin` and `/etc`), and 6 in the probe's. `/etc/pax-run` written in the middle, cut to 3 bytes, grown, renamed, removed and made again: the probe's `initramfs:` lines, on both; the session's `echo more >> /etc/motd` leaves exactly one frame |
| P2: `execve` of a file written since boot refused by name, -EACCES; a renamed program still runs | **right** (`~exec: … status 113` and its refusal line; `initramfs: the program renamed 0, run by its new name: status 7`, on both) |
| P2: `/dev` a second file system: -EXDEV across it, -EROFS for a name made in it, `mkdir /dev` -EEXIST, `rmdir /dev` and `rename` of it -EBUSY | **right** (`rename: … of /dev -16, onto /dev -16, into /dev -18, out of /dev -18`, `remove: … of /dev -16`, `make: … of /dev -17`, on both; `~limits: a file made in /dev -30, a directory -30` on PAX, where Linux makes them: named drift) |
| P3: a file's link count 1, a directory's 2 and one a subdirectory, its size 40 and 20 an entry | **right** on both (`dir:` and `rename:` lines: 40, 140, 120, 100, 760) |
| P3: an unlinked file lives while a descriptor holds it, `st_nlink` 0, and its frames return at the last close | **right** (`unlinked:` lines on both; the kernel's line after the probe: every frame back but the two named in T4) |
| P3: a working directory removed: it stays, empty; `getdents64` and a create -ENOENT; `stat(".")` 0 links (predicted); `getcwd` -ENOENT (predicted); `..` still leads up | **right, all of it**, on both (`cwd:` lines) |
| P3: `rmdir` of `.` -EINVAL, of `..` -ENOTEMPTY, of `/` -EBUSY | **right** on both |
| P4: `rename` all or nothing; over a file; the same inode; -EISDIR, -ENOTDIR, -ENOTEMPTY, -EINVAL into itself and below; `.` and `..` -EBUSY ("-EINVAL possible"); a moved directory takes its subtree and a process working in it | **right** on both, -EBUSY included; and 500 renames over a name while another process opens it: the reader never found the name missing or empty (`atomic:`), on both |
| P5: mtime and ctime real, 10 ms steps; atime by relatime's rule; uid, gid 0; an initramfs entry's times its header's | **right** as far as the probe goes (`times:` lines on both: which of the three a write, a read, a rename, a truncation and an unlink move, and a second read leaving atime alone). A directory's atime on a reading of it is not moved on PAX and not probed |
| P5, P7: refused by name: links, device nodes -EPERM; mode, owner, times -EOPNOTSUPP; the open flags; a `renameat2` flag; counted | **right**: twelve refusal lines in the probe, twelve counted (`tree: … refusals 12`), T2 |
| P6: umask 022 at start, inherited, kept | **right** (`make: umask 022`, `mode:` lines on both) |
| P7: 16 new numbers ± 2 | **17**: 18, 21, 74, 75, 76, 77, 82, 83, 84, 87, 95, 258, 263, 264, 269, 316, 439 (glibc 2.39's `faccessat` asks `faccessat2` first; the probe asks 269 itself). Each is in a strace: 82, 83, 84, 87 in bu21's and lobo's, the rest in the probe's (`notes/px27/straces/tree-probe.calls.txt`) |
| P7: `O_RDONLY\|O_TRUNC`, `pwrite` on an O_APPEND descriptor, `copy_file_range` onto O_APPEND and onto itself, `sendfile` and `splice` between files | all as Linux, measured where the prediction was silent: `O_RDONLY\|O_TRUNC` truncates; `pwrite` at 0 on an O_APPEND descriptor appends; `copy_file_range` onto O_APPEND -EBADF, overlapping itself -EINVAL, apart 10; `sendfile` onto O_APPEND -EINVAL; `splice` file to file -EINVAL |
| P7: -EFBIG past 1 GiB | **PAX only** (`~limits: a byte written at 1 GiB -27, a file grown to 2 GiB -27`; tmpfs takes both): named drift |
| P8: frames at the prompt 5 ± 2 fewer than trunk's with the same programs | **the tree's own: 6. The kernel's: 36** (trunk `88544 before, 88046 with 1 processes`; this kernel `88508`, `88010`, the same thirteen programs and 512 MiB): the other 30 are the kernel's own image, which grew by that many pages, and were not predicted. With bu21's five in the image: @@SHELL_FRAMES@@ |
| P8: 16 MiB under TCG write 30 MiB/s, read 40 MiB/s; under KVM 400 and 500, each within a factor of three | **wrong by more than that, the right way**: the tree copies with REP MOVSQ, not a byte at a time. kasumi, TCG: native 128 MiB rewritten in 130 ms and read in 130 ms (about 985 MiB/s), the first 16 MiB (frames taken and zeroed) in 30 ms; release 50 ms and 40 ms (2,560 and 3,200 MiB/s). hasu, KVM: @@KVM_SPEED@@. The guest's clock steps 10 ms |
| P8: the soak flat, the fill to ENOSPC and back, under 180 s a boot | **right**: four census lines, all `frames held 7, inodes 7, frames free 63522` (native BIOS); every frame and inode back after the two fills; the program's break moved 0 bytes; a soak boot takes about @@SOAK_SECS@@ s on kasumi |
| P8: at least 100 KVM boots on hasu | @@KVM_BOOTS@@ |
| P9: every kernel's bytes move; `tests/mpx3-shell`'s three transcripts that list `/bin` | **right**: `user/console/shell-howl.expect`, `shell-plumb.expect`, `shell-long.expect` (S6); S2 held on the first boot. The shell's image already booted with 512 MiB on both firmwares (px26), so nothing changed there |
| P9: the other suites' verdicts do not move | @@GAUNTLET@@ |
| P10: bu21's five on trunk's kernel: `mkdir: cannot create directory …: Function not implemented`, `syscall 83: -ENOSYS`; `echo one > f`: pelt's own refusal and `refused: the initramfs is read-only, -30` | **right** (`notes/px27/kasumi-red-shell-tree-on-trunk-kernel.txt`: `mkdir: cannot create directory '/t': Function not implemented`; `pelt: line 5: cannot create a/f1: Read-only file system`); the probe on trunk's kernel: -ENOSYS for 18, 83, 84, 87, 95 and exit status 9 (`kasumi-red-tests-on-trunk-kernel.mpx3-tree.out`) |
| P10: plant A reddens the probe's frame line; plant B the probe | **right**, and in how: plant A at T4 (`792 frames not back`), plant B at T1 (`rename: a to c 0: a mode 100644 …`: both names) and then a kernel panic (the directory's entry count goes below zero when the second name is removed), which is why a boot now ends at a `PANIC` line too: the first run of plant B on kasumi waited out the boot's 300 s |

## 4. Evidence index

### The Linux side

- The straces (strace 6.8, Linux 7.2.8, kasumi, each run in a throwaway `px13-ubuntu` container, the programs on a tmpfs): `notes/px27/straces/bu21-NN-*.strace` and `.out` (50 runs of the file changers, `ls`, `stat` and pelt's redirections; `strace-changers.sh`), `lobo-b256d2e-files.txt` (lobo's file-side lines; `strace-lobo.sh`), `tree-probe.calls.txt` (every distinct call the probe makes, counted; the whole strace `@@PROBE_STRACE@@` stays on kasumi). The marked list is §2's.
- Every transcript's reference is taken afresh by the suite: `tools/linux-tree` (a throwaway container, no network, nothing of the host mounted but a staging directory; inside it the root a tmpfs, `tools/linux-tty --root --pid1`). On kasumi the container is `px13-ubuntu` on Linux 7.2.8 (podman); in CI `python:3.12-slim` by digest on the runner's Linux 6.17.0-1022-azure (docker 28.0.4): the probe prints the same on both, and PAX the same as each.

### The probe (`user/elf/tree.c`, one static file on both)

- Linux and PAX, `cmp` equal: `notes/px27/session-probes.{linux,pax}.txt` (kasumi, native BIOS, the gauntlet at `ef994df`); the `~` lines differ by design and T2 holds PAX's to their text. In CI the same comparison runs against the runner's kernel on both tiers, BIOS and UEFI (job `mpx3-tree`).

### The sessions

- `shell-tree`, PAX against Linux, `cmp` equal with seven dates compared by rule: `notes/px27/session-shell-tree.{pax,linux}.txt`; the same keys through the PS/2 keyboard (`shell-tree-ps2`); both tiers, BIOS and UEFI (T1). `rm -rf /` is refused with Linux's two lines and status 1, and afterwards Linux's root holds the 25 names it started with (T6) and PAX's tree the inodes it was made with (T4).

### The soak and the fill

- `notes/px27/kasumi-native-bios-soak.serial.log`: the four census lines, the two `tree: full:` lines, the frames and tree lines after init's end; the program's own lines in `session-soak.{pax,linux}.txt`.

### Frames at the prompt

- Before: `notes/px27/kasumi-base-5afb903.mpx3-shell.out` (trunk's kernel, pelt and the twelve programs: `frames free 88544 before, 88046 with 1 processes`). After, the same programs: `88508`, `88010` (kasumi, this lane's first boot of the suite on the new kernel); with the eighteen: the gauntlet's `mpx3-shell` output.

### Red first

- On trunk's kernel (`5afb903`'s `kernel/` and `boot/` under this lane's tests, kasumi, native BIOS): `notes/px27/kasumi-red-tests-on-trunk-kernel.mpx3-tree.out` (the probe: T1 to T4 and T8 FAIL, `stopped early`) and `kasumi-red-shell-tree-on-trunk-kernel.txt` (the typed session's first lines).
- Planted break A (a file's frames are kept when it goes), commit dc80c20: CI run **38150572440**, job mpx3-tree **114502991094** the only failing job of 23, red 3 min 26 s after it started (`FAIL T4 native bios probes: 792 frames not back`, then `stopped early`). Reverted in 12a28ba. On kasumi first: `notes/px27/kasumi-plant-a.mpx3-tree.out`.
- Planted break B (a rename leaves the old name in place), commit c2364f9: CI run **38151451539**, job mpx3-tree **114505596525**, red 4 min 38 s after it started (`FAIL T1 native bios probes: … rename: a to c 0: a mode 100644 links 1 size 3 blocks 8`, `FAIL T8 … the kernel panicked: PANIC overflow ./tree/tree.lu:1050`, then `stopped early`); @@PLANT_B_JOBS@@. Reverted in ef994df. On kasumi first: `notes/px27/kasumi-plant-b.mpx3-tree.out`.

### Boot counts

@@BOOTS@@

### CI

- Run 38150572440 (plant A's head): 22 jobs green, mpx3-tree red as planted. @@CI@@ The head's own run is in the PR body.

### Drift from the contract, reported

1. **How the item list and the "no call on a guess" rule were read**: §2, under the marked list. The calls item 2 names outright are in and each is in the probe's strace on Linux; `link`, `linkat`, `symlink`, `symlinkat`, `chmod`, `fchmod`, `fchmodat`, `chown`, `fchown`, `utimensat` are in no strace of a program in an image or of lobo and are refused by name.
2. **`writev` to a file is not here**: px24 had not landed it when this lane was cut. When it does, a file is `files.write_target`'s 4 and takes `files.file_write`.
3. **No hard link**, so "inodes with link counts" are 1 for a file and 2 and up for a directory; the count is kept and `drop_file` already waits for it to reach 0.
4. **`execve` runs only the archive's own bytes**: a program copied or written since boot is refused by name, -EACCES.
5. **PAX's `/dev` is fixed** (-EROFS for a name made or removed there; Linux's is writable), and **the largest file is 1 GiB** (-EFBIG; tmpfs's limit is far higher).
6. **A directory lists oldest first** but for reused records, where tmpfs on 7.2.8 lists newest first; no test depends on the order.
7. **The inode table's frames are never given back** (at most 512 frames, for 16,384 inodes); T4 counts them apart.
8. **Dates in `ls -l` are compared by rule**, not held by a fixed clock: the date of a file made in the session is masked on both sides, a date from 1970 is compared as it stands.
9. **The Linux side of `tests/mpx3-tree` needs a container engine** (docker in CI, podman on kasumi) and its container is `--privileged` (mount, chroot, a pid namespace, all inside it); nothing of the host is mounted but a staging directory under `build/`.
10. **Not done, by name**: links of either kind, `chmod`, `chown`, times set by a call, `mmap` of a file, `fallocate`, `statfs`, file locks, `O_SYNC` and its kin, a directory's atime, `/proc` and `/sys` beyond `/proc/self/exe`, AF_UNIX path sockets, SMP.

### What lobo on PAX still lacks from the file side

From this lane's strace of lobo `b256d2e` (`lobo-b256d2e-files.txt`): every call it makes on its logs and its pid file is answered (`mkdir`, `openat` with O_CREAT\|O_TRUNC and O_CREAT\|O_APPEND, `write`, `rename`, `unlink`, `statx` by path and by descriptor, `lseek`). What it opens besides and PAX does not have: `/proc/self/status`, `/proc/self/cgroup`, `/sys/fs/cgroup/cgroup.controllers`, `/sys/fs/cgroup/cpu.max`, `/sys/devices/system/cpu/online` (each -ENOENT on PAX; whether lobo goes on without them was not run), and its control socket, an AF_UNIX path socket in `logs/` (`bind`, and `unlink` of the name), which no lane owns yet. lobo itself was not run on PAX.

### Filed

@@FILED@@

## 5. Done-when

@@DONE@@
