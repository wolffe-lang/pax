# px36 — The file changes (modes, times and links on PAX; the pin to 0.2.28)

Contract: px36's, `sprints/pax/36-the-file-changes/` in wolffe-lang/wolf
(read 2026-10-12), with px27's (`sprints/pax/27-the-writable-tree/`) and
the rules of `sprints/wave-53.md` down to `wave-45.md`. Branch `px36` in
pax, cut from pax trunk `6316c51`. §1–§3 are committed before the first
change to the kernel, the tests, the pins or the images; §2's straces
were taken first, from a working tree whose only change was the
boreutils pin (not committed before this note).

One deliverable: the calls that change a file after it is made —
`fchmodat`, `utimensat`, `linkat`, `symlinkat`, `readlinkat` on written
links, `fchownat` — answered on PAX as Linux answers them; boreutils at
bu22 (`2ab3651`) in the image, with `chmod`, `touch` and `ln` sessions
byte-identical to Linux; and pax's toolchain pin moved to wolf 0.2.28
(own commit) if it changes nothing else.

## 1. Forbidden, absolutely

- No kernel's, libc's or file system's source is read (ruling #22), and
  none is searched for; the refs clone's sparse checkout is never
  widened. Facts come from the Linux man pages (`chmod(2)`,
  `fchmodat(2)`, `chown(2)`, `utimensat(2)`, `link(2)`, `linkat(2)`,
  `symlink(2)`, `symlinkat(2)`, `readlink(2)`, `readlinkat(2)`,
  `open(2)`, `stat(2)`, `statx(2)`, `path_resolution(7)`, `symlink(7)`,
  `inode(7)`), POSIX.1-2024, the uapi headers the sparse checkout holds,
  and black-box runs on Linux's tmpfs: strace of the real binaries, and
  static C programs that print what Linux answers. boreutils, pelt and
  lobo are used as built from their own repositories at their pins,
  never read for how they work; no GNU, busybox, uutils or toybox
  source.
- No syscall or flag is added on a guess: each is in a strace this lane
  took (bu22's binaries, or the probe, a static program in an image);
  everything else is refused with Linux's errno, by name, and counted.
- No word implying filming, recording, viewers or a demo anywhere in
  pax. px25's files (`kernel/procfs`, `kernel/sched`, `kernel/tcp`,
  `kernel/paging`, `tests/mpx4-lobo`, `tools/lobo-*`, `user/lobo*`, and
  its hunks in `kernel/files/files.lu`: `syn_child`, `syn_open`, the
  `/proc` branch of `getdents`) and px35's (`kernel/arp`, `kernel/net`,
  `kernel/virtio`, `kernel/kmain_net.lu`, `tests/mpx4-net`,
  `tests/mpx2-heap`, `tools/net-peer`, `tools/paxtcp.py`,
  `user/unix/unixprobe.c`) are not touched; whichever lands second
  rebases.
- **The utilities under test change files.** `chmod`, `touch`, `ln`,
  `rm` and `mv` run only inside PAX guests and inside throwaway
  containers in which nothing of the host is mounted but scratch under
  `~/lanes/px36/` (and the programs, read-only), never against a host
  path.
- Test binaries for PAX are built in the Ubuntu 24.04 container on
  kasumi (`px13-ubuntu`) or on the CI runner, never with kasumi's own
  glibc. A toolchain pin comes from the release archives by digest,
  never a clone, Homebrew or `~/.local/bin`.
- No `rm` outside `~/lanes/px36/` on any host; no scratch in `/tmp`; no
  `git add -A`; nothing under `~/.claude`; no merge, no tag; no issue
  filed or closed (listed instead); no `2>/dev/null` on a checkout; no
  trailer of any kind on a commit or the PR. No build on nomad-1.
  Nothing is installed anywhere. Another lane's CI run is never
  cancelled.
