# px63 — virtio-blk and ext2: a disk that outlives the boot

Crawl 54, Opus 5.5. Contract `sprints/pax/63-virtio-blk-and-ext2`. PR
pax#132. The prediction was committed first, `afb7ff7a`
(`notes/px63/prediction.txt`). Branch `px63` from `origin/px62`
`97eda050`, which became trunk when px62 merged (the rebase onto trunk
was a no-op).

## 1. Forbidden, and what was read

No Linux kernel source (`fs/ext2`, `fs/ext4`, `drivers/block` included),
no other kernel's, no musl's, glibc's, QEMU's or e2fsprogs' source, and
no file-system driver from anywhere. What was read is in
`docs/SOURCES.md` (px63): the kernel's own documentation of the on-disk
layout (`Documentation/filesystems/ext2.rst` and the
`Documentation/filesystems/ext4/` pages for the superblock, the group
descriptors, the bitmaps, the inode table, inodes and their extra time
words, the block map, directories and the special inodes), the virtio
1.2 specification's §5.2 (the block device) beside the §2 and §4.1 px20
read, man pages (`fstab(5)`, `mount(8)`, `statfs(2)`, `fsync(2)`,
`sync(2)`, `syncfs(2)`, `reboot(2)`, `msync(2)`, `statvfs(3)`,
`mke2fs(8)`, `e2fsck(8)`, `debugfs(8)`), the uapi headers in the refs
clone for numbers only (`linux/magic.h`, `asm-generic/statfs.h`,
`linux/reboot.h`, `syscall_64.tbl`), and the ICH9 data sheet's reset
control register. e2fsprogs 1.47.0 (`mkfs.ext2`, `e2fsck -fn`,
`debugfs`) ran from a container pinned by digest, and Linux 7.2.8 ran
on QEMU with the image as its disk: black boxes, never read. Builds in
`px13-ubuntu` (and `px57-rust` for the playground's lupin) on kasumi;
QEMU under `taskset -c 0-3`, `ulimit -c 0`, `setsid -f` with pid files;
nothing installed on any host; nothing built on nomad-1. No merge, tag,
issue filed or closed; no filming words.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `97eda050` (px62, merged during the lane: PR #130); the contract's `c0d394ee` is px61's |
| `kernel/virtio` | px20's transport, a window of BARs per device since px30 (`use_words`: 0-3 the network's, 4-7 sound's); 8-11 are the disk's now |
| how a device completes | net by INTx and its thread; sound's control queue polled. The disk is polled, as sound is: a system call runs with interrupts off from entry to return, so the request is asked and answered inside it |
| `kernel/tree` | inodes as 16-word records, indices 0 to 16,383; kernel/files names a file by its index (T_INO); px62's page cache is the tree's own frames under each record (`page`) |
| `docs/MAP.md` | does not exist; `docs/BOOT.md` and the modules' headers stand in (the disk is described in `docs/BOOT.md`) |
| e2fsprogs | 1.47.0 on kasumi's host (not used), 1.47.0-2.4~exp1ubuntu4.1 in `docker.io/library/ubuntu@sha256:534baea6…` (Ubuntu 24.04, the CI runner's release): `tools/e2fs` runs that image's, never a host's |
| the Linux guest | kasumi's 7.2.8-1-cachyos: virtio_blk and ext4 built in, ext2 mounted by ext4 (CONFIG_EXT4_USE_FOR_EXT2), read black-box from `modules.builtin`; CI's runner kernel is root's to read, so CI holds PAX to the record made on kasumi (`tests/mpx6-ext2.d/linux/`) |
| pins at the head | wolf 0.2.34 (kernel), pelt `57ffef96`, boreutils `12de639`, lope `bc38867`, aspen `476edee`, yew `77c1083`, lupin 0.1.55: none moved |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| virtio-blk needs about 450 kernel lines beside px20's transport (kernel/vblk ~300 with its header, kernel/block ~350), fewer than 20 changed in kernel/virtio | kernel/vblk 562 lines (144 of them comments), kernel/block 726 (131 comments; the buffer cache, its hash and clock, the device table, the books); kernel/virtio +27 (a 32- and a 64-bit configuration read with config_generation's retry) | wrong: twice the size; the transport's share right in kind, 7 lines over |
| completion polled, not px20's interrupt | polled: `vblk.wait` spins on the used ring, bounded, a lost request named | right |
| the tree's inode table cannot hold an ext2 number; a mapping: a record per ext2 inode in use, the number beside it, a lookup from (volume, number), a record nobody holds given back | so: a side table beside the inode table (the ext2 number, the volume, the mount point it covers, a generation stamp), a hash by (volume, number), records evicted when unheld past VOL_KEEP and not looked up in the current system call | right |
| the first `e2fsck` complaint names the group counts (pass 5's "Free blocks count wrong for group #0") | no `e2fsck` run of PAX's own disk ever found a fault, first boot on (`kmain_console`'s write session, `notes/px63/writerows.sh`); the bitmap plant's: `Block bitmap differences: +(1040--1044) …` first, then `Free blocks count wrong for group #0` (run 39928403889) | wrong: no complaint came; pass 5 names the bitmap before the counts |
| the reboot row about 30 s on kasumi (two ~12 s boots and the host's checks), about 60 s on CI | kasumi: the row 3.5 s (`rebootrow.sh`: the first boot 0.92 s to the reset, the second 1.9 s to the halt, e2fsck and debugfs between); in the suite (qemu-run and qemu-halt's own start-up counted) 3.1 s and 4.2 s; CI: 8.4 s for the row (plant run 39928403889, 09:02:01.27 to 09:02:09.67) | wrong: 8 times too slow a guess (a kmain_console boot is under a second, not 12) |
| the 100 MiB file read back in under 20 s under TCG | the whole read boot 9.1 s on kasumi (51,662 requests, 413,290 sectors, the 100 MiB file and 496 other lines) | right |
| write-through about 3 times write-back for a session of small writes, by blocks written | 17,580 writes (140,640 sectors) against 1,590 (12,720): 11 times; the boot 4.13 s against 3.72 s (R-px63-3) | wrong: 11x, not 3x |
| the existing suites unchanged: no disk, no device, no new line | the PR's first run (39927513570, 42 suites): 41 green; mpx4-lobo's R10 flat red by 16 kB (§8) | see §8 |

Two things the first boots taught, measured, not predicted:

- **debugfs writes the superblock's write time at its close.** Two
  `tools/mkdisk` runs a minute apart differed in one byte, offset 1072
  (`s_wtime`); mkfs's E2FSPROGS_FAKE_TIME, given to debugfs too, makes
  one disk's bytes (`19b46860`), checked on every run since.
- **CI's TCG is two to four times slower than kasumi's.** The tree
  comparison held each session-made time to the same distance from each
  session's clock within a second; on the runner a step 0.40 s into
  Linux's recorded session was 1.51 s into PAX's. Times are now held to
  each session's own window (its first `~clock:` to its last) and the
  distances scaled to the reference's length (`35a48f82`).

## 4. What was built

**kernel/vblk** brings up a virtio block device (1af4:1001 transitional
or 1af4:1042) on the transport's windows 8-11: features VERSION_1, and
FLUSH, RO, BLK_SIZE, SEG_MAX when offered; one queue of 64 descriptors,
16 request slots of three descriptors (header, data, status), polled
completion, INTx left off. A request is kernel/block's record (op,
sector, count, frame, status).

**kernel/block** is the disks: a device table (`vda`, 254:0, as Linux
numbers it), `rw` with every refusal by name (past the end, a write to
a read-only disk, a count over 8 sectors), `flush`, and a buffer cache
of 512 block buffers with a 512-chain hash and clock eviction; a buffer
is good until the next `get` or `fresh`; dirty buffers wait for `sync`
under write-back and go out at once under write-through. The books
(`block: vda: R reads (S sectors), W writes, F flushes, E errors, X
refused; cache …`) close every boot.

**kernel/ext2** reads and writes an ext2 volume: the superblock
(revision 0 and 1, blocks of 1, 2 or 4 KiB; INCOMPAT FILETYPE only,
anything else refused by name; an unknown RO_COMPAT makes the mount
read-only, by name), groups, both bitmaps and the free counts, inodes
(owners' high 16 bits, the extra time words with their epoch bits and
nanoseconds, `i_extra_isize` 32 for a new inode, LARGE_FILE), the block
map through the single, double and triple indirect blocks, truncation,
holes, directories (linear; a modified directory's INDEX_FL cleared, so
an htree is never left stale), fast and slow symbolic links. A
read-write mount marks the volume in use and its unmount marks it clean,
so `e2fsck -fn` and Linux accept it.

**kernel/tree's second store.** A record may stand for a volume's
inode: the tree's operations are one interface over both (header, "Two
stores"). The record keeps what is the memory's (its holders, the
parent, a FIFO's words, the frames a mapping filled: px62's page cache,
reused) and mirrors the mode and link count; size, times, owner, blocks,
bytes and entries are the volume's, asked each time. A mount point's
lookup answers the volume's root, whose parent is the point's parent;
EBUSY for the point, EXDEV between stores, EROFS on a read-only mount.

