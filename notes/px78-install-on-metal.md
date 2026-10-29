# px78 — install on metal: the allow-list, RST refused, the whole install in QEMU shaped like kasumi (P6)

Crawl 54. Contract `sprints/pax/78-install-on-metal/px78-install-on-metal.md`, with the orchestrator's R-px78-1
answer of 2026-10-29 (the target is a SATA SSD the maintainer plugs in later; not `sdb`; the stick's default list
stays empty; the runbook's first metal step reads the model and serial from CachyOS). Branch `px78` was built on
px76's head `101e7761` (the contract's base `10a27451` plus px76, read before the first change); px76 merged at that
same commit, and px77b's notes-only merge `f2aa9fd8` is the base the branch was rebased onto before the PR. The shas
below are the rebased branch's. One model wrote it, Claude Opus 5.5, across one context reset and one account switch
(the weekly limit). The prediction was committed first (`a63f021c`, `notes/px78/prediction.txt`, 15:45), before the
first change (`6f2bf351`) and before any guest ran.

Before this lane the installer would write any disk that was not the running root, mounted or read-only; PAX could
not see the stick it booted from (px74 logged QEMU's SuperSpeed `usb-storage` as "enumerated, not driven"), so it
could neither read a list from it nor write a log to it; and an Intel controller in RST mode left the SATA disks
silently absent. Now
the installer writes only to a disk named by model and serial on the stick, says why every other disk is refused,
writes its transcript to the stick after every step, and the whole path (boot the stick, install, power off, boot
the disk alone, log in, read back a file) runs on a QEMU machine shaped like kasumi with every other disk held
byte-identical.

## 1. Forbidden, and what was read

No kernel, firmware, hypervisor, driver, bootloader or partition-tool source: not Linux's `drivers/usb/` (xhci,
storage, usb-storage's transport), `drivers/scsi/` (sd), `drivers/ata/`, `block/`, `fs/`; not EDK2's or SeaBIOS's
USB, AHCI or boot-manager code; not QEMU's `hw/usb/` or `hw/ide/`; not Limine's. What each piece was written from is
`docs/SOURCES.md`'s px78 section: USB Mass Storage Bulk-Only Transport 1.0 and the class overview 1.4, the T10 SPC-4
and SBC-3 command formats, the xHCI 1.2 sections px74 already cites plus the bulk-transfer and endpoint-recovery
ones, virtio 1.2's `GET_ID`, the PCI class codes, the FAT32 FSInfo fields and `reboot(2)`; the rows that say
"knowledge" were written from the lane's knowledge of those published documents, not from a copy opened during the
lane. Run as black boxes: Linux 7.2.4 under QEMU 8.2.2 for the sysfs identity of NVMe, SATA and USB disks
(`notes/px78/linux-ident.txt`, `ident.sh`), QEMU 8.2.2 and Ubuntu's OVMF (`OVMF_CODE_4M.fd`), `sgdisk` 1.0.10,
`fsck.fat` 4.2, `e2fsck` 1.47.0. Read: PAX's own tree (`kernel/{xhci,block,ahci,procfs,vblk,files}`,
`kernel/kmain_console.lu`, `user/install`, `user/disktools/paxfat`, the disk suites, `tools/{mkdisk,check-usb,
usb-session,linux-nodes,ci-plan}`, `tools/ci-tiers.map`, `.github/workflows/ci.yml`), the px71, px73, px74, px75b,
px76, px77a and px84 notes, and the p6 campaign.

Work on hasu block A (CPUs 0–5 by taskset inside the container, 12 GiB) under
`flock /home/mfwolffe/lanes/hasu-block-A.lock`, waited for in printing loops while px77b held it; the image
`localhost/px78-ubuntu:1` (`localhost/px75-ubuntu:2` plus the disk oracles), the stick's FAT tools through the host's
rootless podman (`~/lanes/hasu-env`) because `tools/disktools` needs a container engine the image does not nest.
Every sparse image lived under `/home/mfwolffe/lanes/px78/` and was deleted after its row. The Mac worktree was used
for git only. Nothing of the maintainer's was touched; no merge, tag, label, release, or issue filed or closed.

## 2. Inputs, verified

- **Base:** px76's `101e7761` (pax#236), then trunk `f2aa9fd8` (px77b, notes only) by rebase; nothing to resolve.
- **Toolchain:** wolf 0.2.35 (pin `cf0c13d`, sha256 `4cc4045b…`) and Limine 12.9.1 by digest
  (`tools/fetch-wolf`, `tools/fetch-limine`, "wolf 0.2.35 (wolfgang, pin cf0c13d)" in every log); QEMU 8.2.2
  (`Debian 1:8.2.2+ds-0ubuntu1.18`), CI's.