- No "seen red" without a run id, sha, path or digest. Strict evidence
  (wolf-lang#571): `PAX_REQUIRE_UEFI=1`, `WOLF_PAIRING_REQUIRE_SIBLING=1`,
  full output kept, SKIP counted; `wolf build` exit 2 is a compile
  error; the rows with two processes also under `taskset -c 0-3`.
- kasumi and hasu: remote commands wrapped in `bash` (hasu `env bash`),
  jobs under `setsid` with a pid file, ended by that pid only; a
  container is stopped by its own id only. kasumi's `/home` is at 97%:
  `CARGO_INCREMENTAL=0`, one build directory, pruned as I go.
- A planted break fails fast: the suite it reddens has a deadline
  before the break is planted. If the harness refuses an action, I stop
  and report; I do not route around it.

## 2. Inputs, verified (2026-10-12)

| input | found |
|---|---|
| pax trunk | `6316c51` (px32 merged), at or after the contract's `6316c51` |
| the kernel's pin | wolf 0.2.27 (`5e17eebe…`, pin `0ddda6b7`) / lupin 0.1.50 (`e2867a35…`) by archive digest (`kernel/wolf.pin`) |
| wolf 0.2.28 | tag `v0.2.28` → wolf-lang `f71ece8e`; linux x86-64 archive `3215f321…` as GitHub lists it (to be read again from the download); lupin 0.1.51 → wolf-interp `f72e78d7`, linux x86-64 `d8f62dd1…`. boreutils' `wolf-toolchain.toml` at bu22 names the same two digests |
| `user/boreutils.pin` | `abc59f5` (bu21); boreutils trunk on origin is `2ab36513a0233a0d176010ca09c583bd51f5f5a4` (bu22: wolf 0.2.28 / lupin 0.1.51 / wolf-std `98e1b7b`; `chmod`, `touch`, `ln`, `mkdir -m`, `cp -p`; 39 utilities). Moves in a commit of its own |
| `user/pelt.pin` | `b32bebc` (sh05): not moved |
| the binaries the straces ran | built by pax's own `tools/mkboreutils` and `tools/mkpelt` at the pins, in `px13-ubuntu` on kasumi (glibc 2.39 static): 20 utilities at bu22 (`kasumi:~/lanes/px36/st/bore/sums.txt`; `touch` `6b7c2884…`, `ln` `e57aa550…`, `chmod` `c4584281…`) |
| **how files work today** (read from `kernel/tree` and `kernel/files` at `6316c51`) | px27's tree: inodes with a link count that is 1 for a file and 2 and up for a directory; a mode set at creation (`mode & ~umask`) and never again; three times and a birth time from the wall clock (10 ms steps), set by the tree's own changes only. Refused by name: `link`, `linkat`, `symlink`, `symlinkat`, `mknod`, `mknodat` -EPERM (`R_LINK`); `chmod`, `fchmod`, `fchmodat`, `fchmodat2`, `chown`, `fchown`, `lchown`, `fchownat`, `utimensat`, `utimes`, `utime` -EOPNOTSUPP (`R_META`). `readlink` answers `/proc/self/exe` alone, anything else that exists -EINVAL. A path is walked a directory at a time (`walk_k`); there is no symbolic link to follow, so `AT_SYMLINK_NOFOLLOW` and `O_NOFOLLOW` change nothing but the `/proc/self/exe` case. `tests/mpx3-tree`'s probe holds the twelve refusals to their text (T2) |
| **the list, re-taken** | `notes/px36/straces/` (strace 6.8 on Linux 7.2.8, as root in a throwaway `px13-ubuntu` container, the programs on a tmpfs; `notes/px36/strace-changes.sh`): 57 runs of bu22's `chmod`, `touch`, `ln`, `mkdir -m`, `cp -p` and of `ls -l`, `stat`, `readlink`, `cat`, `rm`, `mv` meeting links. The marked list is below |
| kasumi | QEMU 11.1.1, TCG only; `px13-ubuntu` (`ad896450…`); `/home` 97% (35 GB free); load average about 27 on 16 cpus (other lanes) |
| hasu | KVM through `nix-shell -p qemu` |

### The marked list

What each call is on PAX at `6316c51`: **right**, **wrong** (present,
another answer), **absent** (-ENOSYS).

| call, as straced | who | at `6316c51` |
|---|---|---|
| `chmod(path, mode)` (90): `0600`, `0700`, `0644`, `04755`, `01777`; through a symbolic link it changes the target | `chmod` (octal, symbolic, `-R`, `-v`, `-c`, `--reference`), `mkdir -m` (a set-id or sticky bit: `mkdir` then `chmod`), `cp -p` | wrong (-EOPNOTSUPP) |
| `utimensat(AT_FDCWD, path, times, 0)`: both times given to the nanosecond, `[UTIME_NOW, UTIME_NOW]`, `[t, UTIME_OMIT]`, `[UTIME_OMIT, t]`; -ENOENT for a missing name | `touch` (new, existing, `-t`, `-d`, `-a`, `-m`, `-r`, a directory), `cp -p` (each file and directory, the source's nanoseconds) | wrong (-EOPNOTSUPP) |
| `utimensat(AT_FDCWD, path, times, AT_SYMLINK_NOFOLLOW)`: a link's own times | `touch -h` | wrong |
| `linkat(AT_FDCWD, old, AT_FDCWD, new, 0)`: 0; -EEXIST; a symbolic link linked as itself (`ln -P`) | `ln`, `ln -f` (to a temporary name, then `rename` over), `ln -T`, `ln -L` (the target resolved by the utility, `readlink` and `getcwd`), `ln f dir` | wrong (-EPERM) |
| `symlink(target, path)` (88): 0, a dangling target | `ln -s`, `-sf` (a temporary name, then `rename`), `-sfn`, `-sr`, `-sv`, `cp -P`, `cp -r` of a link | wrong (-EPERM) |
| `readlink(path, buf, 256)` (89): the target's bytes | `ls -l`, `stat`, `readlink`, `ln -L`, `ln -r`, `cp -P` | wrong (-EINVAL) |
| `statx(…, AT_SYMLINK_NOFOLLOW)` of a link: `S_IFLNK\|0777`, size the target's length, blocks 0; `statx` without the flag: the target's | `ls -l`, `stat`, `chmod`, `ln`, `cp` | wrong (no link can exist) |
| `openat(…, O_RDONLY\|O_CLOEXEC)` through a link, and of `st/a/b/x` where `st` is a link to a directory | `cat` | wrong (no link can exist) |
| `openat(…, O_WRONLY\|O_CREAT\|O_APPEND\|O_CLOEXEC, 0666)` | `touch` | right |
| `openat(…, O_RDWR\|O_CREAT\|O_EXCL\|O_CLOEXEC, mode)` with the source's mode (0644, 0700) | `cp -p`, `cp -r` | right |
| `mkdir(path, mode)` with `0700`, `0757`, `0711` | `mkdir -m`, `mkdir -p -m`, `cp -r` | right |
| `umask(0)`, `umask(022)` | `mkdir -m`, `cp -p` | right |
| `rename(tmp, name)`, `unlink(name)` of a link | `ln -f`, `ln -sf`, `mv`, `rm` | right for files; a link is a new case |
| `getdents64` of a directory with links (`d_type` DT_LNK) | `ls -l`, `chmod -R`, `cp -r` | wrong (no link can exist) |
| `getcwd` | `ln -L` | right |

Not in any strace of bu22, so **added only as the probe asks**:
`fchmod`, `fchmodat`, `fchmodat2`, `symlinkat`, `readlinkat` of a
written link, `linkat` with `AT_SYMLINK_FOLLOW` or `AT_EMPTY_PATH`,
`chown`, `fchown`, `lchown`, `fchownat`, `utimensat` on a descriptor
(`futimens`). **How this lane reads the contract here** (px27's
reading): the contract names `fchmodat`, `utimensat`, `linkat`,
`symlinkat`, `readlinkat` and `fchownat` outright, so each is added and
held to Linux by the probe, a static binary in an image whose strace on
Linux is kept; `utime` (132), `utimes` (235), `futimesat` (261),
`mknod` and `mknodat` are in no strace and named by no item, and stay
as they are (refused by name, or -ENOSYS). bu22 itself refuses
`cp -p`'s owner by name before any call, so no `chown` appears in its
straces.

## 3. Prediction (committed before the first change)

### Q1. The pin to 0.2.28 (one commit, before any kernel change)

- `kernel/wolf.pin` to wolf 0.2.28 (`3215f321…`, pin `f71ece8e`) and
  lupin 0.1.51 (`d8f62dd1…`), the tour's banner (`wolf 0.2.28`) and the
  README's and CHANGELOG's words in the same commit, so CI never sees
  the pin alone.
- Every kernel builds with no diagnostic under 0.2.28 (r33 is the
  soundness release: #660, #665 and #678's direct half refuse new
  shapes with E1010; the kernel has no channel, no `spawn` and no
  region-built string handed to a call that outlives it).
- Bytes: the native kernels identical once stripped of debug and
  build-id unless `libwolf_rt_none.a` moved; the tour's two kernels move
  one loaded byte (the banner). Predicted: under ten kernels' loaded
  bytes move, and every verdict is unchanged: the same PASS count in
  every suite of a kasumi gauntlet at the trunk and at the pin, and
  `tests/mkw` step 6 names lupin 0.1.51.

### Q2. The boreutils pin to bu22 (one commit)

- 39 utilities, all static; the image of `tests/mpx3-tree`'s shell
  gains `chmod`, `touch` and `ln` (about 40 MB more initramfs). Every
  boreutils binary's bytes move (wolf 0.2.28, std `98e1b7b`), so every
  transcript that prints a size under `/bin` moves: `tests/mpx3-shell`'s
  `ls -l /bin` transcripts (`shell-howl`, `shell-plumb`, `shell-long`),
  regenerated from Linux as px27 did; no verdict moves.

### Q3. Hard links

- `linkat(olddirfd, old, newdirfd, new, flags)` (and `link`): a second
  record leading to the same inode; the count goes up, the inode's ctime
  and the new directory's mtime and ctime move. `flags` 0 does not
  follow a last link in `old` (a link to the link itself, as `ln -P`
  showed and `link(2)` says of Linux); `AT_SYMLINK_FOLLOW` follows it;
  `AT_EMPTY_PATH` links the descriptor's file (root has the capability)
  and -ENOENT for a file whose count is 0 (predicted); any other flag
  -EINVAL. A directory -EPERM (Linux's answer, not a refusal by name);
  a name that exists -EEXIST (also a dangling link: not followed); a
  trailing `/` on `new` -ENOENT (predicted); across `/dev` -EXDEV.
- `unlink` of one name drops the count by one; the inode, its bytes and
  every other name live on; the frames go back when the last name and
  the last descriptor are gone (px27's rule, now with counts above 1).
  `rename` of one name over another name of the same inode does nothing
  and answers 0 (`rename(2)`; px27's code already does that).
- `execve` of a second name of an initramfs program runs it (the inode
  is still the archive's bytes); `/proc/self/exe` answers the archive's
  path, which is what Linux answers too (the first name)… predicted;
  the probe checks it.

### Q4. Symbolic links

- A link is an inode of its own: `S_IFLNK|0777` (`symlink(7)`: the mode
  is ignored), one name, its bytes the target's (held as a file's: one
  frame for any target up to 4095 bytes, the cap counting it), its size
  the target's length; `st_blocks` as tmpfs answers (0 for a short
  target, measured; predicted 8 from a threshold the probe finds,
  guessed at 128 bytes, else named drift). `symlink` of an empty target
  -ENOENT; a target of 4096 bytes or more -ENAMETOOLONG; a name that
  exists -EEXIST (never followed); in `/dev` refused by name, -EROFS.
- **Resolution** (`path_resolution(7)`): a link met before the last
  component is always followed; the last is followed or not as the
  call says. The path in `pax_kbuf` is rewritten in place — the target
  first, then what was left of the path — and the walk starts again
  from the directory the link is in (or `/` for an absolute target); a
  new length past PATH_MAX is -ENAMETOOLONG. At most 40 links in one
  resolution: the 41st is -ELOOP, as is a link to itself. A trailing
  `/` forces the last one to be followed. `..` after a link to a
  directory goes to that directory's parent (physical, as on Linux).
- **Followed at the end**: `open` (but `O_NOFOLLOW` -ELOOP on a link,
  and `O_CREAT|O_EXCL` -EEXIST on one, dangling or not; `O_CREAT` alone
  through a dangling link makes the file it names), `stat`, `statx` and
  `newfstatat` without `AT_SYMLINK_NOFOLLOW`, `chmod`, `chown`,
  `utimensat` without the flag, `truncate`, `chdir`, `execve`,
  `access`/`faccessat`. **Not followed**: `lstat` and the flag,
  `readlink`, `unlink` (removes the link), `rmdir` (-ENOTDIR), `rename`
  (moves the link), `mkdir` and `symlink` (-EEXIST), `linkat`'s new
  name, `lchown`.
- `readlink`/`readlinkat`: at most `size` bytes of the target, no NUL,
  the count; `size` 0 -EINVAL; what is no link -EINVAL (px26's
  `/proc/self/exe` kept as it is). `getdents64` gives a link `d_type`
  10 (DT_LNK); `ls -l` prints `lrwxrwxrwx … name -> target`.
- `fchmodat2(…, AT_SYMLINK_NOFOLLOW)` on a link -EOPNOTSUPP (tmpfs
  keeps no mode for a link; predicted from `fchmodat(2)`'s "not
  implemented" for the flag, measured before it is relied on); on what
  is no link it changes the mode.

### Q5. Modes

- `chmod`, `fchmod`, `fchmodat` (and `fchmodat2` with flags 0) set the
  twelve permission bits (`mode & 07777`), keep the type, move ctime
  and nothing else; root keeps a set-group-ID bit it asks for (no group
  rule applies). A `write` by root to a set-user-ID file leaves the bit
  (root has CAP_FSETID; predicted, measured). `chmod` of a link changes
  its target. `/dev` and `/proc` are fixed: refused by name, -EROFS
  (Linux lets root change `/dev/null`'s mode: named drift).
- `execve` and `access(X_OK)` read the bits as they are now: `chmod -x`
  makes a program -EACCES, `chmod +x` makes it runnable again (still
  only the archive's own bytes, px27's rule).

### Q6. Times, to the nanosecond

- `utimensat(dirfd, path, times, flags)`: `times` NULL sets both to
  now; each `timespec` is a time to the nanosecond, `UTIME_NOW` (now),
  or `UTIME_OMIT` (left alone); a `tv_nsec` that is none of these and
  not below 10⁹ -EINVAL; ctime moves to now unless both are
  `UTIME_OMIT` (then 0 and nothing moves, predicted). `path` NULL
  (`futimens`, as glibc makes it) names the descriptor; `flags`
  `AT_SYMLINK_NOFOLLOW` sets a link's own times; any other flag
  -EINVAL. The `stat` that follows answers the same seconds and
  nanoseconds, whatever they were; "now" is the kernel's wall clock (the
  CMOS reading at boot plus 10 ms ticks), the same clock
  `clock_gettime(CLOCK_REALTIME)` reads, so a probe's `before ≤ time ≤
  after` holds on both.
- A time is held as signed nanoseconds since the epoch in a 64-bit word
  (1677 to 2262). A time before 1970 is kept (`touch -t 196001010000`);
  one outside that range is clamped to it (predicted; tmpfs's own range
  is measured by the probe and any difference named drift).

### Q7. Owners

- PAX has one user, root. `chown`, `fchown`, `lchown`, `fchownat`
  with each of owner and group 0 or -1 answer 0 as root's do on Linux:
  ctime moves; a set-user-ID or set-group-ID bit on an executable file
  is cleared when an id is given (`chown(2)`: "since Linux 2.2.13, root
  is treated like other users"), and kept when both are -1 (predicted;
  measured). Any other id is **refused by name, -EINVAL**: POSIX's errno
  for "an owner or group ID that is not a value supported by the
  implementation" (`chown` in POSIX.1-2024), where Linux as root would
  answer 0 and keep the id: named drift. `fchownat` flags
  `AT_SYMLINK_NOFOLLOW` and `AT_EMPTY_PATH`; others -EINVAL.

### Q8. Calls added, refusals, and the count

- **New numbers**: `chmod` (90), `fchmod` (91), `fchmodat` (268),
  `utimensat` (280), `link` (86), `linkat` (265), `symlink` (88),
  `symlinkat` (266), `chown` (92), `fchown` (93), `lchown` (94),
  `fchownat` (260); `fchmodat2` (452) if glibc 2.39 asks it; `readlink`
  (89) and `readlinkat` (267) extended. 12 numbers ± 1.
- **Still refused by name**: `mknod`, `mknodat` -EPERM; `utime`,
  `utimes` -EOPNOTSUPP (in no strace); a link, a mode or a time in
  `/dev` -EROFS; an owner that is not root -EINVAL.
- `tests/mpx3-tree`'s twelve refusals become six (`O_SYNC`,
  `O_TMPFILE`, a file made in `/dev`, a directory made in `/dev`,
  `RENAME_NOREPLACE`, the `execve` of a program written since boot):
  the `~refused` line's link, symlink, chmod, chown (0, 0) and
  utimensat answer 0 on both, and a hard link to a directory is -EPERM
  on both with no `refused:` line (it was one of the twelve). The new
  probe section's own refusals (an owner of 1000, a link and a mode in
  `/dev`) are counted on top: **6 + 4 = 10** predicted.

### Q9. Numbers

- Frames at the prompt: the shell's image with bu22's 20 programs; the
  tree's own frames at boot as px27's (6), the kernel's image a few
  pages larger (predicted under 10).
- **The soak**: px27's 10,000 rounds gain, per round, a hard link, a
  symbolic link, a `chmod` and a `utimensat`, and the two new names
  removed: frames, inodes and the heap the same after as before; the
  census, one line every 2500th file name removed, from 4 lines to 12
  (three names removed a round), all equal.
- At least 100 KVM boots on hasu for the lane's suites, all green.

### Q10. What moves, and what fails first

- Every kernel's bytes (each links `kernel/files`), so every ISO.
- `tests/mpx3-tree`: the probe's new lines (links, symbolic links,
  modes, times, owners), T2's refusal lines and count, T5's census
  count, a new typed session `shell-changes` (serial and PS/2, both
  tiers, BIOS and UEFI) with `chmod`, `touch`, `ln`, `mkdir -m`, `cp -p`,
  `readlink`, `ls -l` and `cat` through links; `ls -l`'s date masking
  learns the `l` type, and a date `touch -t` set is compared as it
  stands. `tests/mpx3-shell`: the transcripts that list `/bin`.
- Other suites' verdicts do not move.
- **On trunk's kernel** the new session fails at its first `chmod`
  (`chmod: cannot change permissions of 'f': Operation not supported`)
  and the probe's first new line; with bu22 in the image the old
  session still holds.
- **Planted breaks**, each its own commit and CI run, each failing
  inside one boot's deadline: (A) `unlink` of one name of a file with
  two frees the inode — the probe's links line and T4 (and likely a
  panic), nothing else; (B) `utimensat` keeps whole seconds only — the
  probe's times line and the session's `cp -p` line, nothing else.

## 3a. The prediction, scored

§1–§3 above are as committed (`46f5c0d`), before any change. Scored
here, item by item; "the probe" is `user/elf/tree.c` at `b63c2d6`,
"Linux" a throwaway `px13-ubuntu` container on kasumi (Linux 7.2.8, as
the container's root, the root a tmpfs), "PAX" the same binary as the
first program (`notes/px36/session-probes.{linux,pax}.txt`).

| # | predicted | measured | verdict |
|---|---|---|---|
| Q1 | the pin its own commit with the banner; every kernel builds with no diagnostic; under ten kernels' loaded bytes move; every verdict unchanged | PIN_ELFCMP | PIN_VERDICT |
| Q2 | 39 utilities; the shell image gains `chmod`, `touch`, `ln`; `tests/mpx3-shell`'s `/bin` transcripts move | 39 at bu22, built static in `px13-ubuntu` (`kasumi:~/lanes/px36/st/bore/sums.txt`); `tests/mpx3-tree`'s shell image gains the three. **`tests/mpx3-shell` did not move**: its transcripts mask every size under `/bin` (`SIZE`, `BLOCKS`), and its own image keeps bu21's seventeen (the three join `mpx3-tree`'s shell image only) | wrong on mpx3-shell |
| Q3 | hard links: a record to the same inode; flags 0 does not follow, AT_SYMLINK_FOLLOW does, AT_EMPTY_PATH links a descriptor's file and -ENOENT for one with no name; a directory -EPERM; -EEXIST; a new name with a trailing `/` -ENOENT; -EXDEV across `/dev`; ctime moves; frames back at the last name and descriptor; rename between two names of one file 0; a second name of an initramfs program runs | **right, all of it** (`link:` lines on both: `again -17; a missing name -2; into a missing directory -2; a new name with a trailing slash -2, an old one -20; through a file -20; a flag -22; into /dev -18; out of /dev -18`; `AT_EMPTY_PATH of a file with no name -2; of one with a name 0`; `/bin/tree linked 0, run by its second name: status 7`); 101 names on one file; T4 holds the frames. Not predicted: an old name with a trailing `/` on a file is -ENOTDIR. `/proc/self/exe` after a run by the second name was not printed (Linux names the path the program was run by, PAX the archive's: left out of the probe, named in §5) | right |
| Q4 | a link S_IFLNK\|0777 holding its target as a file's bytes; blocks 0 below a threshold "guessed at 128 bytes", 8 from it; empty -ENOENT; 4096 -ENAMETOOLONG; -EEXIST never followed; `/dev` -EROFS by name; the walk follows a link before the last component, the last as the call says, 40 at most, a trailing `/` forces it, `..` physical; the lists of calls that follow and do not; `readlink` size 0 -EINVAL; DT_LNK; `fchmodat2` NOFOLLOW on a link -EOPNOTSUPP | **right** (`symlink:` lines on both; `blocks by the target's length 1:0 59:0 60:0 61:0 127:0 128:8 …`: the guess was the threshold; `a chain: 39 links end, 40 end, 41 -40`; `.. after one is the target's parent 1`; `fchmodat with AT_SYMLINK_NOFOLLOW on a link -95`, through glibc 2.39's `fchmodat2`, 452). **Not predicted**: `O_NOFOLLOW\|O_DIRECTORY` on a link answers -ENOTDIR, not -ELOOP; a walk through a link and a `readlink` of it move the link's atime by relatime's rule (`its atime moved to now by the walk through it 1`, `a readlink of a link whose atime is before its mtime moves it to now 1`); `readlink` of `s/` is -ENOTDIR (the trailing `/` follows it to a file) | right, three answers not predicted |
| Q5 | `chmod`, `fchmod`, `fchmodat`, `fchmodat2` set the twelve bits, ctime moves, mtime not; through a link the target; `/dev` -EROFS by name (named drift); a write by root keeps a set-user-ID bit; the bits decide `execve` and X_OK | **right** but one: `mode:` lines on both (`07777 0 mode 107777`; `with type bits 0 mode 100644`; `/bin/tree 0644 0: run 113, X_OK -13; 0100 0: run 7, X_OK 0`). **The write by root clears both set-ID bits in kasumi's container** (`06755 and a write by root: mode 100755`), where PAX keeps them: the container's root is root in a user namespace and does not hold CAP_FSETID over the tmpfs as `capabilities(7)` says a privileged process does. PAX keeps the bits (every process is root with every capability); the line is `~`, held to PAX's answer by T2. CI's runner (docker as the host's root) answers RUNNER_SETID | right on PAX; the container differs |
| Q6 | `utimensat` to the nanosecond, UTIME_NOW the kernel clock, UTIME_OMIT, NULL both now, ctime now unless both OMIT, -EINVAL for a bad `tv_nsec` and a flag, NOFOLLOW sets a link's own, `futimens`; before 1970 kept; past 2262 clamped (named drift) | **right, all of it** (`time:` lines on both: `atime 1.123456789 mtime 2.987654321`; `both UTIME_OMIT 0 … ctime moved 0`; `before 1970 0: atime -2208988800.000000005 mtime -1.999999999`). The year 3000: tmpfs keeps `32503680000.000000001`, PAX answers `9223372036.854775807` (`~time`, T2), as `utimensat(2)` allows ("the greatest value supported by the filesystem that is not greater than the specified time") | right |
| Q7 | owner and group 0 or -1: 0, ctime moves, set-ID bits of an executable file cleared when an id is given, **kept when both are -1**; any other id refused by name -EINVAL (named drift) | **wrong on -1 -1**: Linux clears them whatever the ids (`06755 and -1 -1 0: mode 100755`); a set-group-ID bit without group execute is kept (`06745 and 0 -1 0: mode 102745`), and a directory's is kept (`42755`). Implemented as measured. The rest right (`~owner: chown 1000 1000 -22: uid 0` on PAX, `0: uid 1000` on Linux) | half |
| Q8 | 12 ± 1 new numbers; mknod, mknodat, utime, utimes still refused; T2's twelve become six, plus four of the new section: ten | **13**: 86, 88, 90, 91, 92, 93, 94, 260, 265, 266, 268, 280, 452 (89 and 267 extended); each in the probe's strace on Linux (`notes/px36/straces/tree-probe.calls.txt`) or bu22's. **Ten refusals, ten counted** (T2), as predicted | right |
| Q9 | the tree's frames at boot 6; the kernel's image under 10 pages larger; the soak flat with 12 census lines; ≥ 100 KVM boots | the tree's own 6 (`tree: frames … (6 when made)`); the kernel: **8 frames** fewer free before the first program than the pin's kernel with the same probe image (`62983` against `62975`); **the census stays at 4 lines, not 12**: the soak was written so that one `unlink` a round removes the last name (the link renamed over the first name and that over the second), so the census still counts one name a round and its lines stay comparable (`4 census lines, all 'frames held 7, inodes 7, frames free 62135'`); KVM_BOOTS | right but the census count (a change of design, not of measurement) |
| Q10 | every ISO moves; mpx3-tree's lines, T2, T5's count, the new session (serial and PS/2, both tiers, BIOS and UEFI); other suites unmoved; on the pin's kernel the session fails at its first `chmod`; plant A reddens the links line and T4 (likely a panic); plant B the times line and the session's `cp -p` line | the session as planned (111 lines byte-identical on all eight legs). **On the pin's kernel** (`b25a5fe`'s `kernel/` and `boot/` under the head's tests): the session's first lines are `chmod: changing permissions of 'f': Operation not supported` and the probe's first new line differs (`kasumi-red-*`), as predicted. T5's count did not move (above). Plants: PLANT_A; PLANT_B | PLANT_VERDICT |
