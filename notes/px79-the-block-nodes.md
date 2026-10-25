# px79 — block device nodes, the block ioctls and a second disk (pax#144)

Crawl 54, Opus 5.5. Contract `sprints/pax/79-the-block-nodes/px79-the-block-nodes.md`
(pax#144). The prediction was committed first (`e40a2731`,
`notes/px79/prediction.txt`). Branch `px79` from trunk `105d0d1f`
(px68's merge). The final head, its `tier pr` run and the lane-audit
line are the PR's; this note is the lane's record of what was built,
measured and seen red.

## 1. Forbidden, and what was read

No kernel's source: none of Linux's `block/` (ioctl.c, partitions/,
bdev.c, genhd.c), `drivers/block/virtio_blk.c`, `fs/block_dev.c`,
devtmpfs or sysfs, and no other kernel's block layer; no util-linux
source (lsblk, blkid, sfdisk, partx), no libc's, no partitioner's. Read:
the uapi headers `linux/fs.h`, `linux/blkpg.h` and `linux/hdreg.h` from
the refs clone's allowed paths (the requests' numbers and structures),
the man pages ioctl(2), ioctl_list(2), sd(4), open(2), lseek(2), read(2),
write(2), pread(2), fsync(2), sendfile(2), splice(2), copy_file_range(2),
mount(2), proc(5), sysfs(5), mknod(2), and the VIRTIO 1.2 specification's
§5.2.3-§5.2.4 (VIRTIO_BLK_F_GEOMETRY and its config layout) and §4.1.2
(PCI discovery). Run as black boxes: kasumi's installed Linux
7.3.0-4-cachyos on QEMU 11.1.2 (q35, TCG) with one to four virtio-blk
disks, e2fsprogs 1.47.0 (tools/e2fs's image), boreutils' `ls` and pelt.
All of it is in `docs/SOURCES.md` (px79).

Builds in `localhost/px79-ubuntu` (from px13-ubuntu) on kasumi CPUs 0-3
under `flock ~/lanes/kasumi-cores-0-3.lock`; QEMU under `taskset -c
0-3`, `ulimit -c 0`; long jobs `setsid -f` with a marker; nothing
installed on any host; nothing built or booted on nomad; `~/lanes/px69`
never touched. No merge, tag, label, issue or release.

## 2. Inputs, re-derived

- px66 left each partition a device of kernel/block's (`vda1` …, 254:N)
  with no node in `/dev`; `mount(2)` took px67's internal names
  (`/dev/vda2`, `vda2`, `0xfe02` …) by string, not by a path walk; one
  disk only (vblk's single state frame, windows 8-11).
- The guest's answers, measured before the first line of kernel code
  (`notes/px79/guest.sh`, then the suite's own Linux side): with no udev
  devtmpfs makes `brw-------` 0:0 nodes (not the `brw-rw---- root disk`
  a distribution's udev leaves); `st_blksize` 512, `st_size` 0; three
  disks in PCI slot order are 254:0, 254:16, 254:32; partitions 16 and
  up take major 259, minor the lowest free across every disk; a 100-byte
  read at offset 3 answers 100 (buffered, R-px79-4); a write across a
  partition's or disk's end is short, at or past it -ENOSPC (not -EIO);
  a read-only disk opens O_RDWR and every write is -EPERM, a write of no
  bytes too; BLKRRPART is -EBUSY while any partition of the disk is open
  (not only mounted), 0 with the disk itself open, -EINVAL on a
  partition; O_EXCL without O_CREAT is an exclusive open, -EBUSY against
  another exclusive open or a mount of the device, its disk or any of
  its partitions; HDIO_GETGEO answers the device's own geometry (QEMU's
  16/63/130 for a 64 MiB disk; `cyls=100,heads=4,secs=17` as given),
  which needs VIRTIO_BLK_F_GEOMETRY; BLKSECTGET, BLKRAGET and BLKFRAGET
  answer the guest's request queue and read-ahead tunables.

## 3. Prediction, scored

1. Nine kernel files changed: nine, but not that nine: kernel/virtio
   (`device16`) and kmain_part (the partition walk) instead of
   kmain_console and kmain_session, which need no change (each disk
   says its own lines). About 1,400 lines inserted: 1,718 (block 809,
   with 258 out; files 531; procfs 197; vblk 161). Low.
2. Four nodes on the playground disk (vda, vda1, vda2, vda3): right
   (the crash row's `tools/mkdisk --gpt --root` disk, three partitions).
3. No page-cache or journal disagreement in the crash row: right (N14:
   the GPT's first 34 sectors written back through `/dev/vda` and LBA 100
   marked while `/` held uncommitted changes, the kill, the replay, the
   sector read back, e2fsck -fn clean).
4. The ioctl the guest answers that PAX cannot: wrong. Not BLKDISCARD
   (the probe never asks a destructive request); the three are
   BLKSECTGET, BLKRAGET, BLKFRAGET, block-layer tunables with no fact of
   the device behind them. HDIO_GETGEO did need GEOMETRY, and the guest's
   numbers are the device's, not made from the capacity: wrong too; PAX
   takes the feature now.
5. Two disks in the right order at the first try: right (r1's N1).
6. R-px79-1..4's guesses: all four right (254:0/254:16; buffered; EBUSY
   when merely open; short across the end, ENOSPC at it).

## 4. What was built

**kernel/vblk, kernel/virtio** (item 4): up to four disks (DISKS),
each a state frame and windows 8+4k to 11+4k of the transport's slot,
found by walking kernel/pci's table for 1af4:1001 and 1af4:1042 in
order; every public call takes the disk's index. VIRTIO_BLK_F_GEOMETRY
taken and its config read (`virtio.device16`); the features line says
`, GEOMETRY` (tests/mpx6-blk's regexes take it).

**kernel/block** (items 1-3): the device table is per disk, DPD = 129
records each (the disk and 128 partitions), four disks, sparse
(`present`), so one disk's frames are what they were; each disk's
partition-table words and device frames apart; the buffer cache keyed
by device as before (one disk's keys unchanged). Names `vda` to `vdd`,
numbers 254:16k+N up to 15 and 259:M past it (the lowest free M, asked
before the new record says 259: r1's off-by-one). Claims and opens
(`claim`, `open_dev`, `close_dev`; D_CLAIM, D_EXCL, D_OPENS) and the
relation "the same device, or one the other's disk", which carries every
EBUSY rule the guest showed. Raw I/O through a bounce frame (S_BOUNCE),
eight sectors a request, a partial sector read, changed and written
back; `raw_wrote` forgets the clean cached buffers of the disk a raw
write touched. `rescan` (BLKRRPART), `blkpg_add`, `blkpg_del`, their
refusals and one line each; `geometry`, `diskseq`, `soft_block`.

**kernel/files** (items 1, 2, 3, 5): the node type T_BLK (its reference
the device and its record's generation, so a node a rescan removed is
stale, -ENXIO) and the open kind K_BLK; `/dev` lists the block devices
after its fixed names, DT_BLK; stat's fields (S_IFBLK 0600, st_rdev,
st_blksize 512, st_dev 0:5, times 0). `blk_open` (O_EXCL, O_DIRECT,
O_SYNC, O_DSYNC; O_NOATIME and O_PATH refused as on any node), `blk_in`,
`blk_out`, `blk_write`, `blk_seek`; read, pread64, write, pwrite64,
writev, lseek, fsync, fdatasync, flock; sendfile and splice onto a node
(found by reading sendfile's targets: before it they counted the bytes
and wrote none, a silent loss for `cat disk.img > /dev/vdb`; now
`blk_put_kernel`, with the send row to hold it); `blk_ioctl` (§6).
mount(2) walks its source: a T_BLK node is its device (-ENOTBLK for
anything else, the walk's own -ENOENT); `/proc/mounts` prints the node.

**kernel/procfs** (item 1): `/sys/block` (a directory per disk: dev,
size, ro, removable, and a directory per partition: dev, start, size,
partition, ro) and `/sys/class/block` (every device's), their references
carrying the device; a name in them is found by kernel/block's own name
for it (`dev_child`), never by walking the listing (r1's stall).

**kernel/user, kernel/ext2, kernel/fstab, kmain_part**: write's dispatch
for a node; the loops that assumed a dense table ask `block.present`.

**Tools** (item 4): `tools/qemu-run --drive FILE[,ro][;DEVOPTS]`,
repeatable (the generic form, not `--disk2`), each a further raw
`-drive … -device virtio-blk-pci` after `--boot-disk`'s, in order;
`tools/qemu-halt --drive` passes it on; `tools/qemu-rootdisk` (a QEMU
stand-in) leaves a run with disks of its own as it is (its rows name
them vda…), said in its header. `tools/linux-nodes` (new): the Linux
guest with one to four drives, devtmpfs mounted `mode=755`.
`user/elf/nodes.c` and `tools/mknodes` (new): the static probe both
sides run.

**tests/mpx6-nodes** (new; @disk, kernel/files, kernel/user, procfs,
mpx6-part's fixtures in tools/ci-tiers.map; its own job in ci.yml;
tests/ci-plan's expectations): N0-N14, below.

## 5. Rulings (recommended and implemented, not decided)

- **R-px79-1 the numbers: (A), Linux's**, as measured: 254:16k+N to
  partition 15, 259 and the lowest free minor across every disk past it
  (vda16 259:0 … vda128 259:112, vdb16 259:113; after a BLKPG delete the
  freed minor is the next one given). `ls -l /dev`, `/proc/partitions`
  and `/sys` match the guest byte for byte (N1, N2, N11).
- **R-px79-2 where the nodes live: (A)**, in memory, the kernel's `/dev`
  filled from kernel/block's table at boot and after every rescan or
  BLKPG change (the nodes are T_BLK references computed from the table,
  not stored anywhere), so no image changes and the partitions found at
  boot are the ones listed.
- **R-px79-3 BLKRRPART while mounted: (A)**, and the guest's wider rule
  with it: -EBUSY while any partition of the disk is open, mounted or
  held exclusively (an open file counted in D_OPENS), 0 with the whole
  disk open (N6). A mounted partition's node is never dropped under it.
- **R-px79-4 odd-length raw I/O: (A)**, the guest's answers: any length
  at any offset (read-modify-write of partial sectors), short across
  the end, 0 (read) or -ENOSPC (write) at or past it (N4, N5).

## 6. Witnesses (tests/mpx6-nodes, every row against the guest)

Four PAX boots (native BIOS; pelt as pid 1 running the session script)
and the same four sessions on the guest, with copies of the same disks;
each `== section` held line for line by `tests/mpx6-nodes.d/compare`
(the `ls` date column folded; the three tunable ioctls must be PAX's
named -ENOTTY with the buffer untouched).

- **nodes** (vda a 64 MiB GPT with vda1 and an ext2 vda2, vdb 16 MiB
  blank, vdc 4 MiB read-only with geometry 100/4/17): N1 stat, ls, /dev;
  N2 /proc/partitions, /sys/block, /sys/class/block; N3 every ioctl on a
  disk, a partition, the blank and the read-only disk (value and width);
  N4 raw reads; N5 raw writes (and the images unchanged after); N6 the
  holds (BLKRRPART, O_EXCL, mount against opens), a raw write to vda
  with vda2 mounted, e2fsck -fn clean; N7 BLKPG and the table read again
  (vda3 added in the free end, gone after); N13 the books.
- **gpt** (vda the same, vdb and vdc 16 MiB blank, vdd an 8 MiB ext2
  read-only): N8 a pattern written to every sector of `/dev/vdc` and read
  back, the host reading the image (tools/blk-pattern: 32768 sectors, 0
  differ); N9 tools/mkgpt's head and tail written to `/dev/vdb`,
  BLKRRPART, vdb1 and vdb2 with the table's /sys sizes, the host finding
  the bytes; N5 (send) the table's files sent onto vdb2 by sendfile and
  through a pipe by splice, read back, both short across the end, and
  copy_file_range's -EINVAL (the guest's answer); N10 the ext2 copied
  from `/dev/vdd` into `/dev/vdb2`, mounted by its node, /proc/mounts'
  line, the refusals (-EINVAL, -ENOTBLK for /dev/null, -ENOENT), e2fsck
  clean.
- **numbers** (two copies of mpx6-part's `full` fixture, 128 partitions
  each): N11 every number past 15, and after a delete, an add and a
  rescan the lowest free again.
- **fstab** (vda the same, vdb gpt.img with an ext2 vdb2): N12
  `/dev/vdb2 /mnt ext2 defaults 0 2` mounted by kernel/fstab, the
  guest's mount(2) of the same node.
- **crash** (N14, the all rows): `/` a journalled vda2; the GPT's first
  34 sectors written back through `/dev/vda` and a pattern at LBA 100 while
  `/` held changes, the kill; the host finds the table as it was and the
  sector marked; the next boot replays (`1 transaction (sequence 1 to
  1), 15 blocks written home, 0 revoked`), reads LBA 100 back, halts;
  e2fsck -fn clean.

The last local run before the note: r3 on kasumi, 27 PASS, 0 FAIL
(`mpx6-nodes build rc=0 linux rc=0 boot rc=0 137s pass 27 fail 0`), the
Linux side recorded from it (`tests/mpx6-nodes.d/linux/`, `Linux
7.3.0-4-cachyos on QEMU (tools/linux-nodes)`). The neighbours on the
same tree before the send row (batch b1): mpx6-blk 14/0, mpx6-part
93/0, mpx6-ext2 18/0, mpx6-root 30/0 (px67's rows unchanged); mpx6-journal
in the PR's run. On CI the suite runs on the record, said loudly.

The ioctls (N3; widths as the guest's): BLKGETSIZE64 u64 bytes,
BLKGETSIZE unsigned long sectors, BLKSSZGET, BLKPBSZGET, BLKIOMIN 512,
BLKIOOPT 0, BLKALIGNOFF 0, BLKDISCARDZEROES 0, BLKROGET, BLKBSZGET 4096
(or the largest block the size is a whole number of), BLKROTATIONAL 1
(u16), BLKGETDISKSEQ (1 for vda …), HDIO_GETGEO; root only (-EACCES for
a user): BLKFLSBUF, BLKRRPART, BLKPG. Refused by name, one line each:
BLKSECTGET, BLKRAGET, BLKFRAGET, the setters, BLKDISCARD, BLKSECDISCARD,
BLKZEROOUT, BLKTRACE*, BLKPG_RESIZE_PARTITION (-EINVAL), every other
0x12 and HDIO request; a request of no block device's (TCGETS, FIONREAD,
FS_IOC_GETFLAGS) -ENOTTY as the guest answers it.

A raw write and the cache: Linux keeps a disk's and a mounted
partition's caches apart, and a raw write to a block that a mounted file
system holds dirty is the user's to avoid. PAX says the same and adds no
lock: a raw write forgets the clean cached copies of the sectors it
wrote, so the next read sees the disk, and leaves a dirty buffer as it
is, which its file system writes later over the raw write, as on Linux.
N6 writes into vda's first and last 8 KiB raw with vda2 mounted (and
puts the bytes back) and e2fsck finds vda2 clean; N14 does it under `/`.

## 7. The switch px69 flips

PAX legs with a second disk: `tools/qemu-halt --boot-disk DISK --drive
BLANK.img` (or `tools/qemu-run`, the same option), on a kernel built
from this branch. The boot disk is `vda`, the first `--drive` `vdb`
(`/dev/vdb`, no partitions until a table is written and BLKRRPART asked
or the next boot), a second `--drive` `vdc`; `FILE,ro` makes one
read-only. Without `--boot-disk` (an ISO on the CD-ROM) the first
`--drive` is `vda`. `limine bios-install /dev/vdb` and the other disk
tools write through the node; the kernel sees a new table at BLKRRPART.

## 8. CI

The plants, each one commit on a `px79-plant-*` branch, never merged,
dispatched with `-f tier=pr -f suites=mpx6-nodes` (a partial run: every
row, native BIOS):

| run | job | plant | head | red |
|---|---|---|---|---|
| 40159334092 | 121067504774 | px79-plant-size: BLKGETSIZE64 one sector short | `54dffacc` on `99b3bf3b` | N3: `guest 'ioctl BLKGETSIZE64: 0 bytes 0000000400000000…' \| PAX '… 00feff0300000000…'`; N9 and N11 too (their ioctl lines); every other row green |
| 40159335657 | 121067592000 | px79-plant-minor: vda2's minor 7 | `ef48d58e` on `99b3bf3b` | N1: `guest 'stat /dev/vda2: … rdev 254:2 (fe,2) …' \| PAX '… rdev 254:7 (fe,7) …'`, ls and dev the same; N2, N7, N9, N11 (their vda2 lines) |
| 40159337228 | 121067523444 | px79-plant-rescan: BLKRRPART keeps vda3 | `362d4c74` on `99b3bf3b` | N11 only (`stat /dev/vda128: -2 ENOENT`: the stale record took the 128th slot); N7 green, see §9 |
| 40159970068 | 121069469428 | px79-plant-stale: the same plant at the head with N7's new vda3 | `d7a3414e` on `233aa050` | N7: `PAX ' 254        3       1024 vda3'` after the rescan where the guest has none; N11 as above |

The same runs show the suite green on the CI runner on the record (N0's
`LOUD: no readable Linux kernel on this host: the Linux side is the
record made on kasumi`). The PR's own runs are named in its body.

## 9. Seen red

- **r1** (kasumi, the first whole run): N0 (no `disks.sha256` yet; the
  five images' sums the same from the build container and the host,
  recorded); N9's table held the three tunable ioctls to the guest's
  values (the compare's named-refusal rule applied only to the ioctl
  section; now to every `ioctl` line); N11 `vda16 259:1` where the guest
  says `259:0` (ext_minor counted the record it was making); N13 the
  numbers boot never ended (600 s: a lookup in `/sys/class/block` walked
  the listing once per name, each step a walk of the table: 258 names
  made it cubic; now `dev_child`); N14 `Could not allocate block` (the
  96 MiB crash disk left 30 MiB for `/` after mkdisk's 64 MiB ESP; now
  128 MiB). r2: 26 PASS, 0 FAIL.
- **The first rescan plant** was red on N11 alone: the nodes session's
  only vda3 was BLKPG's overlap refusal, so no vda3 existed before the
  rescan. N7 now adds a vda3 in the disk's free end (`add 3 52428800
  1048576`, the guest's 0), which the rescan must take away; the
  re-planted `px79-plant-stale` is red there.
- **sendfile and splice onto a node** wrote nothing and answered the
  count (found reading the targets, no row had asked); fixed, and the
  send section holds both against the guest.

## 10. Departures and limits named

- The nodes are `brw-------` 0:0, the guest's with no udev, not the
  contract's `brw-rw----`: that is udev's rule and group, and PAX has
  no `disk` group yet.
- `/sys/block/<disk>` and `/sys/class/block/<name>` are directories, not
  links into `/sys/devices`; `/sys/dev/block` and `/dev/disk/by-*` are
  absent (udev's). What a reader reads through them is the guest's.
- BLKSECTGET, BLKRAGET, BLKFRAGET refused (-ENOTTY, named), where the
  guest answers its block layer's tunables.
- O_DIRECT is taken but its alignment rule is not enforced (the bounce
  frame serves any buffer); the rows ask only the aligned read.
- Node times are 0 (devtmpfs stamps a node's birth); the compare folds
  the date.
- mmap of a node -ENODEV; a node as sendfile's or splice's input
  -EINVAL; splice onto a node with an output offset -ESPIPE (Linux
  takes one); copy_file_range onto a node -EINVAL, as the guest.
- lsblk, blkid and sfdisk are dynamic glibc programs and do not run on
  PAX; the probe asks what they ask (the files and the ioctls).
- Four disks; 128 partitions a disk (BLKPG beyond: -ENOSPC); raw I/O is
  uncached and eight sectors a request (polled, as px63's).
- tools/qemu-rootdisk does not add a root disk to a run that brings its
  own drives (its rows' names would move); no suite asks for that yet.

## 11. Issues and what to prune

Issues to close: pax#144 (at the merge). To file (none filed here: RULES
§3):
- `/sys/dev/block/<maj:min>` and the `/sys/devices` links, for lsblk
  run unmodified once a dynamic glibc runs (with px66's dynamic-loader
  issue);
- a `disk` group and udev's `brw-rw---- root disk` modes, if P6's
  installer runs as a user;
- BLKDISCARD and BLKZEROOUT (VIRTIO_BLK_F_DISCARD, WRITE_ZEROES), for a
  formatter that discards;
- reading a node by sendfile or splice, and splice's output offset onto
  one;
- run-suite's `--only build` of mpx6-part exits 127 after its P0 PASS on
  kasumi (seen in batch b1; the boots green; not this lane's code, not
  chased).

Prune (at the merge): kasumi `~/lanes/px79/` (the `pax` and `t3`
copies, `build/`, `cache/`, `guest/`, `kc/`, `kb/`, `probe/`, `bin/`,
`runs/`, `tmp/`) and the image `localhost/px79-ubuntu`; this Mac's
worktrees `/Users/mfwolffe/lanes/px79/pax` and
`/Users/mfwolffe/lanes/px79/plant-{size,minor,rescan,stale}`; the
branches `px79-plant-size`, `-minor`, `-rescan`, `-stale` stay on origin
as evidence (never merged).
