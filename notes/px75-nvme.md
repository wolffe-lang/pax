# px75 — NVMe: the desktops' disks (P6, the metal campaign)

Crawl 54, Opus 5.5. Contract `sprints/pax/75-nvme/px75-nvme.md`, with the
orchestrator's two amendments of 2026-10-26 (the metal machine is
kasumi, an ASUS ROG Maximus XIII Extreme, Z590, UEFI: the boot line
carries each controller's PCI vendor:device beside its Identify summary,
and the AHCI paragraph, §7, is written for its Intel 500-series
`8086:43d2` and ASMedia ASM1061 `1b21:0612`). Branch `px75` from trunk
`187aafdf` (gm01's record). The prediction was committed first
(`8e7f24de`, `notes/px75/prediction.txt`), before the guest was measured
and before the first kernel change (`c89e61c9`). The final head, its
`tier pr` run and the lane-audit line are the PR's; this note is the
lane's record of what was built, measured and seen red.

## 1. Forbidden, and what was read

No kernel's, firmware's, emulator's or driver's source: none of Linux's
`drivers/nvme/`, `block/` or `include/linux/nvme.h`, no BSD's `nvme(4)`,
no SeaBIOS or EDK2 NVMe driver, no QEMU `hw/nvme/`, no SPDK. Read: the
NVM Express Base Specification 2.0c, the NVMe over PCIe Transport
Specification 1.0c and the NVM Express NVM Command Set Specification
1.0c, downloaded from NVM Express, Inc. on 2026-10-27 (sha256 `91cfd52a…`,
`7b6d34e6…`, `8ec4272e…`; the sections each fact came from are named in
`kernel/nvme/nvme.lu`'s header and in `docs/SOURCES.md`). Run as black
boxes: QEMU 8.2.2 (Ubuntu 24.04, CI's) and 11.1.0 (hasu's own) with their
`nvme` and `nvme-ns` devices and blkdebug; hasu's installed Linux 7.2.4
(NixOS) as the guest, with px79's probe, this lane's probe, boreutils'
`ls` and pelt. All of it is in `docs/SOURCES.md` (px75).

Work on hasu, block B, under `flock ~/lanes/hasu-block-B.lock`, in a
rootless container of the lane's own (`notes/px75/rig/`: Ubuntu 24.04
with CI's apt list, so QEMU, OVMF, gcc and e2fsprogs are CI's), CPUs 6-11
by `taskset` inside it, 12 GiB, `/dev/kvm`, the host kernel and modules
read-only for the guest; long runs `setsid -f` with a status file. The
engine shim (`notes/px75/rig/shim-podman`) runs tools/e2fs's and
tools/disktools' programs inside the rig, which is their pinned image's
release. Nothing installed on any host; nothing of the maintainer's
touched; the Mac for git only. No merge, tag, label, issue or release.

## 2. Inputs, re-derived

- px63/px79 left one block driver (kernel/vblk), virtio names hard-wired
  in kernel/block (`vd` + a letter from the disk's index, 254:16k+N), a
  request record of 8 words of which kernel/vblk used 6, one frame (8
  sectors) a request, polled completion with IF clear, and four disks in
  the device table (`DISKS`, the state frame's words).
- kernel/pci records each function's class but had no accessor for it;
  the virtio devices' windows end at 23 of PML4 slot 352; no MSI or MSI-X
  anywhere (the network and sound devices take INTx, the block device
  polls).
- The guest's answers, measured before the first kernel change
  (`notes/px75/guest.sh`, runs n1-n5, then the suite's own Linux side):
  one controller beside vda: nvme0n1 259:0, nvme0n1p1 259:1, nvme0n1p2
  259:2, vda's 254:N untouched, /proc/partitions vda's first;
  `/sys/block/nvme0n1` with dev, size (512-byte units), ro 0, removable 0;
  stat st_blksize 512; the ioctls as virtio's but BLKROTATIONAL 0,
  BLKGETDISKSEQ 2 (the second disk), HDIO_GETGEO 64 heads, 32 sectors,
  capacity / 2048 cylinders; two controllers numbered nvme0, nvme1 in PCI
  order, but their minors in their probes' order: three runs, three
  orders, in every one each disk numbered before any partition;
  namespaces 1 and 3 named nvme0n1 and nvme0n2 (the guest's own count);
  a 4096-byte namespace's size in 512-byte units and no partitions from a
  512-byte GPT; blkdebug's EIO: read(2) EIO at the failing sector and
  4096 of 8192 bytes across it. hasu's kernel has virtio_pci and ext2 as
  modules where kasumi's builds them in (tools/linux-nodes loads them now).

## 3. Prediction, scored

1. Six kernel files: wrong, four. kernel/nvme (1,469 lines with its
   header, 1,128 without comments), kernel/block (+333, -52),
   kernel/files (+93, -16), kernel/pci (+19); kernel/wolf.pkg needed nothing (a module is
   found by its `use`), kmain_console, kmain_session, procfs, fstab and
   ext2 unchanged, as predicted. 1,914 kernel lines inserted, against
   ~1,200 predicted: the driver's header and its status names.
2. QEMU's controller: right on every field shown (1b36:0010, class
   01.08.02, MQES 2047, MPSMIN 0, CSS bit 0, "QEMU NVMe Ctrl", the
   firmware revision QEMU's version, MDTS 7, NN 256, a volatile write
   cache, NVMe 1.4.0, NSID 1 of 512-byte blocks, 64 queue pairs granted,
   no fallback). DSTRD and TO are not printed; the doorbells at stride 4
   worked and no wait ran out.
3. The firmware leaves the controller enabled only when booting from
   it: wrong. SeaBIOS and OVMF both leave every NVMe controller enabled
   (every boot's line says "the firmware left it enabled", CD-ROM boots
   included), so the reset path runs on every boot.
4. The guest's names and numbers: right for one controller and for
   namespaces 1 and 3; wrong for two controllers (not "each disk and its
   partitions in turn": every disk first, in an order the probes race
   for; R-px75-2).
5. A 4096-byte namespace: right (size NSZE × 8, BLKSSZGET 4096,
   BLKGETSIZE64 NSZE × 4096, no table).
6. Bytes and errors: right (the images byte for byte the guest's; 2h/81h
   Unrecovered Read Error; EIO on both).
7. Throughput: wrong in its ranges, right in its order. Predicted PAX
   150-400 MB/s written and 200-500 read; measured 684 and 706 (native
   tier), 1,413 and 1,294 (release), with the image in memory. The first
   read-back measured, 137 MB/s, was hasu's spinning disk (the host let
   the image's pages go), not the driver: the row now takes a tmpfs
   (`PAX_NVME_RAM`). The guest is faster on both, as predicted, and above
   the predicted 500-1,500 (2,329 and 3,946). §8 has every number.
8. The plants: (b) right (red only on the 4096-byte rows). (a) half
   wrong: the guest-image row is red as predicted, but PAX's own
   read-back is red too (4,082 bytes differ at 20480: the reads are at
   other lengths and offsets than the writes, so the omission does not
   cancel), and so is the whole-disk read before any write.

## 4. What was built

**kernel/nvme** (new; items 1, 3): every function of class 01.08.02, up
to four controllers, each a state frame and window 24 + c of the device
slot (the properties page and queues 0-1's doorbells, uncached). PCI:
memory, bus master, INTx off; MSI and MSI-X off in their capabilities.
CAP read (MQES, TO, DSTRD, CSS, MPSMIN: MPSMIN not 0 and CSS without the
NVM Command Set are refusals by name); CC.EN cleared and CSTS.RDY waited
for 0 within CAP.TO; INTMS bit 0 set; the admin pair (32 entries); CC
(IOSQES 6, IOCQES 4, MPS 0, AMS 0, CSS 000b) and EN; CSTS.RDY waited for
1, CFS a refusal. Identify Controller (SQES and CQES checked; SN, MN, FR,
MDTS, VER, NN, VWC kept), the active namespace list (CNS 02h; namespaces
1-4 one by one where it is refused), Identify Namespace for each (NSZE,
FLBAS, the LBA format's MS and LBADS, NSATTR; metadata or blocks outside
512-4096 bytes refused by name; capacity in 512-byte sectors, `NSZE <<
(LBADS - 9)`). Set Features, Number of Queues (one each asked, the grant
kept). Create I/O CQ (IEN 0) and SQ, `min(64, MQES + 1)` entries, halved
while the controller answers Invalid Queue Size, down to 2. The request
path takes kernel/block's record: a slot (8, or depth - 1), the
command identifier, sectors to the namespace's LBAs (a request that is
not whole blocks refused by name), PRP1, PRP2 or a PRP list in the slot's
own page (128 KiB at most: 31 entries, never chained; less when MDTS
says), READ 02h, WRITE 01h, FLUSH 00h, the SQ 1 tail doorbell; the CQ
polled by its phase tag, the head doorbell, the status into the record,
a failure's line by the specification's names (generic, command specific,
media, path; DNR). The controller's line at kernel/block's report (§6),
its books and a normal shutdown (CC.SHN 01b, CSTS.SHST 10b) at the end.

**kernel/block** (items 1, 2): a disk's driver and its unit (D_DRV,
D_UNIT, D_CTRL, D_NSO); virtio disks first, then NVMe namespaces, four
in all; names `nvme<c>n<k>` and `nvme<c>n<k>p<N>` (`name_len`,
`name_byte`, `by_name` for both families); every NVMe disk and partition
on 259, the lowest free minor, the disks numbered before any table is
read (R-px75-2); requests and FLUSHes handed to the disk's own driver;
`rw_pages` (one request of up to `max_sectors` through a page list; a
virtio disk's a page at a time); the bounce pages for raw I/O (32
frames); `rotational`, `geometry` and the report's numbers per driver;
`summary` ends with kernel/nvme's books and shutdowns.

**kernel/files** (item 2): raw I/O to an NVMe disk in pieces up to 128
KiB (one command each) with the read-modify-write in the namespace's own
blocks; a piece that fails is read again a page at a time and what came
before the failing page is the answer (the guest's 4096 of 8192);
BLKROTATIONAL from kernel/block. kernel/pci: `class_code`, `find_class`.

**Tools** (item 2): `tools/qemu-run --nvme FILE[,ro][;DEVOPTS]` and
`--boot-nvme`, and tools/qemu-halt passing both; `tools/linux-nodes
--nvme` and `--qemu ARG` (a controller with namespaces, blkdebug), the
nvme module when asked, virtio_pci and ext2 where they are modules;
`PAX_ROOTDISK_BUS=nvme` for tools/qemu-rootdisk and tools/rootdisk-leg;
`user/elf/nvme.c` with `tools/mknvme` (sizes, speed, sum).

**tests/mpx6-nvme** (new; @disk, kernel/nvme, kernel/files,
kernel/procfs and px79's disk record in tools/ci-tiers.map; its own job;
tests/ci-plan's expectations; the tier job's needs): V0-V12 (§8).

## 5. Rulings (recommended and implemented, not decided)

- **R-px75-1, completion polled.** The contract asks for MSI-X if
  kernel/pci and kernel/apic give it as the virtio devices have, else
  the legacy pin. Neither gives MSI-X, and the virtio block device is not
  on an interrupt at all: kernel/block's request is made and waited for
  inside a system call with IF clear, so an interrupt would only end a
  wait that polling already ends. Recommended and implemented: polled,
  as kernel/vblk; the I/O CQ made with IEN 0, the admin vector masked
  (INTMS), INTx and MSI/MSI-X off. MSI-X belongs with several queues and
  a sleeping request path, a later lane's.
- **R-px75-2, the minors with several NVMe disks.** The guest numbers
  them in its probes' order (three runs, three orders), each disk before
  any partition. PAX: every NVMe disk its minor before any partition, in
  PCI and namespace order, then each disk's partitions in turn; the
  single-controller case is the guest's exactly (V2), the several-disk
  rows hold names exactly and the minors as a set (V5).
- **R-px75-3, CC.CSS 000b.** §3.5.1 step 3 says 110b when CAP.CSS bit 6
  is set; that selects every I/O command set the controller has and asks
  the host to drive the I/O Command Set Profile. PAX drives the NVM
  Command Set alone, which 000b selects on every controller that has it
  (CAP.CSS bit 0, required). QEMU accepts it; so must a desktop's disk.
- **R-px75-4, instance numbers.** `nvme<c>` counts every controller
  found, refused ones too, so a photograph's `nvme1` is the second NVMe
  function in PCI order whatever happened to the first. Unmeasured on the
  guest (QEMU offers no controller Linux refuses); Linux's own number is
  taken before its probe can fail.
- **R-px75-5, the largest request.** 128 KiB (256 sectors, one list page
  of 31 entries) or the controller's MDTS when smaller; a PRP list is
  never chained. The bounce pages raw I/O moves by are 32 frames.
- **R-px75-6, the NVMe-root leg.** The contract's "whole mpx suite on an
  NVMe root in one CI leg, kept to the tier full": mpx5-users (it boots
  kmain_console, which mounts `/` from `root=`; mpx3-boreutils' kernel
  keeps its tree in memory, so its disk leg would not run kernel/nvme
  for `/`), a step after its virtio root leg, `tier == 'full'` (`c8d04c17`:
  first `tier != 'pr'`, but the all tier's mpx5-users job is at its 130
  minutes on trunk without the step: 129 in 40208110580, cancelled at the
  bound in 40326263858 and 40394044200; the step took 28 to 53 more).
- **R-px75-7, the queue-depth fallback's evidence.** QEMU 8.2 (CI's) has
  no `mqes`; the CI row is the single-pair grant (`max_ioqpairs=1`, V8).
  The halving on Invalid Queue Size cannot be provoked from QEMU (it
  takes any size up to MQES + 1); it is named, not measured. hasu's QEMU
  11.1 has `mqes`: the note's witness (§8) boots with `mqes=1`, a queue
  of two entries.
- **R-px75-8, the guest is hasu's.** The lane's host is hasu, whose
  installed kernel is NixOS's 7.2.4; px79's records are kasumi's 7.3.0.
  The NVMe answers measured here are none that changed between the two
  (names, numbers, ioctls, sizes); the record says which kernel.
- **R-px75-9, px75b's sources.** AHCI 1.3.1 says how commands reach a
  SATA device, not what the commands are: IDENTIFY DEVICE's words, READ
  and WRITE DMA EXT and FLUSH CACHE EXT are the ATA Command Set's
  (ACS-3, INCITS 522, or its later revision; T13's public drafts).
  Recommended: px75b's contract names ACS beside AHCI 1.3.1 and SATA's
  FIS definitions (the AHCI specification reproduces the register FIS).
- **R-px75-10, the release build.** pax#215's labelled run (40445676996,
  attempts 1 to 3) overran mpx2-interrupts and mpx2-heap at their 60
  minutes in the release kernel builds (`I0`, `H1`), before any boot:
  each 1.3 to 2.7 times trunk's, the native builds unchanged. On hasu (4
  CPUs, `--no-cache`) kmain_ud2's release object took 167 s at trunk
  `187aafdf` and 310 s at `ba76abff`, codegen 3.1 and 3.4 s of them: the
  serial mid-end. 100 gdb samples of it: 78 in rangeopt's loop versioning
  (`version_one`, `with_hypo`, `seed_pi`), which re-seeds every branch
  of a function for each loop it might version, and whose `incoming`
  walks every block: loops times branches squared, a function. By that
  measure over the release IR `block.table_report` was 52% at trunk and
  68% at `ba76abff` (loops 135 to 263, branches 756 to 1,040): the
  decimal loops px75 put in `name_len` and `name_byte`, inlined at every
  `put_name` there and in kernel/ext2's mount lines. Recommended and
  implemented (`f57d3770`): a disk's name written into its record once
  (`make_stem`), read back without a loop; a partition's number is three
  digits at most. The boot is not it: kmain_blk to `halt` under TCG,
  native BIOS, 1.53 s at trunk and at `ba76abff` with no NVMe controller
  (three boots each). Owed to wolf-lang: the range pass's re-seed per
  candidate loop.

## 6. The boot line (item 3, for px77)

One line a controller, at kernel/block's report, on the serial console
and the framebuffer alike (kernel/serial gives every byte to the
screen):

    nvme0: 1b36:0010 at 00:03.0, NVMe 1.4.0 "QEMU NVMe Ctrl" serial "paxnvme0" firmware "8.2.2"; MDTS 512 KiB, 256 namespaces, 1 active, a volatile write cache; nvme0n1 (namespace 1): 131072 blocks of 512 bytes; the I/O queue pair: 64 entries (asked 64, MQES 2048), 64 SQ and 64 CQ granted, a single pair, polled; the firmware left it enabled

The PCI vendor:device and the slot are `lspci -nn`'s: on kasumi the
Samsung 990 PRO should read `nvme0: 144d:a80c at 02:00.0, …` (bus 2,
behind a root port: kernel/pci walks bridges). Then each namespace's
`block:` line and its table's. A refused controller says why on a line
of the same start. kasumi's NVMe is its Linux root and never a write
target: on it PAX reads (the table, the raw reads a session asks), and
the end's shutdown notification (CC.SHN) is the only register it writes
beyond the bring-up's; no command PAX sends writes the medium unless a
program writes the node. Expected on metal and not testable here: MQES
far above 64 (a 990 PRO's is 16383), MDTS 9 (2 MiB: PAX's 128 KiB
stays), TO tens of units, APST and the host memory buffer never asked
for (the controller runs without them).

## 7. AHCI: what px75b needs beyond this (item 3; no AHCI code here)

px75b drives the Intel 500-series SATA controller in AHCI mode
(`8086:43d2`, the install target's SATA SSD; the firmware must be set to
AHCI, not Intel RST, whose class code is RAID, 01.04.00, and which PAX
should name and refuse) and the ASMedia ASM1061 (`1b21:0612`), both class
01.06.01, from the AHCI 1.3.1 specification and ACS (R-px75-9). It reuses
this lane's plumbing whole: kernel/pci's `find_class` and the bridge walk;
a BAR mapped uncached in a window of the device slot (AHCI's ABAR is
BAR5; windows 28 on); the PCI command bits and the MSI/MSI-X switch-off
(`interrupts_off`, which px75b should move into kernel/pci); polled
completion with IF clear (R-px75-1); kernel/block's driver dispatch
(D_DRV, `hand`, `waited`), `rw_pages` and the bounce pages (a PRDT entry
per page instead of a PRP); the name families (`sda`, `sdaN`, major 8
with 16 minors a disk and 259 past partition 15, as the guest gives them:
to be measured), the 4096-byte-sector handling and its refusals, the
boot line's shape (PCI ids, slot, IDENTIFY's model, serial and firmware,
the port, the link speed), the shutdown at the end (FLUSH CACHE, then
STANDBY IMMEDIATE), and the test harness: `tools/qemu-run --ahci` beside
q35's own ICH9 AHCI at 00:1f.2 (`8086:2922`: PAX will see it on every
boot, empty, and must say nothing about an empty one), tools/linux-nodes
with `-device ide-hd,bus=ahci0.N`, tests/mpx6-nvme's suite shape with its
compare and session scripts. What is AHCI's alone: the HBA reset (GHC.HR)
and AHCI enable (GHC.AE), the BIOS/OS handoff (CAP2.BOH, BOHC) that real
firmware may hold, ports implemented (PI) and each port's stop and start
(PxCMD.ST, FRE, CR, FR, in the specification's order), the per-port
command list (32 headers of 32 bytes, 1 KiB aligned) and received-FIS
area (256 bytes), the command table (a 64-byte CFIS holding a Register
Host-to-Device FIS, the ATAPI area, then the PRDT: 16-byte entries, byte
counts 0's based, 4 MiB each), PxCI to issue and to see a command done,
PxTFD and PxIS.TFES for errors (the ATA status and error registers named
as ACS names them), PxSSTS.DET and a COMRESET through PxSCTL for a link
that is down, PxSIG to tell a disk from an ATAPI device, and from ACS:
IDENTIFY DEVICE (its byte-swapped strings, the 48-bit capacity in words
100-103, the logical sector size in words 106 and 117-118), READ DMA EXT,
WRITE DMA EXT, FLUSH CACHE EXT. One command slot is enough (as one I/O
queue pair is here); NCQ is not needed.

## 8. Evidence index (tests/mpx6-nvme, every row against the guest)

Local runs on hasu's rig (QEMU 8.2.2, KVM, `logs/` under
`hasu:~/lanes/px75/`): run4, every leg (native and release, BIOS and
UEFI), 109 of 110 rows, the one red the guest-side pattern check's
ordering (fixed in `tests/mpx6-nvme`, then the guest re-recorded alone,
lin5: `PASS V0 (linux)`); final, at `aef80e64` (the code of the final
head) against the record, as CI runs it (no readable kernel, the LOUD
line): 110 of 110 rows PASS on all four legs, `mpx6-nvme: PASS`.

- V0 the build and the guest's record (`tests/mpx6-nvme.d/linux/`,
  `Linux 7.2.4 on QEMU 8.2.2 (tools/linux-nodes --nvme, kvm), recorded
  2026-10-27`; the guest's 1 GiB 2,097,152 sectors, 0 differ).
- V1 the boot lines: names (9), four (5), single (8), two (17) lines are
  `tests/mpx6-nvme.d/boot.golden`'s on all four legs.
- V2 stat (7 lines), dev (6), sys (23): the guest's.
- V3 ioctl (46 lines, 6 named refusals), io (56): the guest's.
- V4 before (the whole disk's FNV, both disks), sizes (45 lines: 22
  writes, fsync, 22 reads, 0 bytes differ), after: the guest's; the image
  sha256 `f2518302…`, the guest's; vda unchanged.
- V5 two controllers: dev~ and sys~ the guest's with the minors folded
  (0-6 on both sides); the reads of nvme0n1, nvme1n1, nvme1n2, nvme1n1p2.
- V6 4096-byte blocks: sys, ioctl, io, wio (odd raw writes put back),
  sizes, after: the guest's; the image `3381d6b0…`, the guest's.
- V7 the media error: rd's six answers the guest's; PAX's line
  `nvme0n1: READ of 8 sectors from 4096: status 2h/81h Unrecovered Read
  Error (media and data integrity), -EIO`; 8 errors in the books.
- V8 one queue pair granted (`1 SQ and 1 CQ granted`), sizes the
  guest's.
- V9 1 GiB: the guest's lines, the image `b594521e…` the guest's; the
  numbers (MB/s, 10^6 bytes; write includes fsync; read includes the
  probe's check), image in memory (`PAX_NVME_RAM`), KVM, hasu CPUs 6-11:

  | | write | read and check |
  |---|---|---|
  | PAX native tier, BIOS / UEFI (final) | 683.9 / 688.3 | 706.4 / 715.8 |
  | PAX release tier, BIOS / UEFI (final) | 1,412.8 / 1,325.6 | 1,293.6 / 1,263.2 |
  | the guest, Linux 7.2.4 (the record, lin5; run4's 1,942.4 / 3,883.8) | 2,329.2 | 3,945.5 |
  | PAX native, the image on hasu's disk (run3) | 631.6 | 137.3 |

  CI's runner (TCG): the speed row runs in the full and all tiers only
  (`--rows all`); its number is in the full run's log.
- V10 /etc/fstab by PARTUUID=: `fstab: PARTUUID=86aec534-… (nvme0n1p2) on
  /mnt: ext2, read-write, write-back`; /proc/mounts and `ls -ln /mnt` the
  guest's.
- V11 `/` on NVMe, booted from the controller under SeaBIOS and OVMF:
  `root: PARTUUID=68ffc1a8-… (nvme0n1p2) on /: ext3, read-write,
  data=ordered`; /proc/mounts `/dev/root / ext3 rw,relatime 0 0`; e2fsck
  -fn clean (`pax-root: 26/16384 files`).
- V12 every NVMe disk 0 errors, every controller `shut down`, init ended,
  halted.
- The queue of two on hasu's own QEMU 11.1 (`notes/px75/mqes-witness.sh`,
  `mqes=1,max_ioqpairs=1`): `the I/O queue pair: 2 entries (asked 2, MQES
  2), 1 SQ and 1 CQ granted`, 106 commands, `PASS sizes: 45 lines, the
  guest's`, halted.
- The disk suites kernel/block's and kernel/files' changes reach, run
  locally native BIOS against their recorded guests: mpx6-blk 15 rows,
  mpx6-nodes 28, mpx6-part 93, mpx6-ext2 19, mpx6-root 31, every one
  PASS (`logs/regress-*.log`).

## 9. CI

`mpx6-nvme`'s job (the pr tier: names, four, error, single; the full and
all: every session), `PAX_NVME_ROWS` from the plan; mpx5-users' job gains
the NVMe-root step in `tier full` (R-px75-6); tools/ci-tiers.map's rules and
tests/ci-plan's expectations (287, every one PASS). This PR touches
tools/qemu-run and tools/qemu-halt, FULL paths, so its plan is the all
tier: every suite on every leg. Run ids: in the PR and the report.

## 10. Seen red

- Plant (a), `px75-plant-prp` (`84231296`, draft PR #213 against px75):
  the PRP list starts at the third page. CI run 40443194956, job
  mpx6-nvme 121988533779 (TCG, the recorded guest), red by name: `FAIL V4
  native bios names: FAIL before: … guest 'sum /dev/nvme0n1: 67108864 at
  0: 67108864 read, fnv 94d4756b7c2e258c' | PAX '… fnv 282165f6be786187'`,
  the sizes read-back `4082 bytes differ` at 20480, `FAIL V4 … (the
  image): sha256 4285e846…`; `FAIL V6 native bios four` and `FAIL V8
  native bios single` the same way; V1, V2, V3, V7 and V12 green. Seen
  first on hasu (`logs/plant-prp.log`, the same fnv and sha256).
- Plant (b), `px75-plant-capacity` (`39a79204`, draft PR #214 against
  px75): the capacity in the namespace's own blocks. CI run 40443196223,
  job mpx6-nvme 121988381271, red by name: `FAIL V1 native bios four: …
  block: nvme0n1: 16384 sectors (8388608 bytes)` for the golden's 131072,
  `FAIL V6 native bios four: FAIL sys: … size 16384` and the ioctls'
  BLKGETSIZE64; every 512-byte namespace's row green (V1-V4, V7, V8, V12
  on names, error and single). Seen first on hasu
  (`logs/plant-capacity.log`).
- Both drafts' base is px75, so each diff is its plant alone and its
  `tier pr` run is mpx6-nvme on the PR leg (the plan job's suites).
- These two runs are also the suite's first on CI's runner: every row
  but the planted ones green under TCG against the recorded guest.

## 11. Departures and limits named

Polled, one I/O queue pair, no MSI-X (R-px75-1). Four disks in all,
virtio first. No `/dev/nvme0` character device, no `/dev/ng0n1`, no NVMe
ioctls (NVME_IOCTL_*), no `/sys/class/nvme`; /sys/block holds px79's
files only (the guest's nvme0n1 has 30-odd more). BLKSECTGET, BLKRAGET
and BLKFRAGET refused by name as on virtio (the guest answers 1024, 256,
256). Several controllers' minors are PAX's order, not the guest's race
(R-px75-2). A namespace with metadata, or blocks past 4 KiB, is refused;
a partition table on a 4096-byte namespace is not read (the guest reads
a GPT made for 4096-byte sectors there; none is tested). Writes that
fail are not exercised (blkdebug's write errors are not in a row). No
Dataset Management (TRIM), Write Zeroes, Format or Sanitize. The
shutdown runs at a clean end only (not after a panic or a power cut, by
nature). The queue depth's halving is unmeasured (R-px75-7). The guest's
ext2 module shows its own mount options (folded in V10).

## 12. Done-when

- [x] items 1-4 as §4-§10; the boot line and the AHCI paragraph (§6, §7)
- [x] the prediction first (`8e7f24de`), scored (§3)
- [x] every row against the guest; the images byte for byte (V4, V6, V9)
- [x] two plants red by name locally, their draft PRs' runs cited (§10)
- [x] README's status paragraph (`a94b730b`, README only), docs/BOOT.md,
  docs/SOURCES.md
- [x] the PR, `Footprint: cross-cutting`; the audit run once
- [ ] the full tier at the head (the orchestrator labels and watches)

## 13. Issues and what to prune

- To file (pax): the open nightly-red #158 (mpx5-pelt on 2026-10-26,
  mpx5-jobs on trunk's last push) is owed by "the next lane", and this
  lane did not take it (its contract does not name it); interrupts and
  several queues for NVMe (R-px75-1); AHCI, px75b (§7).
- Prune after the merge: hasu `~/lanes/px75/` (the clone, the plant
  trees, build/, build-plant-*/, build-regress/, guest/, smoke/, the
  `localhost/px75-ubuntu:2` image); the Mac's worktrees
  `~/lanes/px75/pax`, `plant-prp`, `plant-capacity`; the branches
  `px75-plant-prp` and `px75-plant-capacity` once their drafts are
  closed.