**kernel/fstab** reads the initramfs's `/etc/fstab` before the first
program and mounts each line (R-px63-1); it starts the flusher thread
for write-back volumes (R-px63-3). **kernel/files** answers a volume's
numbers in `stat`, `getdents` (a directory's atime moved as Linux's
relatime moves it) and `statfs`; `fsync`, `fdatasync`, `syncfs`, `sync`
write it. **kernel/user** serves root's `reboot(2)`: every volume
written and marked clean, then the reset (0xcf9, then the 8042).
**kernel/vm** writes a shared writable mapping's pages at `msync(MS_SYNC)`.

Tools: `tools/e2fs` (e2fsprogs from the pinned image), `tools/mkdisk`
(a reproducible image: empty, `--home`, or a tree by `debugfs -w`
commands in sorted order, every attribute set by `sif`, `e2fsck -fn`
clean), `tools/e2tree` (an image's tree with every field and each
file's sha256), `tools/linux-blk` (Linux on QEMU with the image as
`/dev/vda`), `tools/mkdiskprobe` (`user/elf/disk.c`, the probe, and
`user/elf/reboot.S`, `/bin/reboot`), `tools/blk-pattern`. Tests:
`tests/mpx6-blk` (K0-K8), `tests/mpx6-ext2` (E0-E9). `user/fstab`.

