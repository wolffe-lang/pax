# px77c — the install stick: trunk with px78, for the first install on kasumi (P6, M-PX6)

Contract: `wolf/sprints/pax/77c-the-install-stick/px77c-the-install-stick.md` (crawl 54), launched 2026-10-29 on the
maintainer's question whether the staged smoke stick could install PAX. It could not: px77b's stick (`101e7761`)
predates px78. This lane built the install stick from pax trunk `56b9f554` (px78, pax#245) by px77b's recipe,
qualified that exact image with px78's kasumi leg (M0–M10) on copies, and staged it on nomad with `INSTALL.txt`.
Two additions from the coordinator during the lane (2026-10-29): kasumi now holds only the target SATA SSD, so state
exactly how the smoke stick's inventory and the install stick's allow-list spell model and serial, and write
`INSTALL.txt` for a machine whose only disk is the target; then, after the first metal boot on kasumi restarted the
moment PAX started (px77d triages it), stage the image as a candidate, `pax-install-candidate-56b9f554.img`, with
"NOT YET: PAX does not boot on kasumi yet (px77d); do not install from this stick." atop `INSTALL.txt`. The stick
will be rebuilt once px77d's fix lands. Footprint: notes (notes and one docs/*.md page; no kernel, program, tool or
test change).

## Forbidden

No kernel's, firmware's, bootloader's, emulator's or driver's source was read. Read: the contract, RULES §1–§10,
PAX's own notes (px77a, px77b, px78, px82), `docs/INSTALL-METAL.md`, the README, and PAX's tree (`tests/mpx6-kasumi`,
`tests/mpx6-install`, `tests/mpx6-install.d/metal.py`, `tools/{mkdistribution,distribution-root,mkdisk,check-usb,
linux-nodes,fetch-busybox}`, `user/install/{allow,inventory,main,ui}.lu`, `kernel/ahci/ahci.lu`'s identity strings,
`boot/install-targets`), and the planning repo's `wolf/tools/lane-audit.sh`. Run as black boxes only: QEMU 8.2.2,
Ubuntu's OVMF, Limine 12.9.1, hasu's Linux 7.2.4 kernel and modules (`/nix/store/j66ih4hz…-linux-7.2.4/bzImage`,
`5c4bsam2…-linux-7.2.4-modules`, binaries), Ubuntu's static busybox by digest, macOS's `hdiutil` and `diskutil`.
kasumi was not touched; no physical disk was opened (the macOS step ran on a disk-image copy); hasu's `:9364` and
`:9308` servers and the maintainer's hasu data were not touched; nothing was installed; no label, dispatch, merge,
issue or release; no attribution trailers. On nomad only `~/lanes/px77c/` and the new files in `~/pax-smoke/`
were written; every file already in `~/pax-smoke/` is unchanged.

## Inputs, verified

- **Base** pax trunk `56b9f554ebbb0e781d6a963fe9c259d6369839a3`, a fresh clone on hasu at
  `/home/mfwolffe/lanes/px77c/pax`; `build-inside.sh` asserts the head and a clean tree, `tools/mkdistribution`
  asserts both again. The Mac worktree (branch `px77c`) was used for git only.
- **Recipe** px77b's, unchanged but for the lane's directory, the head, the image's name and px78's sixth stick file
  (`notes/px77c/{build,build-inside,stick-build}.sh`, `live-payload.py` and `podman-shim` byte-identical to
  px77b's). px77b's hasu directory is pruned, so its inputs were rebuilt by its note: px77a's copies of px82's
  inputs, copied (never moved) from `/home/mfwolffe/lanes/px77a/` and compared by `diff -r` (equal; the two dangling
  `changelog.Debian.gz` links in the disktools cache are links in both trees): `base-dev.cpio` sha256
  `098b918ecfe7fae1b1c05c1a92b0bbde33cbc88fab0b63b3737941590f8a35c4` (read twice, and asserted by
  `tools/distribution-root`), `build/inputs`, `cache`, `inputs/lope-local`, `inputs/limine-download`. No pin moved
  between `101e7761` and `56b9f554` (`git diff --stat` over `user/*.pin`, `user/install/games.txt`), so the copied
  program inputs still match their pins, which `tools/distribution-root` checks file by file; the kernel, the
  installer, the disk tools, Limine's installer and `reboot` are rebuilt from the checkout.
- **Toolchain** wolf 0.2.35, archive sha256 `4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a`;
  Limine 12.9.1, `limine-binary.tar.gz` sha256 `5cdebc518daa3af30b22c2322ba0dba2e0e2046fa8b087b9e13071b8dbcdcff4`;
  each read twice (`archive-reads.txt`, `limine-read-{1,2}.sha256`). QEMU 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.18);
  OVMF_CODE_4M `ad23261d…`, OVMF_VARS_4M `5d2ac383…` (`qualify-*/versions.txt`), px77b's.
