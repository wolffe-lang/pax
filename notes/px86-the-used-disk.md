# px86 — the used disk: clear the BIOS boot partition before Limine (P6)

Contract: `wolf/sprints/pax/86-the-used-disk/px86-the-used-disk.md` (crawl 54), launched 2026-10-31 from the
maintainer's install on kasumi with `pax-install-kasumi-197330ad.img` (pax trunk `8495bdc0`'s installer). The guided
install stopped at its `limine` phase: Limine's `bios-install` refused partition 3, because the 860 held two
partitions from an older install, the first at sector 2048, so that file system's first sectors lay exactly in PAX's
BIOS boot partition (bytes [1 MiB, 2 MiB)), and nothing in the installer cleared it. Every QEMU target before this lane
was blank there. Now the installer zeroes partition 3, and the other places where a used disk's old signature would
still be read, after the new table and before any formatter or Limine writes; every phase is in the plan and the disk
log. Footprint: module (`user/install`, the installer's tests, `tools/used-disk`, docs, notes).

The maintainer's disk serial is written `<kasumi-serial>` in every file under `notes/px86/`: this repository is
public. The staged stick carries it, as its sha256 below covers.

## 1. Forbidden, and what was read

No kernel's, firmware's, bootloader's, emulator's, driver's or partition tool's source was read: not Limine's (its
`bios-install` was run as a binary and its messages observed, `notes/px86/logs/limine-probe.log`), not util-linux's
(`wipefs`, `blkid`, `mkswap` run as black boxes), not dosfstools', e2fsprogs', mtools' or xorriso's. Read: the
contract, the lane rules of 2026-10-31, RULES §1–§10, `sprints/pax/index.md`'s standing rules, the px77c, px78 and
px78b notes and px78b's recipe scripts (`notes/px78b/scripts/`), PAX's tree (`user/install/{plan,execute,main,
inventory,allow}.lu`, `user/disktools/{paxgpt,paxfat,paxext2}/main.lu`'s write paths, `tests/mpx6-install`,
`tests/mpx6-install.d/{install,metal,verify,gap,executor,planner}.*`, `tests/mpx6-kasumi`, `tools/{mkgpt,mkinstall,
mkdistribution,ci-plan,ci-tiers.map}`, `.github/workflows/ci.yml`'s two install jobs, `docs/{INSTALL-METAL,BOOT}.md`,
the README), the crawl's entries for the 860 (its inventory: 1 TB, two old partitions; the screen as the maintainer
read it) and the planning repo's `wolf/tools/lane-audit.sh`. Facts used from published documentation, not from any
source: the Linux swap partition type GUID (the Discoverable Partitions Specification), the ISO 9660 primary volume
descriptor at sector 16 of 2048 bytes (byte 32768), `wipefs(8)` and `blkid(8)`'s options.

