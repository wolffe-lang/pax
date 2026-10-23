# px66 — the partition table: GPT, partitions as disks, and a disk that boots without the ISO

Crawl 54, Opus 5.5. Contract `sprints/pax/66-the-partition-table`
(pax#134). The prediction was committed first, `2790b7ac`
(`notes/px66/prediction.txt`). Branch `px66` from `origin/trunk`
`e5dfad45` (px63's merge).

## 1. Forbidden, and what was read

No Linux kernel source (none of `block/partitions/`, `efi.c`,
`msdos.c`), no other kernel's partition, boot or FAT code, and no source
of util-linux, gptfdisk, dosfstools, mtools, e2fsprogs, systemd, busybox,
QEMU or Limine. Limine's binary release carries its installer's source
(`limine.c`); `tools/fetch-limine` builds it as before, and it was not
opened. What was read is in `docs/SOURCES.md` (px66): the UEFI
specification 2.10, chapter 5 (the GPT disk layout) and Appendix A (a
GUID's text); Limine's `USAGE.md`, `CONFIG.md` and `FAQ.md` at v12.9.1
and `PROTOCOL.md` (`struct limine_file`, `struct limine_uuid`); the man
pages of sfdisk, sgdisk, mkfs.fat, fsck.fat, mcopy, mmd, mtools,
fstab(5), mount(8), blkid(8), lsblk(8), proc(5) and dumpe2fs(8).
sfdisk, sgdisk, mkfs.fat, fsck.fat and mtools ran from Ubuntu 24.04's
packages pinned by digest (`user/disktools.pin`) inside the image
`tools/e2fs` pins; Limine's installer, QEMU and kasumi's Linux 7.2.8 on
QEMU ran as black boxes. Builds in `px13-ubuntu` on kasumi CPUs 0-3
under `flock ~/lanes/kasumi-cores-0-3.lock`; QEMU under `taskset -c 0-3`,
`ulimit -c 0`, long jobs by `setsid -f` with pid files; nothing
installed on any host; nothing built on nomad-1. No merge, tag, issue
filed or closed; no filming words.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `e5dfad45` (px63); px64 (scent on PAX) open as a PR while this lane ran, px65 not yet |
| `kernel/block` | px63's: a table of 4 device records, one disk (`vda`, 254:0, by vblk), the buffer cache keyed by (device, block size, block); `rw` refuses past the capacity by name |
| `kernel/ext2` | mounts mark the volume in use in the cache (write-back: written at the flusher's first turn); unmount marks it clean when it was clean at the mount |
| `kernel/fstab` | `/dev/vda` or `vda`; `LABEL=` and `UUID=` refused by name |
| Limine | 12.9.1 by digest (`boot/limine.pin`); the release has `BOOTX64.EFI`, `limine-bios.sys`, `limine-bios-hdd.h` (the installer's embedded BIOS stages) and the installer |
| the guest | kasumi's 7.2.8-1-cachyos on QEMU, virtio_blk built in (modules.builtin); its partition code is the kernel's own; `lsblk` and `blkid` from the pinned image's util-linux 2.39.3, copied with their libraries into its initramfs |
| QEMU | 11.1.1 on kasumi (no `/dev/kvm`: TCG), 8.2.2 on CI, 11.1.2 on the maintainer's Mac |

## 3. Prediction, scored

| predicted | measured | score |
|---|---|---|
| about 450 kernel lines: block ~330, fstab ~80, procfs ~25; the window itself under 30 | kernel/block +1,224 lines (187 of them comments: the module grew from 726 to 1,929), fstab +69, procfs +21, ext2 +93, files +15, boot_info +33, kmain_console +37, and kmain_part (the self-test) 206: 1,761 inserted in all. The window itself (the offset and the bound in `rw`, the count on both books) 28 lines | wrong: the table is 2.7 times the guess (the 129 device records, the names, the PARTUUID text both ways, the reports); the window's share right |
| the guest and I agree on badprimary; we disagree first on the numbers past vda15 (I guessed 259) | the numbers past 15 are 259:0 on in order (vda16 259:0 … vda128 259:112; holes' vda64 259:0, vda128 259:1), and PAX had them right at its first boot, because the guest was asked before the kernel was written. The disagreements are badprimary (Linux reads no backup header unless booted with `gpt`: "Primary GPT is invalid, using alternate GPT" only then) and wide (Linux reads no entry larger than 128 bytes, with or without `gpt`): both where the contract asks for the specification's reading, so both are named drifts (R-px66-4) | wrong on both counts |
| Limine's BIOS path on GPT needs a partition of its own; the installer refuses GPT without one | so: `limine bios-install` on a GPT image with no BIOS boot partition says "no BIOS boot partition specified or detected" and changes nothing; with one it detects it by its type when no number is given; it writes the MBR's boot code (bytes 1-422) and stage 2 from the partition's first sector (45 sectors, 22.5 KiB) | right |
| boot time: the disk within 25% of the ISO under TCG, both firmwares; under KVM both under a second | QEMU's start to the kernel's first line, the same kernel and initramfs, medians of five on kasumi under TCG: SeaBIOS 0.868 s from the ISO, 1.183 s from the disk (+36%); OVMF 1.764 s from the ISO, 1.424 s from the disk (−19%). KVM not measured: kasumi has no `/dev/kvm` | half right: UEFI inside 25%, BIOS outside it (SeaBIOS reads the 59 MB initramfs through virtio-blk's int13 more slowly than the CD-ROM's); KVM unscored |
| px63's halt leaves the clean flag set; a kill leaves `not clean`; the volume then stays not clean through clean halts, as Linux does | exit and reboot(2) left `clean` with px63's code (the rows passed unchanged); a kill did **not** leave `not clean`: the mount's state sat in the write-back cache until the flusher's first turn, so QEMU killed within 5 s of the mount left `clean, mount count 0` (`notes/px66/kill-before.out`); fixed (`0404c429`): the mounted state is written and flushed at the mount, and the clean state only after every other block is flushed. A not-clean volume stays not clean through a clean halt on PAX and on Linux (measured: mount count 2 to 3, `not clean` both times) | half right: the halts right, the kill wrong |

## 4. What was built

**kernel/block** reads the partition table once at `start` and makes
each partition a device of its own:

- **The table** (UEFI 2.10 §5). LBA 0: 0x55aa or no table, said nothing
  (a bare file system, a blank disk); a record whose boot flag is
  neither 0 nor 0x80 means a FAT boot sector, not a table, said nothing.
  A 0xEE record from LBA 1 is the protective MBR: the primary header at
  LBA 1 and the backup at the last LBA are each checked in §5.3.2's
  order (the signature, a revision of major 1, the header size 92-512,
  the header CRC32 with its own field zero, MyLBA, the usable range, the
  entry size of 128 or a larger multiple of 8 up to 4096, the array of at
  most 1 MiB inside the disk and outside the usable range, the array's
  CRC32). The primary is used when it holds and a failing backup is said
  once; a failing primary with a good backup uses the backup, said once;
  both failing is no partition, said once, `vda` whole. A primary whose
  AlternateLBA is not the last LBA and two good headers that disagree
  are each said. An entry with a zero type GUID is unused; any other is
  partition N (its slot plus one), unless its first LBA is after its last
  or it leaves the usable range (refused, counted, the first named).
  An MBR-only disk's four primary records are partitions 1-4
  (R-px66-1), an extended record refused by name. A disk whose logical
  block is not 512 bytes is refused by name, not read.
- **The devices.** DEVMAX (129) records of 64 words in 17 frames taken
  at `start`: the disk and up to 128 partitions, each with its window
  (first sector, sectors), its numbers (254:N to 15, then 259:0 on in
  order, the guest's), its kind, type, PARTUUID, attributes and
  PARTLABEL (UTF-16LE kept as UTF-8). Names are made from the disk and
  the number (`vda`, `vda64`); `by_name` reads `/dev/vdaN` and `vdaN`.
- **The window.** `rw` checks a request against the device's own
  sectors, then offsets it by the window's first sector, and counts it
  on the partition and on its disk; past the end is -EIO, refused before
  it is made, one line once per device. FLUSH goes to the disk.
- **Mounts.** `claim` and `release` (kernel/ext2's mount and unmount):
  a disk is refused while one of its partitions is mounted and a
  partition while its disk is, by name, -EBUSY (their blocks would be
  cached twice under two keys).
- **Names.** `by_partuuid` (a GPT GUID's text in either case, or an MBR
  partition's `ssssssss-nn`), `by_partlabel`, `uuid_text`, `put_guid`.
- **`/proc/partitions`** in the guest's layout (`%4d  %7d %10d %s`, the
  size sectors / 2 rounded down), made again for each read
  (`partitions_slice`): 128 partitions are 4,152 bytes, longer than the
  frame a /proc file holds.
- **The books**: the disk's line as px63's, plus one per partition a
  request was made to.

**kernel/ext2**: the volume's lines name its device (`ext2: vda2: …`);
the mount claims the device; `probe` reads a device's superblock for its
UUID and label (kernel/fstab); a read-write mount writes the mounted
state at once, flushed, and unmount writes every other block, flushes,
then writes the clean state.

**kernel/fstab**: `PARTUUID=`, `PARTLABEL=`, `UUID=` and `LABEL=` (the
latter two by `ext2.probe` over every device, the disk first); a line
naming a volume says which device it found (`fstab: UUID=… (vda2) on
/home: …`), on success and on refusal.

**kernel/procfs** and **kernel/files**: `/proc/partitions` (0444,
root's), its bytes made by kernel/block at each read.

**kernel/boot_info** and **kmain_console**: the module's `struct
limine_file` media type, partition index and GPT GUIDs, and one line
when the initramfs came from a disk (`boot: /boot/initramfs.cpio from a
disk: partition 1, GPT disk …, partition …`); nothing for an optical
disc, so no ISO's serial moved.

**kmain_part** (the self-test): the report, `/proc/partitions` as procfs
serves it, and each partition's window (its first and last sector held
to the disk's pattern, a request past its end, on a writable disk a
write through the window at both ends).

Tools: `tools/mkgpt` (a GPT or an MBR-only table, the fixtures' and the
disk's; every GUID from a label and SOURCE_DATE_EPOCH), `tools/disktools`
(sfdisk, sgdisk, mkfs.fat, fsck.fat, mtools, blkid from the pinned
image and packages), `tools/linux-part` (the guest's partitions,
/proc/partitions, sysfs, lsblk, blkid and kernel lines on an image),
`tools/mkdisk --gpt` (the disk that boots; its oracles sfdisk --dump,
sgdisk -v, fsck.fat -n of partition 1 and e2fsck -fn of partition 2,
any complaint failing it), `tools/qemu-run --boot-disk` and
`tools/qemu-halt --boot-disk` (the image as a virtio disk with
`bootindex=0`, no CD-ROM). `user/fstab-disk` (the disk's table: `/home`
on `/dev/vda2`). Suite: `tests/mpx6-part`, its fixtures, the guest's
record and the comparer in `tests/mpx6-part.d/`.

## 5. Rulings asked (recommended, implemented, not decided)

- **R-px66-1, an MBR-only disk.** Recommendation: **read as the guest
  reads it, its four primary records**: partitions 1-4, PARTUUID the
  disk signature and the number (`5ca1ab1e-01`, blkid's spelling),
  numbers 254:N; an extended record (0x05, 0x0f, 0x85) refused by name,
  its logical partitions not read (the guest would list them as vda5
  on). Measured on the mbr fixture: PAX's two partitions, numbers,
  starts, sizes, PARTUUIDs and /proc/partitions are the guest's. Against
  refusing an MBR disk outright: it costs 40 lines, a disk a user brings
  from elsewhere reads as Linux reads it, and the window and the names
  are the same code as GPT's. Logical partitions wait for a disk that
  has them.
- **R-px66-2, the BIOS layout on GPT.** Limine allows one, not two
  (USAGE.md "BIOS/GPT"; measured: the installer refuses GPT without a
  BIOS boot partition and finds one by its type). Recommendation:
  **partition 3, 1 MiB at LBA 2048, first on the disk**, so the ESP and
  `/home` keep the numbers 1 and 2 and stage 2 (22.5 KiB) sits in the
  space alignment leaves before the ESP anyway.
- **R-px66-3, where the ESP is mounted (a report).** Nowhere: PAX reads
  no FAT. Recommendation: `/boot`, by fstab, when a FAT reader exists
  (a lane of its own: the P6 installer will want to replace a kernel
  without the host). Until then the host updates the ESP (`tools/mkdisk
  --gpt`, or mtools on the image).
- **R-px66-4, a table the specification reads and Linux does not.**
  Two fixtures: a primary header that fails its CRC with a good backup
  (the specification: "software must check the last LBA"; Linux 7.2.8
  reads the backup only when booted with `gpt`), and entries of 256
  bytes (the specification allowed any multiple of 8, 2.10 asks for 128
  times a power of two; Linux reads none larger than 128, with or
  without `gpt`; sfdisk reads them, sgdisk does not). The contract asks
  for the backup and for the larger entries, and for PAX to give the
  guest's answer on every fixture; the two cannot both hold here.
  Recommendation: **the specification's reading, as implemented**, each
  drift named in kernel/block's header and held per row to a stated
  reference (badprimary to the guest booted with `gpt`, wide to
  sfdisk's dump): a damaged primary is then a disk PAX can still use,
  and the next step (an installer that restores the primary, §5.3.2's
  "should restore") has the backup to restore from. The other way,
  refusing both as Linux does, is two `if`s and the guest's answer
  everywhere.
- **R-px66-5, a volume found not clean.** PAX keeps it not clean
  through a clean halt (it was mounted not clean: nothing has checked
  it), as Linux does (measured). The cost, named: after one power cut
  the maintainer's `/home` says `not cleanly unmounted` at every boot
  until `e2fsck` runs on the host. Recommendation: **keep Linux's rule**
  until PAX has a check of its own or a journal (px63's R-px63-2 (4));
  the README says how to repair it on the host.

## 6. Witnesses and measurements

**tests/mpx6-part** on kasumi, native, BIOS (and P8 under OVMF), TCG,
86 s for the boots (`notes/px66/kasumi-native-bios.out`):

| row | what | kasumi |
|---|---|---|
| P0 | kmain_part, kmain_console and the programs built; the eleven fixtures their recorded sha256s; sfdisk --dump's counts and sgdisk -v's verdicts (no problem on the 128-byte tables, the CRC named on the broken ones); the Linux side (live 7.2.8, recorded) | PASS |
| P1, P2 | per fixture, PAX's partitions and /proc/partitions are the guest's: one 1, four 4, full 128 (131 lines byte for byte, 259:0-112), holes 4 (vda1 vda3 vda64 vda128), order 3, gap 3, badbackup 4, bothbad 0, mbr 2, fourk 0; badprimary 4 = the guest with `gpt`; wide 4 = sfdisk | 13 boots, PASS |
| P3 | the refusals by name, once each (badprimary's primary CRC32, badbackup's backup CRC32, bothbad's no valid GPT, fourk's 4096-byte blocks); none elsewhere | PASS |
| P4 | 161 windows: first and last sectors the disk's; past the end refused by name and counted; four-rw: the host finds exactly the 8 window-edge sectors changed, each the marked pattern | PASS |
| P5 | `0 errors` on every boot; halted | PASS |
| P6 | PARTUUID= (the guest's blkid's) mounts /home from vda2 (fe02); /dev/vda2, vda2, UUID=, LABEL=, PARTLABEL= each name vda2; /dev/vda refused while vda2 is mounted; /dev/vda9 and an unknown PARTUUID name nothing; nofail silent; UUID= first mounts; a whole-disk ext2 with an MBR: /dev/vda mounts, /dev/vda1 refused while its disk is | PASS |
| P7, P8 | the disk boots with no CD-ROM under SeaBIOS (`Booting from Hard Disk...`) and OVMF (`UEFI Misc Device`): the `boot:` line names partition 1 (the guest's vda1 PARTUUID), /home is /dev/vda2 by user/fstab-disk, / in memory, /proc/partitions the guest's, halted | 3.1 s, 3.3 s, PASS |
| P9 | the ISO with a bare ext2 disk: /home from /dev/vda (254:0), no table line, no `boot:` line | PASS |
| P10 | clean after exit (both firmwares) and across reboot(2) (mount 1 then 2); QEMU killed at the session's wait: `not clean`, mount 1; the next mount says so once, its clean halt leaves it not clean | PASS |

The release tier (LLVM) on both firmwares, the same rows (P1-P5 twice,
P6-P10 once): 172 PASS lines, `mpx6-part: PASS`, 117 s for the boots
(`notes/px66/kasumi-release-both.out`).

**The kill row, seen red** before the fix (`notes/px66/kill-before.out`,
kasumi, px63's ext2 at this lane's kernel b2): after the kill
`Filesystem state: clean; Mount count: 0`, the next boot `clean, mount
1`. After `0404c429`: `not clean; Mount count: 1`, then `not cleanly
unmounted, mount 2`, then `not clean; Mount count: 2`.

**Linux on a not-clean ext2** (`tests/mpx6-part.d/linux/notclean.txt`):
mounted read-write and unmounted by the guest, `not clean` before and
after, the mount count 2 then 3.

**The boot time** (`notes/px66/timing.out`, kasumi TCG, QEMU's start
to `PAX: the console`, the same kernel and initramfs, five boots each):

| firmware | from | five boots (s) | median |
|---|---|---|---|
| SeaBIOS | the ISO, a bare ext2 disk beside it | 0.877 0.868 0.948 0.843 0.841 | 0.868 s |
| SeaBIOS | the GPT disk alone | 1.183 1.182 1.199 1.191 1.182 | 1.183 s |
| OVMF | the ISO | 1.789 1.774 1.764 1.751 1.764 | 1.764 s |
| OVMF | the GPT disk alone | 1.424 1.443 1.435 1.411 1.422 | 1.424 s |

## 7. The playground

`notes/px66/play/`: px63's recipe (`build.sh` unchanged but for the
lane's paths; `assemble.sh` with the disk's `/etc/fstab`, a motd that
says what the disk is, and `tools/mkdisk --gpt` in place of the ISO and
`pax-home.img`; `session.py` on the maintainer's own QEMU line, no
CD-ROM; `boot.sh` checking both boots and the host's view).

| | |
|---|---|
| tree | `9892044c`'s kernel and recipe (`kernel/` unchanged since `0404c429`) |
| `pax-disk.img` | `1e4d7e97abe78e1f22d6410c0318f464eb8156077572e725d3994846bdc4daf0`, 536,870,912 bytes (512 MiB: BIOS boot 1 MiB at 1 MiB, ESP 192 MiB FAT32 of 387,101 clusters, /home 318 MiB ext2), SOURCE_DATE_EPOCH 1792787283 (`9892044c`'s time); read twice on kasumi and twice on nomad-1 after the copy (`notes/px66/play/digests.out`); a second `tools/mkdisk --gpt` with the same inputs byte-identical |
| the oracles | sfdisk --dump (three partitions), sgdisk -v `No problems found`, fsck.fat -n `10 files, 158797/387101 clusters`, e2fsck -fn `12/81408 files` (`kasumi-assemble.out`) |
| the copy | `rsync -S -z` to `~/pax-playground/pax-disk.img`; `pax-home.img` (`49f110e2…`, the maintainer's own writes since px63) and `pax-playground.iso` (`d51e473f…`) read before and after, unchanged |
| the session, SeaBIOS | PASS (`kasumi-session-bios.out`): the first prompt 2.8 s after QEMU started, reboot(2) at 7.6 s, the second boot's prompt at 10.8 s, halted at 11.6 s; both boots `boot: … from a disk: partition 1` and `fstab: /dev/vda2 on /home`, mount 1 then 2; `ls -l` shows `-rw-r--r-- 1 root root 34 … notes.txt`; the second boot's `cat` prints the note; the host's `dumpe2fs -h`: `Filesystem state: clean`, mount count 2; e2fsck -fn clean; debugfs reads the note |
| the session, UEFI | PASS (`kasumi-session-uefi.out`), Homebrew's own `edk2-x86_64-code.fd` (`33090cc0…`, copied from nomad-1) as a read-only pflash: the first prompt at 3.2 s, halted at 12.4 s, the same checks |

The maintainer's lines (the README's "A disk that boots"), in a terminal:

```sh
cd ~/pax-playground
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

and under UEFI:

```sh
qemu-system-x86_64 -machine q35 -cpu max -m 512M -nographic -nic none \
    -drive if=pflash,format=raw,unit=0,readonly=on,file=/opt/homebrew/share/qemu/edk2-x86_64-code.fd \
    -drive file=pax-disk.img,if=none,id=d0,format=raw -device virtio-blk-pci,drive=d0,bootindex=0
```

The contract's UEFI line put that file on `-bios`; QEMU refuses it
(`qemu: could not load PC BIOS '…/edk2-x86_64-code.fd'`, measured on
kasumi's QEMU 11.1.1 with the Mac's own file; the file is 3,653,632
bytes), and as a read-only pflash it boots. `-nographic`: Ctrl-A x
quits, Ctrl-A c is the monitor, Ctrl-C reaches PAX; `exit` halts and
marks `/home` clean; closing QEMU any other way is a power cut, and the
next boot says `not cleanly unmounted` (R-px66-5).

## 8. CI

Plants, each a branch never merged, dispatched with mpx6-part alone
(`-f tier=pr -f suites=mpx6-part`, which the plan makes a partial run
of every row), each red for its own reason (extracts in `notes/px66/`):

- `px66-plant-crc` (`0b0efbdf`, the header CRC32 not checked): run
  40017542144, job 120633751959: P3 badprimary red (`the primary's
  refusal`: the broken primary read as good), P3 badbackup red, P1, P2
  and P3 bothbad red (`4 partitions on PAX, 0 by the guest`); every
  other row green (`ci-40017542144-plant-crc.log`).
- `px66-plant-window` (`7616344c`, a partition's requests one sector
  off): run 40017545197, job 120633750289: P4 red on every fixture
  (`first and last read back, 2 differ`), the host's view red (`changed
  [35, 2048, 2049, …] (want [34, 2047, 2048, …])`), and every console
  row (P6-P8, P10: no ext2 superblock where vda2's should be); P1-P3
  green (`ci-40017545197-plant-window.log`).

The PR's run plans the all tier (tools/qemu-run and tools/qemu-halt are
FULL, and `.github/workflows/ci.yml` and `tools/ci-tiers.map` change):
every suite on all four legs. Its id, and the labelled full run's, are
in the PR body (a note committed after them would be a new head).

## 9. Limits named

- One disk (`vda`), up to 128 partitions; entry arrays of at most 1 MiB,
  entries of at most 4096 bytes; 512-byte logical blocks only.
- The table is read once, at boot: no re-read, no partition ioctls
  (BLKRRPART, BLKPG), no `/dev/vdaN` nodes (PAX has no block device
  nodes), no `/sys/block`.
- PAX never writes a table: a failing primary is read around, not
  restored (the specification's "should restore" is the installer's).
- Overlapping partitions are not refused (the specification forbids
  them; nothing here relies on their absence).
- MBR: primary records only; logical partitions are not read.
- The ESP is not mounted (R-px66-3: no FAT reader).
- `/` is the initramfs in memory from the disk too (px67).
- lsblk and blkid do not run on PAX (dynamic glibc programs); the
  guest's answers stand in for them.
- The boot rows run kmain_console under TCG; KVM was not measured
  (kasumi has no `/dev/kvm`; CI's runner meta says which it used).

## 10. Issues and what to prune

To close: pax#134 (this lane), by hand at the merge. To file (listed,
not filed):

- pax: the installer writing a partition table from PAX itself for P6
  (a GPT written, the backup first, both CRCs; a restore of a failing
  primary from its backup; then the ESP and the ext2 made on PAX).
- pax: NVMe and AHCI device names when P6 meets them (Linux's `nvme0n1`,
  `nvme0n1p1` and `sda`, `sda1`; their numbers measured on the guest:
  NVMe partitions on the extended major from the start, SCSI disks 8:16N).
- pax: a FAT reader and the ESP at `/boot` (R-px66-3).
- pax: MBR logical partitions (R-px66-1's refusal).
- pax: a check or a journal so a volume found not clean can be made
  clean on PAX (R-px66-5; px63's R-px63-2 (4)).
- pax: block device nodes and the partition ioctls (`/dev/vdaN`,
  BLKGETSIZE64, BLKRRPART), when a program asks for them.
- planning: the contract's UEFI line (`-bios …/edk2-x86_64-code.fd`) does
  not boot; the pflash line above does (for px67's contract, which
  reuses it).

Prune (the lane's own): kasumi `~/lanes/px66/` (`build/`, `runs/`, `kb/`,
`cache/`, `play/w/`, `play/cache/`, `play/session-*`, `play/tmp/`, the
two edk2 files copied from nomad-1, the pax clone) once the PR merges;
nomad-1 `/Users/mfwolffe/lanes/px66/` (the worktree and the two plant
worktrees); the plant branches `px66-plant-crc` and `px66-plant-window`
stay on origin as evidence (never merged).