- **The conf** unchanged: px78 moved only `boot/install-targets` and `boot/io.S` under `boot/`, so
  `boot/limine-usb.conf` is px77b's (the stick's copy sha256 `d3b4a14b…`, as on px77a's and px77b's sticks).
- **Containers** the build and every qualify boot in `localhost/px75-ubuntu:2`; the legs in `localhost/px78-ubuntu:1`
  (px78's image for this leg: `px75-ubuntu:2` plus `gdisk fdisk strace`, its history read), because M10's `sgdisk -v`
  is not in `px75-ubuntu:2`. Every container `--memory 12g`, `taskset -c 0-5` inside, block A held by
  `flock /home/mfwolffe/lanes/hasu-block-A.lock` for each job alone and released at its end (each `RELEASED` line in
  `build.log`, `chain-1.log`, `chain-2.log`); px77d shares the block.
- **The old stick** for the spelling: `~/pax-smoke/pax-stick-101e7761.img` copied to hasu (`old/`), sha256
  `598d34396c2c8c05d70a92037dc5dc041fd346b5d5d14312f6db6feaabf7378e` on both hosts, made read-only; its kernel
  taken from its ESP by mtools (sha256 `ba8fda6f…`, px77b's) for the screen's symbols.

Commits on `px77c`: the prediction first (`4d8173a3`), pushed before the first build (02:09Z; the build began
02:11:30Z), then the runbook addition, the scripts, the evidence and this note.

## Prediction

`notes/px77c/prediction.txt` (`4d8173a3`), against what was found:

| predicted | found |
|---|---|
| 795,869,184 bytes, one MiB over px77b's: px78's payload growth crosses the 48,618 bytes left | **right**: 795,869,184. Kernel 2,463,288 → 2,560,208 (+96,920); live archive 384,888,308 → 385,030,412 (+142,104) |
| kernel 2,500,000–2,560,000 bytes | **wrong by 208 bytes**: 2,560,208 |
| a second build byte-identical | **right** (`PASS second stick build byte-identical`, `build.log`) |
| `/pax/install-targets` = `boot/install-targets`, 19 lines, no entry; an empty `/pax/logs` | **right**: sha256 `f282a6d7…` both; `PASS the allow-list on the image is boot/install-targets (19 lines, 0 entries)` |
| the leg M0–M10 PASS on the first run, TCG | **right**, and on all three copies |
| the install 300 s (180–600) from the confirmation, the leg 8 min (5–15) | **wrong, both under the range**: 140.85 s and 196.01 s. The release tree stages fast; the install's time is the root's inode tables, as px78 found (161 s for its small tree) |
| 2 GiB of guest memory may not hold the archive, its root and the staged copy | did not happen |
| old inventory: the whole model; new: its first 16 bytes trimmed; the serial the same; an empty list's `--check` prints no allow line | **right** on every disk. Not predicted: a serial with leading spaces keeps them on the boot line (`serial "   21021X801234"`); both inventories and Linux drop them |
| macOS: `hdiutil attach` mounts the ESP; macOS adds `.fseventsd`; fsck clean; the leg reads the line | **wrong on the mount**: `hdiutil: attach failed - no mountable file systems` (macOS never mounts an EFI partition by itself); `diskutil mount diskNs1` did. **Right** on `.fseventsd`, plus `pax/._install-targets` (AppleDouble for `com.apple.provenance`); fsck clean; leg B read the line |
| the runbook's Linux step writes `model=Samsung SSD 870 serial=PX78-TARGET-0001`; the leg reads it | **right** (leg C) |
| the smoke qualify: MSI keyboard types first try; the stick a driven `/dev/sdb`, read-only, refused as a live medium; `reboot -p` reaches S5 with no debugger; 4K by Limine's editor | **right** but one: the read-only stick is refused as `read-only`, the third refusal, before the live-medium one (the installer's order) |

Not predicted: the first metal boot on kasumi restarted the moment PAX started (the coordinator's word; px77d's, not
reproduced in any QEMU machine here); `--check`'s closing hint says "the refusals above print each disk's own line to
copy" while, with the shipped empty list, no refusal does; the variant legs' witness digests differ from px78's
record (below).

## Evidence index

Everything under `notes/px77c/`; the hasu tree is `/home/mfwolffe/lanes/px77c/`.

### The release pair and the stick

`build.log`: block A 02:11:30Z–02:19:06Z; `tools/mkdistribution` 02:11:30–02:18:41Z (7m11s; `logs/distribution.log`),
the live payload (`out/live-payload.txt`: only `etc/pax-files.sha256`, `etc/pax-live-login`, `etc/pax-run`, `root`
differ from the verified release archive), `tests/usb-tools` (14) and `tests/usb-linux-fetch` (6), `tools/mkdisk
--usb`, `tools/check-usb` with SIX expectations (`logs/usb-check.log`: px77b's five and `/pax/install-targets`), the
empty-list assertion, a second build `cmp`-identical, both negative checks red by name (`logs/usb-efi-red.log`:
`required boot file missing: /EFI/BOOT/BOOTX64.EFI`; `logs/usb-mbr-red.log`: `protective MBR must cover the disk`).

| | px77b's smoke stick | this install stick |
|---|---|---|
| commit | `101e7761` | `56b9f554` |
| image | 794,820,608, `598d3439…378e` | 795,869,184, **`e520d515ff5ceb27c526b07627043ab894ac81f21378bc51fb28897271c8996e`** |
| `/boot/pax` | 2,463,288, `ba8fda6f…` | 2,560,208, `113d94249a12c29ab2155867c818a0a487d0d944fbe468378d033e9fadc107de` |
| `/boot/initramfs.cpio` | 384,888,308, `08a0c1dd…` | 385,030,412, `ff6ecd6b0a0a8cc89b93bbe740475299968bfe0d0c9566968555f70feabedd48` |
| `/pax/install-targets` | absent | 849 bytes, `f282a6d7…`, 19 comment lines, no entry |
| conf, BOOTX64.EFI, limine-bios.sys | `d3b4a14b…`, `90a9a6a5…`, `96867c2b…` | the same three |
| banner | `release 98bbabc6` | `PAX: kernel 56b9f554…; release 09dfc428` (`out/pax-banner`), SOURCE_DATE_EPOCH 1793315136 |

The image's sha256 was read six times, all equal: twice after the build (`image-hasu-build-read-{1,2}.sha256`), twice
on hasu at staging (`image-hasu-stage-read-{1,2}.sha256`), twice on nomad after the copy
(`mac/image-nomad-read-{1,2}.sha256`, `shasum -a 256`).

### The spelling: the smoke stick's inventory against the install stick's allow-list

`qualify.py` machines `s-old` and `s-new`: px77b's machine a (q35, 2 GiB, `qemu-xhci`, OVMF, `-serial none`, TCG)
with the same four SATA disks on q35's AHCI (`qualify-s-*/command.json`, the same `-device ide-hd,model=…,serial=…`
strings), booted once from each stick read-only, `pax-install --inventory` typed on both (`--check` on the new one);
and Linux 7.2.4 on the same four device strings (`linux-ident/guest/serial.log`, px78's `ident.sh`):

| QEMU `model=` / `serial=` | 101e7761 `--inventory` | 56b9f554 `--inventory` (= its allow-list line) | Linux `device/model` |
|---|---|---|---|
| `Samsung SSD 870 EVO 500GB` / `S6PXNM0T612345A` | `model=Samsung SSD 870 EVO 500GB serial=S6PXNM0T612345A` | `model=Samsung SSD 870 serial=S6PXNM0T612345A` | `[Samsung SSD 870 ]` |
| `CT500MX500SSD1` / `ABCDEFGHIJ0123456789` | `model=CT500MX500SSD1 serial=ABCDEFGHIJ0123456789` | the same | `[CT500MX500SSD1  ]` |
| `WDC WDS500G2B0A-00SM50` / `   21021X801234` | `model=WDC WDS500G2B0A-00SM50 serial=21021X801234` | `model=WDC WDS500G2B0A- serial=21021X801234` | `[WDC WDS500G2B0A-]` |
| `SanDisk SDSSDH3 512G` / `2104AB401234` | `model=SanDisk SDSSDH3 512G serial=2104AB401234` | `model=SanDisk SDSSDH3 serial=2104AB401234` | `[SanDisk SDSSDH3 ]` |

Both kernels print the boot line the same way, the whole 40-byte model and the serial with its leading spaces kept
(`ahci0: … port 2: sdc model "WDC WDS500G2B0A-00SM50" serial "   21021X801234"`). The rule, from the code that makes
each line (`kernel/ahci/ahci.lu` `identity_len`: trailing spaces dropped from 16 model bytes since `751458e8`, from 40
before; `user/install/inventory.lu` and `allow.lu`: each value `trim()`med, compared with `==`):

- **model**: the first 16 characters of the 101e7761 inventory's model, every character counted (spaces and
  punctuation too), case unchanged, then the spaces at the end of those 16 dropped; a model of 16 or fewer stays
  whole. (The 16 are the raw ATA bytes, so a model the boot line shows starting with a space counts from the quote;
  no tested disk has one.)
- **serial**: copied whole, never cut (ATA's 20 bytes); both sticks have already dropped leading and trailing spaces.
- **line**: `model=<model> serial=<serial>`, one space between, case-sensitive.

`s-new`'s `--check` with the shipped list: `Disks (5); install allow-list /dev/sde1:/pax/install-targets:
/dev/sde1:/pax/install-targets names no disk`, each SATA disk `refused: no usable install allow-list (…)`, the stick
`refused: read-only` (QEMU's `readonly=on`), and no allow line printed (`qualify-s-new/command-2.txt`).

### Kasumi tonight in QEMU, and the smoke qualify on the unmodified image

`b-old` and `b-new`: px76's F8 machine (q35 `pit=off`, 8 GiB, both xHCIs `nec-usb-xhci,msi=on,msix=off`, BARs above 4
GiB, a VGA offering 3840x2160) with kasumi's one disk tonight, a 2 GiB SATA file of known content as `Samsung SSD 870
EVO 500GB`, serial `S6PXNM0T612345A`; `c-new` is `b-new` with Limine's editor adding `resolution: 3840x2160` for one
boot (px77b's c). Root and every command typed through the USB keyboard on MSI, first try (`xhci 1: ports 8 MSI vector
80`, `xhci 2: ports 8 MSI vector 81`, `xhci: keyboard usb2-5 speed 3 boot report 8`).

- `b-old` (what tonight's photo was to show): `model=Samsung SSD 870 EVO 500GB serial=S6PXNM0T612345A`; ends as
  px77b's checklist, `reboot -h`, the halt summary (`sda: 1 reads (1 sectors), 0 writes`), QMP quit.
- `b-new` (the install stick before its line): NEW since px77b, the stick is a driven disk (`usb-storage: usb1-1:
  "QEMU    " "QEMU HARDDISK   " … write-protect on`, `block: sdb: … read-only`, its GPT read), `ls /dev` lists
  `sda sdb sdb1 sdb3`, the inventory prints `model=Samsung SSD 870 serial=S6PXNM0T612345A`, `--check` refuses both
  disks and writes nothing; `reboot -p` (px78) ends at S5, QEMU exit 0, no debugger (`07-poweroff-last-screen.txt`:
  `block: sda: … 0 writes`, `block: sdb: 231 reads … 0 writes`, `poweroff: ACPI S5 types 0/0`). 392 rendered lines
  before the login (343 scrolls + 49 rows), 386 in the kernel's transcript.
- `c-new`: `screen: 3840x2160 … font spleen 8x16 at 2x, 240x67 cells`; ends `reboot`, QEMU exit 0.
- Every writable file byte-identical (sha256 of every byte before and after): the four spelling disks
  `802dc9d0…`, `8229a7d9…`, `3e25cbab…`, `a6ff71fe…` under both sticks; kasumi's target
  `16eb4d61d9104c39a01301a08a315593ee684d9219eb3fc0b636524bd6c9620c` in b-old, b-new and c-new.

### The leg on copies of the exact image (M0–M10)

`leg.sh NAME COPY tcg|kvm [VARIANT]` moves a fresh copy of the image in as the leg's `metal/stick.img` (its sha256 at
the start in `leg-*/stick-at-start.sha256`) and runs px78's leg in run mode (`PAX_METAL_MODE=run`): an inputs
directory holding what run mode reads, the stick's own kernel ELF (`native.elf.path`, for the screen's symbols) and
the `paxfat` built with it. M0's build row is this lane's build (the same `check-usb` with the allow-list among the
files); the leg's M0 append and read-back ran in A.

| leg | the line on the copy | machine | accel | M0–M10 | install from the confirmation | the leg | wall |
|---|---|---|---|---|---|---|---|
| **A** | the leg's own `paxfat append` (as from CachyOS), `tests/mpx6-install --only metal` unmodified | px78's: NVMe, Steam 4TB, SanDisk, target `PX78-TARGET-0001` | TCG | all PASS | 140.85 s | 196.01 s | 3m16.5s |
| **B** | written on macOS (`mac/mac-edit-transcript.txt`), the line read off `b-new`'s screen | kasumi tonight: the target alone (`S6PXNM0T612345A`) | TCG | all PASS (M5 vacuous: no other disk) | 129.28 s | 181.14 s | 3m01.6s |
| **C** | written by `docs/INSTALL-METAL.md` step 2's commands under Linux 7.2.4 (`linux-cachyos/guest/serial.log`) | px78's | KVM | all PASS | 23.43 s | 72.63 s | 1m13.1s |

Leg A's PASS lines (`chain-1.log`): M1 the live login, the witness file, `/` lists `dev` once; M2 the target alone on
the list, `sda` (the right model, the wrong serial), `sdb` and the NVMe refused by name, the stick refused before the
list; M4 guided to `/dev/sdc`, ACPI power-off; M6 `/pax/logs/install-1.txt` on the stick holds the inventory, the
refusals, the plan, every phase and each written partition's first MiB (equal to the target image's), the stick's ESP
`fsck.fat -n` clean; M7 OVMF booted the AHCI disk with the stick removed, chosen as from the boot menu; M8 the witness
file read back, `/home/wolf` there; M9 the installed disk refused as the running root; M10 the root `e2fsck -fn`, the
GPT `sgdisk -v` and the ESP `fsck.fat -n` clean; M5 the three other disks byte-identical over their allocated extents
before and after both boots: nvme `23e7b466f3c8ef15703702419ab725900d2256297deed9de6ce1c77119baafa2`, steam
`e1203a73fb211b26d621cff5b85085bd3a650e2a79f1f0e86d8959f2504e1535`, sandisk
`303fd56ea5315b1f89e6a7dc4b88e1a60b80415b4fbba4be05e48bb91c7b9e08`, the same digests px78's record run printed.
Leg C's witnesses (`d6e37655…`, `b1a76e2d…`, `b74c56d0…`, before = after) differ from A's because the variants run
their copy of `metal.py` directly, without `tests/mpx6-install`'s `SOURCE_DATE_EPOCH=1700000000`, and `tools/mkgpt`
derives the foreign disks' GUIDs from it. The sticks after the install (their logs written): A `51b0a409…`, B
`524bf3c9…`, C `9b46c80e…`. Screens: `leg-*/metal/boot{1,2}/*.txt` (PNGs for A and B), the stick logs
`leg-*/metal/install-1.txt`.

The variants (`make-variants.py`, each edit asserted to apply once; `metal-noappend.py.diff`, 1 line;
`metal-onedisk.py.diff`): `metal-noappend.py` drops only the append, so the copy's own line is what M0's read-back, M2
and M6's `1 line(s)` see; `metal-onedisk.py` is noappend's leg with the NVMe and the two other SATA disks removed, the
target on `ide.0` as `/dev/sda`, the stick `/dev/sdb`, the needles renamed to match.

### The allow-list step, macOS and Linux, each tested on a copy

- **macOS** (nomad, `mac/`): `hdiutil attach -imagekey diskimage-class=CRawDiskImage` of a copy, then `diskutil mount
  diskNs1` (no sudo), `echo '<line>' >> /Volumes/PAX-ESP/pax/install-targets`, `grep -c '^model='` = 1, `diskutil
  eject /Volumes/PAX-ESP`. On hasu (`esp-check-legB-mac.txt`): `fsck.fat -n` exit 0; mtools lists macOS's
  `.fseventsd/` (3 files) and `pax/._install-targets` (4,096 bytes); the stick's `paxfat` reads one entry. Leg B
  installed from it.
- **Linux** (`cachyos-step2.sh`): the runbook's five lines verbatim but for the two names, under busybox's `sh`,
  `sed`, `tee` and `mount` with a root `sudo` shim and hasu's `vfat` modules; Linux's raw `device/model` is
  `[Samsung SSD 870 ]`, the line written `model=Samsung SSD 870 serial=PX78-TARGET-0001`
  (`esp-check-legC-linux.txt`: `fsck.fat -n` exit 0, one entry). Leg C installed from it.

### Seen red

- **macOS's mount** (`mac/hdiutil-attach.log`, `mac/mac-edit-transcript.txt`): `hdiutil: attach failed - no mountable
  file systems` on the copy: macOS never mounts an EFI partition by itself; `diskutil mount` does. INSTALL.txt and the
  runbook say so.
- **The first Linux oracle run** (`linux-ident-run1/guest/serial.log`): `qemu-system-x86_64: -device
  ide-hd,…: Block node is read-only`; QEMU's `ide-hd` refuses a `readonly=on` drive, so `linux-oracle.sh` gives the
  scratch disks read-write (`linux-ident/` is the second run).
- **The two negative stick checks** (`logs/usb-efi-red.log`, `logs/usb-mbr-red.log`), red by name as above.

### Staged on nomad

`df -h ~` first: 68 GiB available (`mac/df-before-staging.txt`). `~/pax-smoke/pax-install-candidate-56b9f554.img`
(the coordinator's name; made read-only), 795,869,184 bytes, sha256 `e520d515…996e`, the six reads above.
`~/pax-smoke/INSTALL.txt` (`staged-INSTALL.txt`, sha256 `09ac1486…`): the NOT YET line first; which file is which (the
install stick against both smoke sticks); the rule with the four measured rows; the line from tonight's photo (A), from
the install stick's own inventory, boot–read–power off–edit on the Mac–boot again (B), or from CachyOS (C); flashing
and the macOS edit; the firmware settings, the check, the install, the log, F8 to the SSD, back to CachyOS (its NVMe
put back), each with its reference screen. `~/pax-smoke/56b9f554-candidate/`: eleven reference PNGs from b-old, b-new,
c-new and leg B (`staged-screens.sha256`). Nothing already in `~/pax-smoke/` changed; px77b's `README.txt` still names
the smoke stick, and `INSTALL.txt` says never to install from it.

### The runbook

`docs/INSTALL-METAL.md` step 2 gained "From macOS" and "Without CachyOS: the line from an inventory" (`6e10a8a4`),
each from the tests above.

## Done-when

- [x] The prediction committed and pushed before the first build (`4d8173a3`).
- [x] Item 1: the release pair and the stick at `56b9f554` by px77b's recipe, its inputs rebuilt from px77a's copies by
  the note; the same conf; a second build byte-identical; six ESP files checked, the allow-list empty at px78's path.
- [x] Item 2: px78's leg M0–M10 on a copy of the exact image (A, TCG: 196.01 s, install 140.85 s; witnesses above),
  and on copies carrying a macOS-written (B, the target alone) and a Linux-written line (C); px77b's smoke qualify on
  the unmodified image: the MSI keyboard, the 4K GOP, the read-only listing, `reboot -p` at S5, no disk written.
- [x] Item 3: the line for macOS and for CachyOS, each written to a copy and read by the installer; the 101e7761 to
  56b9f554 spelling rule measured on four disks under both sticks and Linux (the coordinator's addition).
- [x] Item 4: staged as `pax-install-candidate-56b9f554.img` with `INSTALL.txt` for a machine whose only disk is the
  target, NOT YET first (the coordinator's word); six digest reads; every existing file kept.
- [x] Item 5: this note; README read against the pass: current (notes and one runbook page; "Physical writes and
  real-machine boots are not tested here" still holds).
- [ ] The orchestrator reviews the audit; no label, no CI wait (notes). The stick is rebuilt after px77d's fix.

Departures: the legs ran in `localhost/px78-ubuntu:1`, not `px75-ubuntu:2` (M10's `sgdisk`); the leg in run mode with
lane-local variants for B and C (diffs kept); leg C under KVM; the staged name and the NOT YET line by the
coordinator's instruction; `qualify.py` keeps no frames (px77b kept 48 per boot).

Issues filed or closed: none. Owed to file (pax):
- `pax-install --check` with the shipped empty list ends "(the refusals above print each disk's own line to copy)",
  but only a `not on the install allow-list` refusal prints one; with no list, print each disk's would-be line (the
  maintainer's route B reads it from `--inventory` instead). Its `Disks` line also repeats the list's source
  (`install allow-list /dev/sdb1:/pax/install-targets: /dev/sdb1:/pax/install-targets names no disk`).
- `tests/mpx6-kasumi` cannot be pointed at a given image: a `--stick IMAGE` (and a no-append switch for a stick whose
  line is already written) would let a release lane qualify the staged bytes without a lane-local copy of `metal.py`.
- Already in hand, not this lane's: the restart at PAX's start on kasumi (px77d).