kasumi was not touched (the maintainer's). hasu block A was held under both lock names for each run alone
(`notes/px86/hasu/ctr.sh`), shared with px85; hasu's `:9364`, `:9308` and the maintainer's data were not touched;
nothing was installed; no label, dispatch, merge, issue or release; no attribution trailers. On nomad only
`~/lanes/px86/` (the worktrees `pax` and `plant`, registered in the org checkout's git) and one new file in
`~/pax-smoke/` were written, besides one planner path list written to `/tmp` by mistake and removed at once.

## 2. Inputs, verified

- **Base** pax trunk `8495bdc0` (its installer is 197330ad's: between the two only `tools/qemu-halt`, tests and
  notes changed). Branch `px86`; the Mac worktree `~/lanes/px86/pax` for git, `gh` and the staged stick, the branch
  asserted before every commit. On hasu, clones from GitHub under `/home/mfwolffe/lanes/px86/`: `red` (the
  tests-only heads), `green` (the fix), `stick` (the stick's head), `plant`, `gaunt` (the gauntlet's fresh clone).
- **Toolchain** wolf 0.2.35 (`4cc4045b…`), Limine 12.9.1 (`limine-binary.tar.gz` `5cdebc51…`), each read twice
  (`notes/px86/stick/archive-reads.txt`, `limine-read-{1,2}.sha256`); `base-dev.cpio` `098b918e…`. The inputs were
  px77c's, copied (never moved) from `/home/mfwolffe/lanes/px77c/` (px78b's hasu directory is pruned): `cache`,
  `build/inputs`, `inputs/{base-dev.cpio,limine-download,lope-local}` (lope-local holds the pin `e6f623c7`).
- **Containers** `localhost/px75-ubuntu:2` (`6bab9e96`) for the units, the inputs and the release pair;
  `localhost/px78-ubuntu:1` (`51bb7b38`) for every row that runs `sgdisk`, `wipefs` or `blkid` and for the legs:
  QEMU 8.2.2, OVMF 2024.02, dosfstools 4.2, e2fsprogs 1.47.0, util-linux 2.39.3, mtools 4.0.43, xorriso 1.5.6,
  gdisk 1.0.10. Neither image has `mkntfs`, so the contract's NTFS case did not run (a lane installs nothing).
  Every container `--memory 12g`, `taskset -c 0-5` inside, both block-A lock names held, the block's name outside.
- **The block** was shared with px85 (three chains of five-to-seven-minute holds). The first waits polled
  `flock -n` every 30 s and lost every race to px85's blocking waits for ten minutes; from then on every wait is a
  blocking `flock -w 240` that prints at each expiry, and each chain takes the block once for all its steps
  (`notes/px86/hasu/`), never idle.

Commits on `px86` (the prediction first, the failing rows before the fix):

- `a4b00f88` notes/px86/prediction.txt: the used disk's rows, before the first change
- `0e9f227d` tools/used-disk: a used disk as the 860 came, and the signature oracle
- `b53778dd` tests/mpx6-install: used targets (fat32, ext4, iso) install and leave no old signature
- `575defb3` tests/mpx6-install.d/metal.py: the 860 target, used; Limine's refusal named; M11-signatures
- `15979821` tests/mpx6-kasumi: the leg again onto a used 860
- `aa992464` tests/mpx6-install.d/planner.lu: the zero phases' ranges, named by the plan
- `59e7eb1b` tests/mpx6-install.d/executor: each zero phase writes its ranges and nothing else
- `50aa4b15` tests/mpx6-install.d/install.py: a used disk's token from --dry-run (its identity names the old partitions)
- `3da487e5` user/install/plan.lu: the zero phases (wipes), named by the plan
- `76e570fc` user/install/execute.lu: zero partition 3 and the old disk's signature places before any formatter or Limine
- `5e5dd7be`, `407dbc01` the metal leg's and the used rows' stops name Limine's `error:` line
- `3308e975` tests/mpx6-install.d/planner.lu: read the spans' ints, never move a span out
- `3fea068b` tests/mpx6-install.d/executor.py: the four phases together are I-zero-all
- `adb53141` tools/used-disk: hold each partition to its signature kinds and PAX's label, not one wipefs row
  (the stick's head)
- `d7020e63`, `6b9183fe`, `c596048a` docs/INSTALL-METAL.md, docs/BOOT.md, README (a README-only commit)
- `15f60bd0`, `e72699c0`, `c4367018`, `82bdf001`, `63da5bf7` and this note: the evidence under `notes/px86/`

## 3. Prediction, scored

`notes/px86/prediction.txt` (`a4b00f88`, 00:33Z, pushed before the first change and before any guest ran):

| predicted | found |
|---|---|
| The 860 legs at the tests-only head, fat32 and ext4: M0–M3 PASS, FAIL M4-install by name with Limine's text, then `pax-install: stopped: command_failed`, the phase log ending `limine failed` | **right**, both (`red/leg-used-{fat32,ext4}/05-bad.txt`): `pax-install: limine: exit 1; … error: The partition selected to install the BIOS boot code to contains a recognised filesystem. … Install failed, undoing work...`, then the stop. Limine's own text says "partition" and "THIS": the maintainer's "parition" and "THIUS" were his typing |
| the other disks' witnesses unchanged even so | **not measured**: the leg ends at its FAIL line, before M5 compares |
| the unattended rows I-used-fat32 and -ext4 red by name | **wrong at first, then right.** The first run (`59e7eb1b`) was red for another reason, `pax-install: before writes: unconfirmed`: a used disk's identity names its old partitions (`inventory.lu`'s topology, `;vdb1:254:17:1:2048:208896;…`), so the rows' precomputed token cannot match; they now take it from `--dry-run`, as `docs/BOOT.md`'s scripted path does (`50aa4b15`). At `50aa4b15` both red by Limine's text (`logs/chain-after.log`, red2) |
| I-used-iso: Limine does not refuse, the install completes, red at the signature oracle (`iso9660` at byte 32768) | **right on the mechanism**, the row red at its own phase-set expectation first (the zero phases are absent at base); the as-left oracle then reads `iso9660@32769` on the whole disk. **Not predicted:** Limine took the old descriptor for an isohybrid: `Detected ISOHYBRID with a GUID partition table (GPT). Converting to MBR for improved compatibility... Cannot convert partition type for partition 2, will not convert GPT.` (§4.3) |
| the new units red as a compile error, wolf build exit 2 | **right**: `error[E0301]: nothing named wipes is in scope`, exit 2, both units |
| green: the 860 legs M0–M11 PASS under KVM, the install 35–70 s from the yes, the leg 80–150 s | **right**: 48.1 / 92.7 s (fat32, the branch's leg), 37.5 / 93.7 s and 35.1 / 88.5 s (the stick's legs, fat32 and ext4) |
| the zero phases under 1 s together, about 7 MiB | **wrong on the size, unmeasured on the time**: 6,212,096 bytes (5.9 MiB) on the 1 TB disk and on 512 MiB alike (the tail slack is 3,584 bytes on both); the disk log carries no clock per phase |
| the oracle: the whole disk PMBR and gpt, p1 vfat, p2 ext2, p3 nothing, on every case | **right on what the disks hold; my oracle's first form was wrong**: wipefs lists a FAT32 boot sector three times (`vfat` at 0, 82, 510), so a check of one row per partition went red on a green install; it now holds the kinds and blkid's label (`adb53141`) |
| the unit: zero-bios writes exactly [1048576, 2097152) and nothing but its two log records; the other phases their ranges | **right** on 512 MiB and on 1 TB (I-zero-bios, -esp, -root, -gap, -all) |
| the existing rows unchanged: the blank 870 leg, mpx6-install's smoke rows, gap.py's oracle | see §4.6, the gauntlet |
| R-px86-1's measurement: paxfat writes the ESP's first 1,049,600 bytes, paxext2 the root's first MiB, both leave their last MiB; nothing writes the gap or the tail slack | **right** to the byte (`logs/chain-after.log`, coverage): 0 of 1,048,576 old bytes left in either first MiB, all of each last MiB, all 48,128 + 917,504 of the gap, all 3,584 of the tail slack, all of partition 3 |
| the stick: 794,820,608 bytes, a second build byte-identical, six files, the legs green, the summary naming the 860 | **right** on each |
| the plant: I-used-fat32 and -ext4 red by Limine's text, I-zero-bios red | **right** (§4.5) |

## 4. Evidence index

### 4.1 The change

After `gpt` (the new table) and before `fat`, `root` or `limine`, `execute_plan` runs four zero phases of its own
(`plan.lu`'s `wipes`, `execute.lu`'s `zero_ranges`): through the target's claimed descriptor, 64 KiB writes of
zeros, an fsync, every range read back as zeros, a `started` and a `durable` record in the disk log, `phase zero-…:
durable` on the screen and in the stick's log. The plan names each with its byte ranges (`plan_body`, so the screen,
`--dry-run` and the log's record of what was erased all carry them); on the 860:

```
zero-bios [1048576,2097152) (partition 3 whole, before Limine)
zero-esp [2097152,3145728) [68157440,69206016) (partition 1's first and last MiB)
zero-root [69206016,70254592) [1000203816960,1000204865536) (partition 2's first and last MiB)
zero-gap [17408,65536) [131072,1048576) [1000204865536,1000204869120) (the first MiB outside the table and the log; the tail before the backup)
```

Limine's `--force` is never passed. The ranges never touch the primary table `[0, 17408)`, the log `[65536,
131072)` or the backup table (`planner.lu`'s I-wipe-span holds every size from the 77,611,520-byte minimum to 18.7
TB to that, the ranges also pairwise disjoint). When the ext2 bound leaves capacity unused, zero-gap also takes the
last MiB before the tail. `gap.py`'s oracle has always zeroed `[1 MiB, 2 MiB)` in its candidate before running
Linux's Limine on it: the executor now guarantees what the oracle assumed.

### 4.2 Rows, red then green (hasu block A)

| row | red | green |
|---|---|---|
| planner I-wipe-plan, I-wipe-span | `59e7eb1b`: E0301, exit 2 | PASS (`logs/green-units2.log`) |
| executor I-zero-bios, -esp, -root, -gap, -all, 512 MiB and 1 TB | `59e7eb1b`: E0301, exit 2 | PASS |
| I-used-fat32, -ext4 (512 MiB virtio, TCG) | `50aa4b15`: Limine's refusal by name | PASS, then verify.py, gap.py (`Limine envelopes [0, 423, 1048576, 1071464]`) and I-used-signatures |
| I-used-iso | `50aa4b15`: past the install, `iso9660@32769` left on the whole disk | PASS, the descriptor gone |
| the kasumi leg, 860 used fat32 and ext4 (KVM) | `59e7eb1b`: FAIL M4-install, Limine refused the BIOS boot partition | M0–M11 PASS (`green/leg-used-fat32/`, `stick/leg-stick-*`) |
| the kasumi leg, blank 870 (KVM) | `59e7eb1b`: M4 PASS (25.1 s), FAIL M6-stick-log `missing 'phase zero-bios: durable'` (the new needle) | PASS in the gauntlet (§4.6) |

### 4.3 Limine observed (`notes/px86/logs/limine-probe.log`)

Limine 12.9.1's `bios-install IMG 3` on PAX's table (sgdisk: p3 bios 2048–4095, p1 4096–135167, p2 from 135168)
over an old file system at byte 1048576: FAT32, FAT16, ext4 and ext2 each refused, exit 1, on stderr, the image
unchanged after `Install failed, undoing work...`; an old swap area and blank bytes were accepted. A disk once
written with a hybrid ISO, its table replaced: Limine installed, but first printed `Detected ISOHYBRID with a GUID
partition table (GPT). Converting to MBR for improved compatibility...`, and kept PAX's GPT only because `Cannot
convert partition type for partition 2`. The trigger is the old ISO 9660 descriptor at byte 32768, in the gap no
PAX phase wrote before px86; zero-gap clears it, and I-used-iso holds the result.

### 4.4 R-px86-1, measured

Each formatter alone on a pattern-filled 64 GiB image (`notes/px86/hasu/coverage.py`, `logs/chain-after.log`):
the GPT writes `[0, 17408)` and the backup table; paxfat writes the ESP's first MiB whole (its 32 reserved sectors
and two FATs of 1,009 sectors) and leaves its last MiB; paxext2 writes the root's first MiB whole (block 0, the
group descriptors, the bitmaps, the inode table) and leaves its last MiB; nothing writes `[17408, 65536)`,
`[131072, 1048576)`, partition 3 or the 3,584 bytes between the root's end and the backup table. Hence zero-esp and
zero-root's last MiB and all of zero-gap; their first MiBs are written anyway, and zeroing them keeps the guarantee
independent of what a formatter happens to write. What stays: the old bytes inside the partitions, which no probe
reads as PAX's (an old ext4's backup superblocks inside the new root, an old FAT's clusters inside the new ESP); only
a whole-disk wipe clears those, about half an hour of writes for 1 TB (estimated), not done.

### 4.5 The plant

`px86-plant-used` (`219dda70`: this branch's `c596048a` plus one commit, zero-bios logged durable but writing
nothing), run locally as a module lane's plant is (RULES §7), `logs/chain-after.log`:

- `FAIL I-zero-bios: 536870912 bytes: a byte outside the phase changed or inside it is not zero, in [131072,1179648)`
  (executor.py), exit 1;
- `FAIL I-used-fat32: the install onto the used disk stopped: pax-install: limine: exit 1; … a recognised
  filesystem. | Install failed, undoing work...`, partition 3 as left still `OLD-ESP`; I-used-ext4 the same, partition
  3 still `old-root`;
- I-used-iso past the install and red at gap.py: `AssertionError: ([0, 423, 1048576, 1071464], ('0', '423',
  '1048576', '1071465'))`: PAX's Limine envelope over old bytes in partition 3 differs from the oracle's over zeros;
- the 860 leg (fat32, KVM): `FAIL M4-install: Limine refused the BIOS boot partition: pax-install: limine: exit 1; …
  error: The partition selected to install the BIOS boot code to contains | a recognised filesystem. | Install
  failed, undoing work...`, exit 1.

The draft PR is the plant's record; nothing of it merges.

### 4.6 The gauntlet

One wrapper (`notes/px86/hasu/gauntlet.sh`) at the head named below, a fresh clone, fresh work directories, one
hold of block A by both names; it stops at the first nonzero step and prints each step's `END`. The commits after it
are this note's and its evidence's only.

GAUNTLET_RESULT

### 4.7 The stick (the coordinator's first deliverable, handed back at 01:30Z)

`~/pax-smoke/pax-install-kasumi-adb53141.img` on nomad, read-only, 794,820,608 bytes, sha256
`ce86a7e699111eccc3a71570e7d19b04104c31358f8df7fa6200d899a1c280ac`, read six times, all equal: twice after the build
and twice at staging on hasu (`stick/kasumi-hasu-{build,stage}-read-{1,2}.sha256`), twice on nomad
(`stick/image-nomad-read-{1,2}.sha256`); the coordinator read it twice more. Built at `adb53141` by px78b's recipe
(`hasu/stick.sh`): the release pair by `tools/mkdistribution`, the live payload (`stick/sout/live-payload.txt`),
`tools/mkdisk --usb`, `tools/check-usb` on six files (`stick/slogs/usb-check.log`), a second build byte-identical, the
EFI and MBR corruptions refused by name; the plain stick `8a909608…` (`stick/stick-plain-read-{1,2}.sha256`). The
kernel is 197330ad's (`/boot/pax` `3160e4f5…`); the initramfs differs by the installer. The 860's line appended to a
copy by the stick's own `paxfat`, the file read back equal to `boot/install-targets` plus that line
(`stick/install-targets.expected`, `c21b04ae…` as on 197330ad's), `check-usb` again, the copy renamed and made
read-only. Qualified on copies (each `stick-at-start.sha256` equal to the staged digest) by the head's own
`metal.py` in run mode, `PAX_METAL_TARGET=860 PAX_METAL_TARGET_SERIAL=<kasumi-serial> PAX_METAL_LISTED=1`, KVM:
used fat32 M0–M11 PASS, the install 37.5 s, the leg 93.7 s; used ext4 M0–M11 PASS, 35.1 s, 88.5 s. The screen:

```
Erase Samsung SSD 860, serial <kasumi-serial> (1.0 TB, /dev/sdc), and install PAX?
The root file system is ext2 without a journal.
Type yes to install; anything else cancels: pax-install>
```

The px78b and px77c owed item "`tests/mpx6-kasumi` cannot be pointed at a given image with its line already
written" is closed by `PAX_METAL_LISTED` and `PAX_METAL_TARGET_SERIAL`: no lane-local copy of `metal.py` was made.

## 5. Done-when

### 5.1 Rulings (recommended and implemented)

- **R-px86-1, clear more than partition 3:** A, partition 3 alone (what the contract requires); B, A and the first
  and last MiB of partitions 1 and 2 (the contract's suggestion); C, B and the gap and the tail: `[17408, 65536)`,
  `[131072, 1048576)` and the sectors between the root's end and the backup table (the old ISO 9660 descriptor that
  makes Limine try to convert the table; an old partition's last sector); D, the whole disk (half an hour for 1 TB,
  and PAX has no discard). Recommended C, implemented; the coordinator took it (2026-11-01).

### 5.2 Checklist

- [x] Item 1, reproduced red by name: the 860-shaped target (1 TB sparse, an old GPT, partition 1 at sector 2048
  with a real FAT32 or ext4, a second partition) stops at the `limine` phase with Limine's message at `8495bdc0`'s
  installer. NTFS: not run (no `mkntfs` in either image).
- [x] Item 2, partition 3 zeroed whole before Limine, logged and named by the plan; `--force` never passed;
  R-px86-1 C.
- [x] Item 3, the item 1 cases green through M0–M11 under KVM with every other disk's witness unchanged; the unit
  row (I-zero-bios: exactly `[1 MiB, 2 MiB)` and nothing else); the existing rows unchanged (§4.6).
- [x] Item 4, the stick, qualified and staged, handed back before the PR.
- [x] Item 5, `docs/INSTALL-METAL.md`, `docs/BOOT.md` ("A used disk") and the README's installer section say a used
  disk is fine; the line for `~/pax-smoke/INSTALL.txt` went to the coordinator, who wrote it.
- [x] Item 6, this note, the plant (`px86-plant-used`, a draft PR), the PR, the audit.
- [x] README read against the pass: the installer paragraph, the test paragraph and the tools row moved and are
  refreshed (`c596048a`, a README-only commit); nothing else in it moved.

### 5.3 Departures and limits

- NTFS was not laid down: neither image has `mkntfs`. A Windows disk's usual first partition at 1 MiB is a FAT32
  ESP, the fat32 case.
- The 860's old layout is not known: the cases are the common ones (an old ESP and root; an old root and swap; an
  old live image). Any file system at sector 2048 is now zeroed before Limine looks.
- The zero phases' time is not measured on its own (the disk log has no clock); the installs onto the used 860 took
  35–48 s from the yes under KVM, the blank 870's 25.1 s at base.
- CI runs the used 860 leg under TCG in `mpx6-kasumi` after the blank leg; its time there is unmeasured until the
  PR's run (`tier pr` selects `mpx6-ahci`, `mpx6-install`, `mpx6-kasumi` for these paths, `tools/ci-plan`).
- Real hardware: nothing here ran on kasumi.

### 5.4 Issues

Filed or closed: none. Owed to file (pax), the coordinator's call:
- NTFS among the used cases, with an image that carries `mkntfs`.
- The disk log has no clock per phase: a phase's time on metal is not recoverable from the target or the stick.