## 5. Rulings asked (recommended, implemented, not decided)

- **R-px63-1, the mount table and where `/home` is mounted.**
  Recommendation: **fstab(5)'s file, read by the kernel before the first
  program**: `/etc/fstab` in the initramfs (`user/fstab`: `/dev/vda
  /home ext2 defaults 0 2`), each line mounted by kernel/fstab with
  mount(8)'s option names (`ro`, `rw`, `sync`, `async`, `nofail`;
  `relatime`, `nosuid`, `nodev`, `noexec` named and not acted on;
  `LABEL=` and `UUID=` refused by name), `/home` on the disk and `/`
  the memory's. PAX's init is the kernel's run list and no PAX program
  mounts, so the kernel does what a distribution's init does with the
  same file; when PAX has an init of its own and `mount(2)` for root,
  the same file moves to it unchanged. Against a kernel command-line
  `home=` (Limine's cmdline): the table would live in the boot
  configuration, apart from the image's files, and say less. Against
  serving `mount(2)` now and a shell line in `/etc/pax-run`: it needs
  root's mount semantics (propagation, flags, `umount2`) this lane does
  not measure. Measured: a disk that is not there leaves `/home` the
  tree's, said once (`fstab: /dev/vda for /home: no such disk`); the
  reboot row's image reads `user/fstab` itself, comments and tabs.
- **R-px63-2, what `/` on disk would take (a report).** (1) The root
  record: the tree's root becomes a volume's root at boot, the
  initramfs's files then a second store or gone; kernel/files' `/`
  lookups, `chroot`'s root check and `/proc`, `/sys`, `/dev` as mount
  points of the memory over the disk. (2) The image's programs on the
  disk: px56's exec from the tree already maps a file's frames, and a
  volume file's frames come through the same `page`, so exec needs no
  new path, but `/bin` must be installed onto the disk: an installer
  (P6), which needs a partition table (GPT: an EFI system partition
  for Limine and a Linux partition for ext2), which needs kernel/block
  to read one and to offset a partition's sectors. (3) A first boot's
  `/etc` (passwd, group, fstab) and `/dev` nodes written by that
  installer. (4) Durability the memory never needed: a crash between
  the flusher's writes leaves the volume marked in use; `e2fsck` on the
  host repairs it, and PAX has no `fsck` (a journal, ext3's, is the
  remedy and a lane of its own). (5) `mount(2)` for root, and `umount`
  at the halt in order. Recommendation: a lane after the installer's
  partition table, not before; issues listed in §11.
- **R-px63-3, the write-back policy.** Recommendation: **write-back by
  default, flushed every 5 seconds by a kernel thread, and at `fsync`,
  `fdatasync`, `syncfs`, `sync`, `msync(MS_SYNC)`, the halt and root's
  `reboot`**; `sync` in a line's options for write-through. Measured on
  the write session (`notes/px63/kasumi-measurements.out`, the same
  kernel, the same disk, only the option changed): write-back 1,590
  writes, 12,720 sectors, 3.72 s; write-through 17,580 writes, 140,640
  sectors, 4.13 s; both disks `e2fsck -fn` clean, the same tree. Cost
  named: a machine switched off without a halt loses up to 5 s of
  writes (the flusher's interval, Linux's default writeback interval)
  and leaves the volume marked in use. The flusher writes with
  interrupts off, as a system call does, so no call sees a half-written
  volume.

## 6. Witnesses and measurements

**tests/mpx6-blk** (kmain_blk): a pattern (`((s << 32) | w) ^ PAX_DISK`)
written across a 16 MiB + 3 sector image in 4,097 requests, flushed and
read back, 0 differ; the host reads the image (`tools/blk-pattern`):
32,771 sectors, 0 differ; read-only (`readonly=on`: RO taken, every
write refused by name, the image's sha256 unchanged); past the end
refused by name before it is asked, the last sector right; no disk: no
`blk:` line.

**tests/mpx6-ext2**, every row on kasumi's four legs (native and release,
BIOS and UEFI: `notes/px63/kasumi-ext2-four-legs.out`):

| row | what | kasumi native BIOS |
|---|---|---|
| E0 | three disks made by `tools/mkdisk`, each the recorded sha256 (fixture `c8e475b7…`, write `15adbd4b…`, home `495f938d…`); the Linux side | live 7.2.8 or the record |
| E1 | one `blk:` line; `fstab: /dev/vda on <dir>: …`; `…; clean, mount N; …`; no fault line, no refusal | each boot |
| E2 | the read session byte-identical to Linux's: `ls -l`, `ls -la`, `stat`, `readlink`, `cat`, `wc -c`, the probe's fields, statfs | 497 lines, `5bed8292…` |
| E3 | the 100 MiB file's sum on both sides; debugfs's dump of it is the generator's sha256 | `fnv 073397faab819fc1`, `b942aba3…` |
| E4 | the write session byte-identical (`~` lines apart) | 94 lines |
| E5 | `e2fsck -fn` clean | `27/16384 files, 1051/16384 blocks` |
| E6 | PAX's disk's tree is Linux's: names, types, modes, owners, links, sizes, blocks, bytes; times in each session's window | 18 names, 0 differences |
| E7 | a note written, `reboot(2)`, e2fsck clean between, debugfs reads it, the second boot prints it, mount 1 then 2 | PASS |
| E8, E9 | the books with 0 errors; init ended, halted | each boot |

The fixture: a 100 MiB file through the double-indirect range (12
direct blocks, 1,024 through the single indirect, the rest through the
double), fast, slow and dangling symbolic links, modes 0, 0755, 04755,
01777, 0600, owners 990, 65534 and 70000:70001, times of 1980, 2001 and
2039, a directory of 300 names, a 255-byte name, a hard link.

## 7. The playground

`notes/px63/play/`: px61's playground recipe made lane-local (CPUs 0-3,
the head's pins), plus `/bin/reboot`, `/etc/fstab` (`user/fstab`), root's
HOME `/home/pax` and a shell that starts there, and `--disk 128M`:
`tools/mkdisk --home 128M pax-home.img` beside the ISO. Booted with a
copy of the disk under TCG and the maintainer's session typed at COM1
(`session.py`): `cd`, `cat > notes.txt` (a line, Ctrl-D), `ls -l`,
`reboot`, then on the second boot `cat notes.txt` and `exit`, checked by
`boot.sh` (both boots mount `/home`, the note in `ls -l` and read back,
`e2fsck -fn` clean, debugfs reads it).

| | |
|---|---|
| tree | `d6f6f015`'s kernel and recipe (the commits after it are the changelog, this note and its evidence) |
| kmain_console.elf | `12219e62b7afc3ce6db255e654a621c5f1de70c5d5ac3efda186bf8cd2272e0d` |
| `pax-playground.iso` | `d51e473fb324f02f591b5c0112f3f2af12b83b830972bbeec1d77a4881537909`, 84,846,592 bytes: read twice on kasumi, twice after the copy to `~/pax-playground/pax-playground.iso` on nomad-1 (`notes/px63/play/digests.out`) |
| `pax-home.img` | `ea88fa0a55b854802614a97797c7cb94c3e4a2ad81b07c449f2d07001306700b`, 134,217,728 bytes (`tools/mkdisk --home 128M`, SOURCE_DATE_EPOCH 1792749658, `d6f6f015`'s time; `e2fsck -fn`: 12/32768 files, 2066/32768 blocks), read twice on each host, at `~/pax-playground/pax-home.img` |
| px61's image | kept as `~/pax-playground/pax-playground.iso.px61`, `8fb1c8ea…` as px61 recorded it |
| the copy | rsync over ssh: the ISO by delta against px61's (81,760,400 bytes matched, 3,086,192 sent, 93 s); the disk compressed (131,045 bytes received, 24 s) |
| the session | PASS (`notes/px63/play/kasumi-session.out`): the first prompt 2.2 s after QEMU started, `reboot(2)` at 7.0 s, the second boot's prompt at 9.8 s, halted at 10.6 s; both boots `fstab: /dev/vda on /home: ext2, read-write, write-back`, mount 1 then 2; `ls -l` shows `-rw-r--r-- 1 root root 34 … notes.txt`; the second boot's `cat notes.txt` prints `written on PAX, before the reboot`; the copy `e2fsck -fn` clean (18 inodes: the note and lope's store, which lives in `$HOME`) |

The maintainer's command (macOS, Homebrew's QEMU; no `-no-reboot`, so
`reboot` restarts the machine on the same disk):

```sh
cd ~/pax-playground
qemu-system-x86_64 -machine q35 -cpu max -m 512M -display cocoa \
    -serial file:serial.log -nic none -cdrom pax-playground.iso \
    -drive file=pax-home.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0
```

then `cd`, `cat > notes.txt` (a line, Ctrl-D), `ls -l`, `reboot`, and
on the second boot `cat notes.txt`. A fresh disk:
`tools/mkdisk --home 128M pax-home.img` (any host with podman or
docker), or a copy of this one kept aside. The shell runs as root with
HOME `/home/pax` (on the disk); `su pax` is the user whose home it is.

## 8. CI

Plants, each a branch never merged, dispatched with its suite alone
(`-f tier=pr -f suites=…`), each red for its own reason (extracts in
`notes/px63/`):

- `px63-plant-bitmap` (`61946328`, each allocated block's bit taken back
  out of the bitmap): run 39928403889, job 120330686286, mpx6-ext2 E5
  red: `e2fsck -fn: Block bitmap differences: +(1040--1044) +2584
  +(2586--2588) +(2590--2591) +2594 … Free blocks count wrong for group
  #0 (13789, counted=15345)`, and E7's check between the reboot's boots
  (`+524`); E1 and E4 red too (kernel/ext2 itself said `a block freed
  that was free: 1071`), E2, E3, E8, E9 green
  (`ci-39928403889-plant-bitmap.log`).
- `px63-plant-sector` (`61ecb94c`, every request one sector off): run
  39928408921, job 120330651205, mpx6-blk K2 red (`read back 32771
  sectors, 3 differ`, a request past the end failed), K3 red (`the host
  reads the image: 32771 sectors, 32771 differ, first at 0`), K4, K5,
  K7 red; K6 (no disk) green (`ci-39928408921-plant-sector.log`).

The PR's first run, 39927513570 at `88a45687` (`tier pr`, 42 suites on
native BIOS): 41 green, mpx6-blk and mpx6-ext2 among them. Red:
mpx4-lobo, `L3 native bios load: R10 flat: moved: kernel less 32 kB a
thread 7440 -> 7456 kB` (16 kB over its 8 kB band between the load
rounds). tl29 recorded the same row red once at trunk (`7112 -> 7288 kB`,
38935970457), the same commit's full run green. Nothing px63 adds allocates without a disk: the volumes' frames
are taken at the first mount (`vol_ready`), the block layer starts only
in kmain_console. The second run, 39936300084 at `d6f6f015` (the
playground's tree; the commits after it are the changelog, this note
and its evidence):
mpx4-lobo green there with the same kernel, so the R10 red above was
the band, not the kernel. The final head's `tier pr` and the labelled
full run are named in the PR body.

## 9. Limits named

- One disk: windows 8-11 hold one device, `vda`; MOUNTS is 4 volumes.
- No partition table: the disk is the file system (P6's installer).
- `/` stays the in-memory tree (R-px63-2).
- ext2 only: an INCOMPAT feature but FILETYPE is refused by name
  (ext3's journal with RECOVER, ext4's EXTENTS, 64BIT, FLEX_BG); an
  unknown RO_COMPAT mounts read-only. Block sizes 1 and 2 KiB are read
  and written by the same code but only 4 KiB is in a suite.
- Directories are linear: an htree's INDEX_FL is cleared at the first
  change, and no htree is built.
- The reserved blocks are counted in statfs (f_bavail) but a user's
  allocation is not stopped at them.
- Extended attributes are neither read nor written (ext_attr's blocks
  are kept as they are).
- Polled I/O with interrupts off: a long read holds the CPU for its
  system call (the 100 MiB read is one boot's 9 s); the flusher writes
  the same way.
- A shared writable mapping's pages are written whole at `msync`,
  `fsync`, `sync` and when the record goes: the page table's dirty bit
  is not read.
- `fallocate` on a volume's file answers as the tree's (a punched range
  zeroed in place, its blocks kept); what Linux's ext2 answers there was
  not measured.
- A volume record nobody holds stays until VOL_KEEP (2,048) are kept;
  the side table has the tree's 16,384 records' room.
- The flusher's 5 s is a constant; no `sysctl`.

## 10. Issues and what to prune

To close: none (no issue named this lane). To file (listed, not filed):

- pax: `/` on a disk (R-px63-2's report), after the installer.
- pax: the installer's partition table for P6 (GPT, an EFI system
  partition and an ext2 partition; kernel/block reading it and offsetting
  a partition's sectors).
- pax: a user's allocation stopped at ext2's reserved blocks (§9).
- pax: a shared mapping's writeback by the page table's dirty bit (§9).
- pax: mpx4-lobo's R10 band (16 kB over at 39927513570, 176 kB over at
  38935970457), if it reds again at the final head.

Prune (the lane's own): kasumi `~/lanes/px63/` (`build/`, `runs/`, `kb/`,
`kc/`, `probe/`, `play/w/`, `play/session/`, `tmp/`, `cache/`, the pax
copy) once the PR merges; nomad-1 `/Users/mfwolffe/lanes/px63/` (the
worktree and the two plant worktrees); the plant branches
`px63-plant-bitmap` and `px63-plant-sector` stay on origin as evidence
(never merged).