- **Linux oracle:** hasu's `/nix/store/j66ih4hz9b6k8fm6qhspnxancdfwsbda-linux-7.2.4/bzImage` with its own modules
  (`xhci-pci`, `usb-storage`, `sd_mod` loaded by `tools/linux-nodes --qemu … usb-storage`), binaries only.
- **The hasu clone** was kept file-for-file equal to the Mac worktree (sha256 of every changed file compared after
  each sync; 51 files at the last check). One sync from macOS left AppleDouble `._*` files beside the sources, which
  `wolf build` (a directory is one module) read as source: the first inputs rebuild failed on
  `./files/._files.lu`; they were deleted and every later copy made with `COPYFILE_DISABLE=1`.

## 3. Prediction, scored

`notes/px78/prediction.txt`, committed first (`a63f021c`, 15:45), against what was found:

| Predicted | Found |
|---|---|
| The install onto the sparse 512 GB target, guided, under TCG: 270 s (150–450); the whole leg 15 min | **The install inside the range, 40% under:** 160.8 s from the typed confirmation to `Installation complete` under TCG on hasu (170.9 s from the first answer); 24.4 s under KVM. **The leg, wrong by 4×:** 210.6 s under TCG for both boots, the typing, the install and the checks (70.1 s under KVM), not 15 min; the boots are seconds, not minutes, and the install is most of it. |
| OVMF boots the installed AHCI disk with no boot entry of its own, by the removable-media path | **Wrong as stated.** With the stick removed and boot 1's variable store, OVMF did not fall through to the disk: it went to its UEFI shell, with the disk's ESP mapped as `FS0` (`notes/px78/seen-red/boot2-no-bootorder-uefi-shell.png`). With the disk first in QEMU's boot order (bootindex 0: the firmware boot menu's choice, F8 on kasumi) OVMF made the option itself and booted `\EFI\BOOT\BOOTX64.EFI`; PAX writes no boot entry either way (R-px78-8). |
| The first refusal is the stick not being a disk (enumerated, not driven), then kernel/block's four-disk table against kasumi's five | **Right, both, before the leg first ran:** QEMU's SuperSpeed `usb-storage` was px74's "enumerated, not driven" (px74's own row asserted it, `tools/usb-session`), and five disks overflowed `DISKS = 4`; `kernel/usb_storage` and `DISKS = 8` came first. The leg's own first failures were the installer's: the stick log's second append refused by an exclusive create of a reused scratch name, and staging stopped at the live root's second `dev` (§4.4). |
| Linux's SATA `device/model` is the 16-byte SCSI product, so a line copied from CachyOS will not match PAX's full ATA model | **Right** (`linux-ident.txt`: `Samsung SSD 870 EVO 500GB` reads `[Samsung SSD 870 ]`); R-px78-5 makes PAX's sysfs model the same 16 bytes. |

## 4. Evidence index

### 4.1 What was built

- **USB mass storage** (`bf8f8e21`, `b4622cd7`, `4b117bf0`). `kernel/xhci` drives a mass-storage interface (class
  08h, SCSI transparent, Bulk-Only) at any speed: Configure Endpoint for the two bulk endpoints (SuperSpeed burst from
  the companion descriptor), Normal TRBs with ISP and IOC, a polled completion with interrupts held off, Reset
  Endpoint and Set TR Dequeue Pointer for a halted pipe, and a removal that keeps the record (its disk then refuses
  I/O). `kernel/usb_storage` speaks BOT (CBW/CSW, tag check, residue, reset recovery) and SCSI (TEST UNIT READY with
  REQUEST SENSE until ready, INQUIRY, READ CAPACITY(10), MODE SENSE(6) for write protect, READ(10)/WRITE(10) of up to
  240 sectors, SYNCHRONIZE CACHE(10)). It cannot import `kernel/xhci` (the import cycle through the console, E0303),
  so it calls xHCI's exported functions by address through `pax_call5` in `boot/io.S`. One defect found on the way:
  the transfer ring's early Link TRB left entries a lap old whose cycle bit matched the current lap, and the
  controller ran into them (USBSTS.HCE, a TD at index 251); `room()` now fills every entry past the early link with
  an empty TRB of the current cycle.
- **kernel/block** (`10e50ab7`, `23cccbfb`, `22b118a9`): eight disks of every driver together (kasumi with its
  target and the stick has five), USB disks named `sdX` after the SATA disks, `removable` from INQUIRY's RMB; the
  USB disks are attached before init runs.
- **Identity** (`751458e8`, `c23db2d1`, `670cea6f`, `4f42a319`): a SATA disk's sysfs model is its first 16 bytes,
  trimmed (R-px78-5); a virtio disk reads its serial by `GET_ID` at bring-up and shows it at
  `/sys/block/vdX/serial`, Linux's place, so the px71 rigs' virtio targets can be allow-listed.
- **The installer** (`48c33648`, `f63b6e36`, `d6e6e116`, `c1128897`, `a065cb8c`): the allow-list (`user/install/
  allow.lu`: parse, judge, the layout in words, the refusal with the line that would allow the disk, `--check`,
  `--allow-list FILE`), the stick identified by its content (R-px78-7), the log on the stick (R-px78-3), a console
  login for an install made from the live medium (R-px78-6), a stop printed once, staging that names the path it
  stopped at. `reboot -p` powers off (`2599ec2d`); `paxfat append` grows a file a step at a time and keeps both FATs
  and FSInfo (`87525e53`).
- **RST** (`4094021e`, `ad427998`, pax#240): a controller of class 01.04 is attached by nothing and named; Intel's
  with the contract's line `AHCI: Intel RST/RAID mode at 00:17.0: switch the firmware to AHCI`. (#240's own text
  suggested `refused: SATA mode is RAID/RST; set AHCI in the firmware`; the contract's wording was used.)
- **The disk suites** (`50fdac20`, `0a415ca2`, pax#241): `kernel_readable` returns nothing under
  `PAX_LINUX=recorded` and says so; a guest that left no log is `FAIL the guest left no log: …`, not a traceback.
- **The kernel's root listing** (`25e3e1ed`): a root whose own tree has a `dev` entry (every live medium's initramfs)
  listed `dev` twice, the tree's and the synthetic one; it now lists the tree's, once, as Linux lists the directory a
  devtmpfs mount covers.
- **The leg** (`554146af`, `b5974fe8`, `50508c52`, `536d9a59`) and its CI wiring (`7c923bf8`, `728a57a0`,
  `d4c61acc`); px74's SuperSpeed row now expects the disk driven (`febb4ace`).
- **Docs:** `docs/INSTALL-METAL.md` (the runbook), `docs/BOOT.md`, `docs/SOURCES.md`, README (`383ce85d`, alone).

### 4.2 The leg, `tests/mpx6-kasumi` (`tests/mpx6-install --only metal`)

The machine: q35, OVMF with a fresh variable store, `-serial none`, 2 GiB; one `qemu-xhci` with the stick
(`usb-storage`, removable, bootindex 0) and `usb-kbd`; an NVMe disk with a foreign GPT and data (1 TB, serial
`S6Z1NJ0W000001`) for CachyOS; three SATA disks on q35's AHCI controller: `Samsung SSD 870 EVO 4TB`
(`S6PXNM0T700001`, one foreign partition), `SanDisk SDSSDH3 512G` (four foreign partitions) and the target
`Samsung SSD 870 EVO 500GB` (`PX78-TARGET-0001`, 500,107,862,016 bytes, sparse, `discard=unmap,detect-zeroes=unmap`).
The Steam disk and the target show the same 16-byte model, `Samsung SSD 870`, so only the serial tells them apart.
The allow-list line is appended to the stick from the host with `paxfat append`, as it would be from CachyOS. Every
screen is read from PAX's exported cells (`pax_screen_state`, `pax_screen_cells`, QMP `memsave` with the machine
stopped), every key typed by QMP `input-send-event`. The record run, hasu block A, TCG as in CI
(`notes/px78/leg/`, `notes/px78/screens/`):

| row | what |
|---|---|
| M0-stick | `tools/mkdisk --usb` and `tools/check-usb`, the allow-list among the stick's files (`stick.check.log`) |
| M1-live-login | the live login through the USB keyboard; a witness file written to `/root`; `/` lists `dev` once |
| M2-check | `pax-install --check`: the target alone on the list; `sda` (the right model, the wrong serial), `sdb` and the NVMe refused by name; the stick refused as a live medium before the list (`02-check.png`) |
| M3 (guided) | the target page (`03-target-page.png`), user `wolf`, games no, the plan (`04-plan.png`), the confirmation line read off the screen and typed back |
| M4-install | `Installation complete`, then `poweroff`: ACPI S5 ends QEMU (`05-complete.png`) |
| M5-witness | NVMe, Steam and SanDisk hashed over their allocated extents (SEEK_DATA/SEEK_HOLE: offset, length, bytes) before boot 1, after it, and after boot 2: identical |
| M6-stick-log | `/pax/logs/install-1.txt` read back from the stick: the inventory, the refusals, the plan, every phase, and the SHA-256 of each written partition's first MiB equal to the target image's; the stick's ESP `fsck.fat -n` clean |
| M7-disk-boot | the stick removed; the disk chosen as from the boot menu; Limine, PAX on `sdc2`, the installed login (`06-disk-login.png`) |
| M8-witness-read | the file written before the reboot reads back; `/home/wolf` there |
| M9-running-root | the installed disk, written on a list by hand, refused as `the running root: /dev/sdc` (`07-disk-check.png`) |
| M10-target-fsck | the root `e2fsck -fn` clean (56 files, 30,523,392 inodes); its GPT `sgdisk -v`: `No problems found` (with sgdisk's caution that partition 2 does not end on a 2048-sector boundary: the root ends on a 4 KiB block, by design); its ESP `fsck.fat -n` clean |

Times (`result.json`): the record run is TCG (CI's accelerator): the install 160.80 s from the confirmation, 170.88
s from the first answer, boot 1 189.85 s, boot 2 17.05 s, the run 210.62 s, 221 s of wall time with the stick's
build (inputs prebuilt; `leg/metal-tcg.log`). Under KVM (`leg/result-kvm.json`, before M10 gained `sgdisk` and
`fsck.fat`): 24.44, 33.63, 50.89, 15.24 and 70.06 s, 80 s of wall time. The stick's sha256 follows its inputs (two
builds of the same inputs give the same image).

Witnesses (sha256 over the allocated extents, before = after):

    nvme     23e7b466f3c8ef15703702419ab725900d2256297deed9de6ce1c77119baafa2  (6 extents)
    steam    e1203a73fb211b26d621cff5b85085bd3a650e2a79f1f0e86d8959f2504e1535  (4 extents)
    sandisk  303fd56ea5315b1f89e6a7dc4b88e1a60b80415b4fbba4be05e48bb91c7b9e08  (10 extents)

### 4.3 The other rows

- `tests/mpx6-install --only allow` (`dec57bb4`, with `I-allow-tool` from `d6e6e116`): I-allow-parse,
  I-allow-bad-line, I-allow-serial, I-allow-root, I-allow-none, I-allow-text, I-allow-layout, I-allow-tool PASS;
  `ui`, `executor`, `prepare`, `snapshot` units PASS at the head.
- `tests/mpx6-install --rows smoke --tier native --firmware bios`: 58 rows PASS, exit 0, 5 min 28 s (I-inventory,
  the no and yes installs and trees, I-session-bios, I-root-nvme, the thirteen fault rows, the units); run again at
  the head after the installer's fixes, its work directory emptied first (the suite assumes a fresh one:
  `install.py` makes `no/source` and stopped on the previous run's, `FileExistsError`).
- `I-root-nvme` (`6fdf530f`): the smoke install's disk booted alone as an NVMe namespace, its own model and serial
  written to a list, `--check` and `--dry-run` refuse it as `the running root: /dev/nvme0n1`. With `I-session`
  (virtio) and the leg's M9 (AHCI), the running root wins over the list on all three buses.
- `tests/mpx6-ahci --tier native --firmware bios --rows pr`: every row PASS, A15-RST among them (kasumi's
  `8086:43d2` at 00:17.0 read as class 01.04 gives the RST line; a `megasas` controller, class 01.04, is named and
  not attached while an AHCI disk beside it is driven).
- `tests/mpx6-usb --tier native --firmware bios`: root, hub and nested topologies, 18 rows each, PASS, after px74's
  SuperSpeed row was changed to expect the disk driven (`febb4ace`; before it, `SuperSpeed enumeration/logging row
  missing`).
- pax#241, on hasu: each of `mpx6-{ext2,nodes,nvme,root}`'s parsers given a missing log ends
  `FAIL the guest left no log: …` with exit 1; `kernel_readable` under `PAX_LINUX=recorded` returns nothing in
  all six disk suites while a kernel is readable.
- `python3 tests/ci-plan`: PASS (310 rows), with the kasumi leg's rows; `python3 tests/ci-budgets.py`: PASS.

### 4.4 Seen red

- **The stick's log stopped at its second append** (the leg's first run): `install log: stopped: paxfat append
  exited -1`. The scratch helper opened `<name>.out` with an exclusive create, and the log's append runs under one
  name at every step. Fixed in `d6e6e116`; `I-allow-tool` runs one name twice.
- **Staging stopped with `io`** (the same run): the live root listed `dev` twice
  (`notes/px78/seen-red/debug-com1-two-dev-entries.log`, a debugging boot with a COM1 log, `ls -la /`), and the
  second `mkdir` of the staged `dev` failed. Fixed in the kernel (`25e3e1ed`); M1 asserts one `dev`.
- **OVMF's UEFI shell** in boot 2 (`seen-red/boot2-no-bootorder-uefi-shell.png`, `leg-3-boot2-uefi-shell.log`):
  R-px78-8.
- **The transfer ring's stale TRBs**: USB writes timed out mid-run with USBSTS.HCE until `room()` filled the entries
  past an early link (§4.1).
- **px74's SuperSpeed row** went red as it should once the disk was driven (`mpx6-usb`, above).
- **The plants** (§4.5).

### 4.5 Plants (dispatched with `-f tier=pr`, never to merge)

| branch | plant | run | red by name |
|---|---|---|---|
| `px78-plant-serial` (`05252815`) | `on_list` compares the model alone | 40967646734 (`mpx6-install mpx6-kasumi`) | `mpx6-install`: `FAIL I-allow-serial: expected 'not on the install allow-list', got ''`; `mpx6-kasumi` (a runner, TCG): `FAIL M2-right-model-wrong-serial: missing 'refused: not on the install allow-list: /dev/sda model=Samsung SSD 870 serial=S6PXNM0T700001'` |
| `px78-plant-root` (`87de51ba`) | `judge` accepts a listed disk before the running-root refusal | 40967650253 (`mpx6-install`) | `mpx6-install`: `FAIL I-allow-root: expected 'the running root', got ''` |

### 4.6 CI

- `mpx6-kasumi` is a job of its own (`.github/workflows/ci.yml`, 120-minute bound, TCG named in its env), planned in
  `tier full` and `tier all` with every suite, and in `tier pr` when its paths change (`tools/ci-tiers.map`:
  `kernel/{usb_storage,xhci,ahci,block}`, `user/install`, `user/disktools`, the stick's tools and files, its own
  scripts). Its first runner run was the serial plant's (40967646734): the inputs built in 3.5 minutes and the stick
  booted to the live login under TCG on a GitHub runner four minutes after the job started, then M2 went red as
  planted. It keeps the screens, the stick's log, `result.json` and the oracles' output as the `pax-mpx6-kasumi`
  artifact.
- `tests/ci-plan` holds the planner to it (three px78 rows, `kernel/usb_storage` reaching `mpx6-firmware` too, whose
  `tools/usb-session` now drives a disk; the installer's, the disk tools', AHCI's and the lope rows now reach it);
  `tools/ci-plan`'s P4 checks pass (`PAX_LEGS`, `--tier`/`--firmware` taken and said).
- The PR's own run and the `tier full` at its final head are the orchestrator's to read (the hand-back names the run
  id read once at opening).

## 5. Done-when

### 5.1 Rulings (recommended and implemented, not decided)

- **R-px78-1, the target disk:** the maintainer's. Answered 2026-10-29: a SATA SSD plugged in later, not `sdb`; its
  line goes on the stick then. The stick's default list (`boot/install-targets`) names no disk; the leg uses QEMU
  serials (`PX78-TARGET-0001`).
- **R-px78-2, where the list lives:** A, a file on the stick, `/pax/install-targets` on the ESP, editable from any OS;
  `--allow-list FILE` for tests and for an install from another medium.
- **R-px78-3, the log:** A, the ESP, `/pax/logs/install-<n>.txt`, appended by `paxfat append` after every step;
  a failed append stops the log, never the install.
- **R-px78-4, the NVMe as never-a-target:** as recommended: a disk not on the list is refused whatever it holds, its
  layout named (`2 partitions PAX did not write`), and the stick's default file names nothing. The running-root
  refusal is separate and first: proven on virtio (`I-session`), NVMe (`I-root-nvme`) and AHCI (M9).
- **R-px78-5 (new), the SATA model's spelling:** A, Linux's 16 bytes in `/sys/block/sdX/device/model`, so a line
  copied from CachyOS matches; B, the full ATA model (lines from Linux never match a long model). Recommended A. It
  reverses R-px75b-4, which kept the whole trimmed ATA model and named the 16-byte difference as a departure; the
  boot line still prints the whole model.
- **R-px78-6 (new), the installed system's login:** A, an install from a tree carrying `/etc/pax-live-login` gets a
  console login (`/etc/pax-login`: root, or an account in `/etc/passwd` by `su`, no passwords in this preview); B,
  copy the live entry (passwordless root on the installed disk, which `docs/BOOT.md` forbids). Recommended A.
- **R-px78-7 (new), how the stick is known:** A, by content: the one disk whose first partition is FAT holding
  `/boot/initramfs.cpio` (a copy of the stick is refused the same way); B, by transport or `removable` (a USB SSD is
  neither a stick nor removable, and a stick can clear RMB). Recommended A.
- **R-px78-8 (new), how the leg boots the disk after the install:** A, the disk first in QEMU's boot order, the
  boot menu's choice, with boot 1's variable store kept; B, a fresh variable store (a machine that never saw the
  stick). Recommended A, and the runbook says to choose the disk from the F8 menu.

### 5.2 Checklist

- [x] Item 1, the allow-list by model and serial from `/pax/install-targets` on the stick; every other disk refused
  by name with its identity; running root, mounted, read-only and the stick refused before the list; an empty or
  missing list refuses all and says how to add a line; the typed confirmation unchanged. Pure rows (`I-allow-*`) and
  the QEMU leg's right-model-wrong-serial refusal (M2).
- [x] Item 2, RST refused by name (pax#240): A15-RST over the configuration bytes and the boot-log line.
- [x] Item 3, pax#241: `PAX_LINUX=recorded` honoured; a missing guest log is a named FAIL.
- [x] Item 4, the install log on the stick (ESP `/pax/logs/install-<n>.txt`), flushed per step, ending with the first
  MiB's sha256 of each written partition (M6 holds it to the target image).
- [x] Item 5, the leg (`tests/mpx6-kasumi`, `tier full` and every `tier pr` its paths select): OVMF, `-serial none`,
  the stick on xHCI, the NVMe for CachyOS, the SATA disks, screens from PAX's cells; install, power off, the stick
  removed, the disk booted, login, the file read back; NVMe and the other SATA disks byte-identical; install time
  recorded.
- [x] Item 6, `docs/INSTALL-METAL.md`, its first metal step the coordinator's (plug in the SSD, read its model and
  serial in CachyOS, write the line on the stick).
- [x] Item 7, two plants red by name; README (`383ce85d`, alone); this note; the issues listed, none closed.
- [ ] The orchestrator: the `full-matrix` label at the final head and a green `tier full`; the merge; closing
  pax#240 and pax#241 by hand (and #139, #152 if judged proven).

### 5.3 Departures and limits named

- The target is the real capacity of an 870 EVO 500GB (500,107,862,016 bytes), not 512 GB; the leg has three SATA
  disks, not two (kasumi's two and the target), and the witness covers all three non-targets.
- The leg runs under KVM on hasu and under TCG in CI (`PAX_METAL_ACCEL`, named in the job): the runner's
  `/dev/kvm` is not the job's.
- The kernel's `user: exec …` and `syscall 273/334: -ENOSYS` lines share the console with the installer: on a small
  grid they push the plan up the screen. The plan and the confirmation stay on kasumi's 3840×2160 GOP; a quieter live
  console is a follow-on.
- A stick removed and plugged in again is not re-attached (its record says removed and refuses I/O).
- Real hardware: nothing here was run on kasumi. The runbook is for the maintainer's metal window.

### 5.4 Issues

To close at the merge (by hand): **pax#240** (A15-RST, `4094021e`), **pax#241** (`50fdac20`, `0a415ca2`). The leg
bears on two more, the orchestrator's call: **pax#139** (the GPT and file systems written from inside PAX: the leg's
M10 holds the installed disk to `sgdisk -v`, `fsck.fat -n` and `e2fsck -fn`) and **pax#152** (an installer that
writes the disk from PAX and the result boots without the medium: M7–M8 under UEFI on AHCI; px71's rows hold the
tree and the BIOS session).

To file (not filed by the lane): a quiet console for the live medium's installer (the exec trace lines above);
re-attaching a USB disk plugged in again; `getrusage` (the installer's peak RSS, still ENOSYS).
