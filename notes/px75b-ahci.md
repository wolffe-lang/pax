# px75b — AHCI: the SATA disks kasumi actually has (P6)

Crawl 54. Contract `sprints/pax/75b-ahci/px75b-ahci.md`, with its
2026-10-28 addendum (the waits are deadlines on px76's clock API, behind
a local PIT shim until px76 merges; R-px75b-2 recommends B). Branch
`px75b` from trunk `6ccfe3fe`, rebased onto trunk `96b7f90f` (px77a's
merge, notes only) before the PR. Two models wrote it: a Codex lane
(GPT-6-Astra) built the driver, the harness, the rows and the plants and
handed back at `9355a03f` (rebased `44f86075`) with a detached
qualification job running; it then hit its weekly limit. A Claude lane
(Opus 5.5) took over from that head: it found the cause of that job's
red, reviewed the source against the specifications, fixed two defects
in the clock shim (R-px75b-7), strengthened one row, measured and wired
R-px75b-6, ran the remaining legs and regressions, and wrote this note.
The prediction was committed first (`c50e8b75`,
`notes/px75b/prediction.txt`), before the first source change
(`2a56dbb5`) and before the guest was measured.

## 1. Forbidden, and what was read

No kernel's, firmware's, emulator's or driver's source: none of Linux's
`drivers/ata/` (libahci, libata), `drivers/scsi/` (sd), `block/`, no BSD
`ahci(4)`, no SeaBIOS or EDK2 AHCI driver, no QEMU `hw/ide/`. Read: the
Serial ATA AHCI 1.3.1 specification (sha256 `3bbd4b7f…`), ATA/ATAPI
Command Set 4, T13 draft revision 18 (`26aaf3ef…`), Serial ATA 1.0a for
the FIS layouts (`be534520…`; SATA 3.x is not publicly released), the
PCI Local Bus 3.0 specification (`74d05cd7…`), and, for the clock shim,
the Intel 8254 data sheet as `kernel/timer` already cites it. The
sections each fact comes from are named in `kernel/ahci/ahci.lu`'s
header and in `docs/SOURCES.md` (px75b). The takeover re-read the four
digests from the extracts the first lane downloaded (all four equal) and
checked the clauses its review leaned on in that text: CAP.NP and
CAP.NCS 0's based (§3.1.1), DBC 0's based with bit 0 set (§4.2.3.3), the
COMRESET's 1 ms (§10.4.2) and the ownership request (§10.6.3).

Run as black boxes: QEMU 8.2.2 (Ubuntu 24.04, CI's) with `ahci`,
`ide-hd`, `blkdebug` and q35's `pit=off`; hasu's installed Linux 7.2.4
(NixOS) as the guest, with px79's probe, px75's probe, this lane's
`user/elf/ahci.c`, boreutils' `cat`, pelt and the installer. Also read:
PAX's own tree (`kernel/{block,procfs,files,nvme,pci,timer}`,
`kernel/kmain_console.lu`, the disk suites, `tools/ci-plan`,
`tools/ci-tiers.map`, `.github/workflows/ci.yml`), px75's and px77a's
notes, px76's contract (its paragraph on kasumi's PIT), and CI's logs.

Work on hasu, block B (CPUs 6–11 by taskset inside the container, 12
GiB), under `flock ~/lanes/hasu-block-B.lock`; the Mac worktree for git
only; kasumi never touched.

## 2. Inputs, verified

- **Toolchain.** wolf 0.2.35 (pin `cf0c13d`) and limine 12.9.1, both by
  digest (`tools/fetch-wolf`, `tools/fetch-limine`); QEMU 8.2.2. The rig
  is px75's (`notes/px75/rig`) in the image `localhost/px75b-ubuntu:1`:
  px75's `localhost/px75-ubuntu:2` plus `gdisk`, `fdisk` and `strace`,
  the three packages CI installs for mpx6-install, mpx6-disktools and
  mpx6-fsck and px75's image lacks (`~/lanes/px75b/rig/image/Containerfile`
  on hasu; built inside the container, nothing on the host).
- **kasumi** (read by the orchestrator, 2026-10-28, the contract): Intel
  500-series AHCI `8086:43d2` at `00:17.0`, ABAR `0xa4e02000`, 32-bit,
  2 KiB, MSI ×1, `ata1`–`ata6`; the Samsung 870 EVO 4T on `ata5` (`sda`);
  ASMedia ASM1061 `1b21:0612` at `6e:00.0`, `ata7`–`ata8`, the SanDisk
  512G on `ata8` (`sdb`); the NVMe is px75's. px76's contract: the
  500-series PCH can gate the 8254 in S0; Linux there lists `tsc hpet
  acpi_pm` and no `pit`.
- **The first lane's claims, each checked, not taken.** Its plants' runs
  are red by name (§4.5). Its native-UEFI and release legs at
  `9355a03f` were green in `logs/ahci-native-uefi.log` and
  `logs/ahci-release.log` (qualify2 reached its regression step only
  after both; `set -e`); all four legs were run again at the final head
  (§4.1). Its "no-write" row, the LBA48 row, the throughput, the name
  order and the 4Kn refusal are rows of the suite, read in the logs.
  Its AHCI-root measurement (`logs/users-ahci-root.log`, `.rc` 0) is
  §4.6's first line. Its qualify2 red is §4.4.

## 3. Prediction, scored

`notes/px75b/prediction.txt` (`c50e8b75`), written before the first
source change:

| prediction | measured | |
|---|---|---|
| QEMU 8.2's AHCI reports CAP2.BOH clear, so the handoff needs a synthetic witness beside QEMU's | `BOH=0` on every controller line; the handoff's code path is not reached under QEMU (no synthetic witness was built: §5's limits) | right; the witness owed |
| at most 128 KiB (256 sectors) a command, 32 PRDT entries of one page, DBC the bytes less one; a PRDT entry could carry 4 MiB | as built (`command`); A4's 22 writes of 1 byte to 1 MiB at aligned and unaligned offsets, each read back with 0 bytes differing, line for line the guest's | right |
| one slot, polled, no NCQ | as built | right |
| beside px75's native 684 MB/s write and 706 MB/s read: AHCI 400–700 write, 400–800 read on the same tmpfs-backed 1 GiB image | native BIOS 639.1 / 642.9, native UEFI 627.9 / 627.9; release BIOS 1206.4 / 1118.5, release UEFI 1179.9 / 1106.9 MB/s (KVM, hasu) | native inside the band; release above it (not predicted) |
| Linux names in controller PCI order, then port order, holes and ATAPI taking no letter: controller A's ports 1 and 4 `sda`, `sdb`, controller B's port 2 `sdc`; probe order may race | the guest's record: `sda` 8:0, `sdb` 8:16, `sdc` 8:32 for exactly those ports (A2, and A1's inventory pairs each name with its serial) | right (the race unmeasured: one recorded order) |
| R-px75b-1 polled with interrupts masked; R-px75b-3 the ASM1061 as generic AHCI | implemented, as recommended | |

Not predicted: that the bootstrap clock would need a refusal for a PIT
that does not count, nor its overflow (R-px75b-7).

## 4. Evidence index

All on hasu, block B, QEMU 8.2.2, KVM unless TCG is named; the Linux side
is the guest's record (`tests/mpx6-ahci.d/linux/`, hasu's Linux 7.2.4 on
QEMU 8.2.2, recorded by the first lane in `logs/test8.log` with
`--record`), as CI uses it. Logs are under `~/lanes/px75b/logs/` on hasu.

### 4.1 tests/mpx6-ahci, every row (the machine: two `ahci` controllers, disks on ports 1 and 4 of the first and port 2 of the second, an NVMe disk, q35's ICH9 controller with its CD-ROM)

| row | holds |
|---|---|
| A0-build | kmain_console on the leg's tier; a build or guest failure is a FAIL, never exit 2 |
| A1-identify-inventory | the real installer's `--inventory` (`user/install`), every line of its report the guest's: device, size, sector, state, identity numbers, model and serial; four identities, the internal-space serial `PX75B B2 INNER` among them (strengthened at `217bff07` from the model lines alone) |
| A1-identify-files | `/sys/block/{sda,sdb,sdc,nvme0n1}/device/{model,serial}` the guest's (R-px75b-4: padding trimmed, the serial byte for byte) |
| A2-linux-name-order | `sda` 8:0, `sdb` 8:16, `sdc` 8:32 across the two controllers and their gaps, `sda`'s size, its `ro` |
| A3/A5-before/after-differential | each disk's 64 MiB read whole, FNV the guest's, before and after the writes |
| A4-prdt-readback | 22 writes, 1 byte to 1 MiB at aligned and unaligned offsets (raw I/O through kernel/block's 128 KiB pieces), each read back, 0 bytes differing, line for line the guest's |
| A5-image-differential | the four images' sha256 after the session equal the guest's |
| A6-no-write | a live boot (`user/usb-login.sh`) with three AHCI disks and one NVMe disk, login as root, `pax-install --inventory`, logout: every image's sha256 unchanged |
| A7-LBA48 | 128 KiB written and read at byte 2^41 (sector 2^32) of a 3 TiB sparse image, the low sentinel intact, both ranges the guest's bytes |
| A8-taskfile-error | blkdebug's EIO at sector 4096: the four reads' answers the guest's, the TFES error named, the next read good |
| A9-512e-ioctls | a 512/4096 disk's block ioctls the guest's (BLKSSZGET 512, BLKPBSZGET and BLKIOMIN 4096, HDIO_GETGEO 255/63/8), less the three refusals the nodes and NVMe suites also name |
| A10-HBA-reset | the optional GHC.HR reset (`ahci-reset`) boots and drives the disk; `ahci-check`'s synthetic rows: a command timeout after its deadline, a stale PxTFD.ERR before completion ignored, TFES, a clean completion; a 4Kn IDENTIFY refused, a 512e one decoded |
| A13-no-pit | q35 with `pit=off`: both controllers refused by name, no port driven, the session reached within 240 s (R-px75b-7) |
| A11-throughput | 1 GiB written, read back and checked on a tmpfs image, byte-identical to the guest's; the times printed, no bar (the full and all tiers; the pr tier says SKIP by name) |
| A12-root-fstab | `--boot-ahci`: `/` from `root=PARTUUID=` on `sda2`, `/etc/fstab` by PARTUUID mounting `sdb1`, files written and read (the full and all tiers) |

At `5ae7388c` (the code's final head; later commits are notes, docs and CI budgets), `logs/b4b.sum` and `logs/b4b-ahci-*.log`, every row PASS, 0 FAIL, the pr tier's SKIP line absent (`--rows all`):

| leg | seconds (KVM; the build included) | PASS lines |
|---|---:|---:|
| native BIOS | 111 | 21 |
| native UEFI | 50 | 21 |
| release BIOS | 367 | 21 |
| release UEFI | 366 | 21 |

Each leg's 21 PASS lines are its 16 rows, A7's two LBA48 witnesses (PAX's
and the guest's), A10's two `ahci-check` lines and the suite's own
`mpx6-ahci: PASS (tier firmware)`; the one LOUD line
names the recorded guest. The pr tier's rows alone (A11 and A12 said
SKIP by name) at `ddda81b3` (`b5358c83` rebased), both firmwares:
`logs/b4a-ahci-native-{bios,uefi}.log`.

The first lane's three legs at `9355a03f` (`44f86075`), before this
pass's changes: native BIOS `logs/test8.log` (the record), native UEFI
`logs/ahci-native-uefi.log`, release BIOS and UEFI `logs/ahci-release.log`,
all PASS.

### 4.2 Throughput (A11, 1 GiB, tmpfs-backed image, KVM)

| leg | PAX write | PAX read and check |
|---|---:|---:|
| native BIOS | 639.1 MB/s | 642.9 MB/s |
| native UEFI | 627.9 MB/s | 627.9 MB/s |
| release BIOS | 1206.4 MB/s | 1118.5 MB/s |
| release UEFI | 1179.9 MB/s | 1106.9 MB/s |
| the Linux guest (recorded) | 357.1 MB/s | 2384.3 MB/s |

px75's NVMe beside it: 684 / 706 MB/s native. On both sides the probe
(`user/elf/nvme.c`'s `speed`) times the writes through their fsync and
empties the buffer cache (BLKFLSBUF) before the read, so each read is the
emulated device's. These are QEMU's controller on a tmpfs image, not a
disk's speed; under TCG (§4.6) PAX's native leg ran at 132.4 / 124.0.

### 4.3 The boot lines a photograph of kasumi should show for its disks

From the contract's reading of kasumi. kernel/pci walks depth first in
device order (a bridge's buses where the bridge stands), and Linux
probed the Intel controller's ports (`ata1`–`ata6`) before the
ASMedia's (`ata7`–`ata8`), so `ahci0` should be the Intel and `ahci1` the
ASMedia; that holds if the ASMedia's root port comes after `00:17` on bus
0, which only the photograph (or `lspci -t`) shows. Then `sda` is the
Samsung on `ata5` (port 4) and `sdb` the SanDisk on `ata8` (the
ASMedia's port 1), as Linux names them. The capacities are the IDEMA
sizes of a 4000 GB and a 512 GB drive; `<…>` is what only the photograph
can say:

    ahci0: 8086:43d2 at 00:17.0, CAP.NP=<n> CAP.NCS=<n> S64A=<0|1> PI=<0x…> BOH=<0|1>; ports idled; one slot, polled
    ahci1: 1b21:0612 at 6e:00.0, CAP.NP=<n> CAP.NCS=<n> S64A=<0|1> PI=<0x…> BOH=<0|1>; ports idled; one slot, polled
    nvme0: 144d:a80c at 02:00.0, … (px75's line)
    block: nvme0n1: …
    ahci0: 8086:43d2 at 00:17.0 port 4: sda model "Samsung SSD 870 EVO 4TB" serial "<S…>" firmware "<…>"; 4000787030016 bytes (4000 GB); logical 512 physical 512 bytes
    block: sda: 7814037168 sectors (4000787030016 bytes), 8:0, read-write, flush
    ahci1: 1b21:0612 at 6e:00.0 port 1: sdb model "<SanDisk …>" serial "<…>" firmware "<…>"; 512110190592 bytes (512 GB); logical 512 physical 512 bytes
    block: sdb: 1000215216 sectors (512110190592 bytes), 8:16, read-write, flush

The install target, plugged into an Intel port below port 4, becomes
`sda` and moves the Samsung to `sdb` and the SanDisk to `sdc`, on Linux
and on PAX: the photograph identifies it by its serial. Empty ports and
the ASMedia's unused port print nothing. If kasumi's PCH does not clock
the 8254, the two controller lines instead read
`ahci0: 8086:43d2 at 00:17.0: refused: the 8254 PIT does not count, so no
AHCI wait could end` (and the same for `ahci1`), and no `sd` disk appears
until px76's clock replaces the shim. If the firmware's SATA mode is
Intel RST rather than AHCI, the controller's class is RAID (01.04) and no
`ahci` line appears at all (see 5.3).

### 4.4 The nodes regression (qualify2's red)

`logs/qualify2.log` (`.rc` 1) went red in `logs/regress-mpx6-nodes.log`:
N1 to N12 "the guest's session has no such section", N13 green. The
session that was missing is the Linux guest's, not PAX's: the rig
(`rig/run.sh`, px75's) exports `PAX_LINUX_KERNEL`, so mpx6-nodes found a
readable kernel and took its live path; `tools/linux-nodes` then got its
busybox by `podman run px13-ubuntu cp /usr/bin/busybox`, which the rig's
engine shim ran in px75's image, where there is no `/usr/bin/busybox`
(`cp: cannot stat '/usr/bin/busybox'`, `linux-nodes: busybox from
px13-ubuntu`); no guest booted and every comparison had nothing to read.
`PAX_LINUX=recorded`, which the job set, is not a value mpx6-nodes reads
(it knows `live`). CI has no readable kernel and always uses the record
made on kasumi. px75 ran its regressions with `unset PAX_LINUX_KERNEL
PAX_LINUX_MODULES` for this reason. No code change; no row touched. At
the same head `9355a03f` with the kernel unset (`logs/regress3-*.log`):
mpx6-nodes every row PASS against the record, 0 FAIL (N0–N14, including
N13's halts with 3, 4, 2 and 2 disks and 0 errors). The q35 ICH9
controller and its CD-ROM do take part in every one of its boots
(`ahciN: … port 0: ATAPI skipped`), and change nothing a row reads.

Two more rig faults met on the way, neither the code's: mpx6-install's
oracle `sgdisk` (CI installs `gdisk`, `fdisk`, `strace` for the disk-tool
jobs; px75's image has none: the lane image adds them), and mpx6-fsck's
oracle wrappers (named `e2fsck` and `mke2fs`, first on its PATH) found
again by the engine shim, which then called `tools/e2fs` and itself
forever; the shim now runs a program on a container's own PATH, as a
real engine does (`rig/shim/podman` on hasu; px75's original kept beside
it).

At `9355a03f`, kernel unset (`logs/regress3.sum`): mpx6-nodes, -part,
-ext2, -root, -nvme, -journal, -disktools, -fsck PASS; mpx6-install red
on the missing `sgdisk` alone (its rows before the oracle PASS). At
`5ae7388c`, with the lane image and the shim's PATH (`logs/b4b.sum`):

| suite (native BIOS) | seconds | PASS lines | FAIL |
|---|---:|---:|---:|
| mpx6-blk | 7 | 14 | 0 |
| mpx6-nodes | 109 | 27 | 0 |
| mpx6-part | 170 | 92 | 0 |
| mpx6-ext2 | 279 | 18 | 0 |
| mpx6-root | 76 | 30 | 0 |
| mpx6-journal | 334 | 23 | 0 |
| mpx6-nvme | 123 | 29 | 0 |
| mpx6-install | 499 | 49 | 0 |
| mpx6-disktools | 205 | 53 | 0 |
| mpx6-fsck | 247 | 77 | 0 |

Every one against its committed Linux record (LOUD by name) or its own
oracles; no row said SKIP. The kernel's change reaches all of them: every
q35 boot now passes kernel/ahci's discovery of the ICH9 controller and
its CD-ROM. mpx6-blk's boot with no disk differs from `9355a03f`'s by one
`ESC[01;01H` before the banner (console, not disk); its other two boots
are byte-identical.

### 4.5 Seen red

| plant | branch, PR, run | red rows |
|---|---|---|
| the IDENTIFY strings without the ATA byte swap | `px75b-plant-strings` (`a02b448b`), pax#229, run 40810509248, job mpx6-ahci | `FAIL A1-identify-inventory: installer did not preserve all four hardware identities`; `FAIL A1-identify-files` (`PX75B-A1` read as `XP57-B1A`) |
| a PRDT byte count written as the count, not the count less one | `px75b-plant-prdt` (`70c1251c`), pax#230, run 40810539823, job mpx6-ahci | `FAIL A3-before-differential`, `FAIL A4-prdt-readback`, `FAIL A5-after-differential` (every FNV and readback differs) |
| AHCI waiting on a PIT that does not count (R-px75b-7) | `px75b-plant-pit` (`1af6796a`), pax#232, run 40818748481, job mpx6-ahci | `FAIL A13-no-pit: the boot never reached its session (a wait on a PIT that does not count)` at 04:46:31Z, 241 s after A10 passed (the row's 240 s bound); A0–A10 PASS before it. The same run's `mpx5-users-ahci` job: success (§4.6) |

Each plant's other rows stayed green (the strings plant's A2–A5, the
PRDT plant's A1 and A2). Both of the first lane's were seen red on hasu
before CI (`logs/plant-strings.log`, `logs/plant-prdt.log`, raw exit 1).

The budget row, seen red on hasu (a check with no QEMU, so no CI run of
its own): `tests/ci-budgets.py` against a copy of the workflow whose
`mpx5-users-ahci` bound is 85 minutes, `FAIL CI budget mpx5-users-ahci:
bound=5100s sizing-floor=3666s margin=1434s`, exit 1
(`logs/final-ci-budgets-red85.log`); at the head's 90, PASS
(`logs/final-ci-budgets.log`).

### 4.6 R-px75b-6, measured

The first lane took the AHCI-root pass out of mpx5-users' job
(`01ab23c4`) after measuring it on hasu (`logs/users-ahci-root.log`, `.rc`
0: 25 boots through tools/qemu-rootdisk, 28 rows SKIP for the disk by
px67's rule, the suite's exit 0; 219 s with the disks' first making).
Measured since:

| leg of mpx5-users, native BIOS, `/` on | hasu KVM | hasu TCG | CI (GitHub, TCG) |
|---|---:|---:|---:|
| virtio (the users job's own step) | 168 s | 1728 s | 1806–3422 s in 16 runs (`tests/ci-budgets.d/runs.json`); 3432 s in the full-tier run 40620130831 |
| NVMe (the users job's, the full tier only) | 168 s | — | 28 to 53 minutes more, px75's measure |
| AHCI | 178 s | 1733 s | 3436 s (run 40818748481, job `mpx5-users-ahci`, green; the build 50 s, the job 3510 s) |

(hasu: block B, `logs/timing.sum`, at `5ae7388c`, the build 35 s; TCG is
the rig without `/dev/kvm`, as CI boots.) Under TCG the two buses cost the
same (1733 / 1728 = 1.003); under KVM AHCI's polled single slot is 6%
slower. CI's one AHCI observation sits at the virtio leg's top. The users
job's budget (px83, `tests/ci-budgets.d`): all-tier floor 8920 s (main
5018 + root 3422 + 300 + 180) under its 12600 s bound; a third root leg
there would need 289 minutes at the 40% rule, and in the full tier (native
BIOS 1678 s, virtio ≤ 3422 s, NVMe ≤ about 3180 s) about 11900 s against
the 9000 s that 210 minutes allows. So option (B)'s whole-suite leg could
not ride the users job in the all tier either: it needs a job of its own
there as well, and (B) would differ from (A) only by leaving it out of the
merge gate.

mpx6-ahci's own job keeps the first lane's 120 minutes: one whole native
BIOS leg (every row) under TCG on hasu took 131 s
(`logs/timing-tcg-mpx6-ahci.log`; A11 at 132.4 MB/s written, 124.0 read
and checked), the plant run's `pr` rows reached A10 in 194 s with the
build in CI, and the release legs' LLVM build (about 370 s each on hasu)
is the larger part of the all tier's four legs. The job has not yet run
its four legs whole in CI: this PR's run is the first.

## 5. Done-when

### 5.1 Rulings (recommended and implemented, not decided)

- **R-px75b-1, the completion path.** (A) polled with the controller's
  interrupts masked (GHC.IE and PxIE clear, INTx disabled, MSI and MSI-X
  enables cleared), as px75. Implemented. An interrupt-driven path is a
  follow-on behind px76's MSI work.
- **R-px75b-2, the HBA reset.** (B) no global reset: §10.1.2 makes
  GHC.HR optional for a controller firmware has configured; each port is
  idled instead (ST then CR, FRE then FR, 500 ms each). Both measured
  under QEMU: A10 boots with the optional reset (`ahci-reset`) and every
  other row without it.
- **R-px75b-3, the ASMedia ASM1061.** (A) driven as generic AHCI, no
  quirk; QEMU's `ahci` stands in for both controllers. On metal it is
  logged and driven like the Intel unless a photograph says otherwise;
  the install target goes on an Intel port (px78).
- **R-px75b-4, sysfs identity.** `device/model` is the ATA model with its
  padding trimmed (all 40 bytes' worth), `device/serial` the serial byte
  for byte with inner spaces (the witness `PX75B B2 INNER`). A named
  departure: Linux's `model` for a SATA disk is SCSI INQUIRY's 16-byte
  product field (the guest pads `PX75B-SATA-A` to 16), so a model longer
  than 16 characters reads shorter on Linux; the serial, px78's key, is
  the same on both. The fixture's models fit in 16, so A1 holds the
  guest's lines exactly once padding is trimmed.
- **R-px75b-5, 4Kn.** QEMU 8.2's `ide-hd` refuses a 4096-byte logical
  block before the guest boots (measured twice by the first lane), so the
  refusal by name is proven on synthetic IDENTIFY words (`ahci-check`,
  A10) and a real 512e disk's sizes against the guest (A9). px84 owns the
  bound itself.
- **R-px75b-6, the AHCI-root leg.** (A) its own job, `mpx5-users-ahci`
  (`56b52f77`): it builds mpx5-users' native BIOS images and boots all 25
  with `/` on AHCI, planned as every suite: the full and all tiers, and a
  pull request that changes kernel/ahci or its clock (`tools/ci-tiers.map`,
  `a9c9f626`), the users suite's script or the root-disk tools (by the
  derivation: its job's block names them), proven by tests/ci-plan's rows
  (`457f921a`; 297 PASS at `ddda81b3` and again at `5bcb6cad`,
  `logs/b4a-ci-plan.log`, `logs/final-ci-plan.log`). Bound 90
  minutes: floor 3666 s (build 50 + CI's leg 3436, above the scaled 3432,
  + 180), 40% above it 5132 s (scaling the newer full-tier 3432 s instead:
  a 3442 s leg, a 3672 s floor, 5141 s); `tests/ci-budgets.py` holds it there from
  `tests/ci-budgets.d/ahci-root.json` (`751489a7`). Its cost: about 59
  job-minutes in each full and all run, in parallel, so the merge gate's
  wall time is still the users job's (85 minutes before px75's NVMe step,
  plus that step). (B), the all tier plus a smoke in the full tier, has
  its smoke already (mpx6-ahci's A12: `/` and `/etc/fstab` by PARTUUID on
  AHCI, files written and read, in the full and all tiers), but its
  whole-suite leg needs the same job in the all tier (above), so (B) would
  save the full tier's 59 job-minutes and lose the merge gate's 25-boot
  AHCI root: a module merge would first meet it on the trunk push.
  Recommended (A), implemented.
- **R-px75b-7 (new), the bootstrap clock.** Every AHCI wait is a
  deadline on `kernel/ahci_clock`, the PIT shim, until px76's clock
  merges. Two defects found in review: (1) `now_ns` computed
  `elapsed * 10^9` in u64, and wolf traps on overflow in every profile
  (the wolf book, ch. 9), so a kernel would panic once 1.8e10 PIT ticks,
  4.3 hours of accumulated waiting, had passed (a long copy to a SATA
  disk is enough); (2) on a machine whose 8254 does not count, which
  px76's contract says kasumi's PCH can do, no deadline ever expires, so
  the first empty port's COMRESET (1 ms) would hang the boot. Options:
  (A) split the product (seconds and remainder) and refuse each AHCI
  controller by name when 100000 latched reads never change; (B) fall
  back to a loop count, a CPU-speed deadline the contract forbids; (C)
  wait for px76. Recommended (A), implemented (`03f27937`, `090614a3`),
  witnessed by A13 on q35's `pit=off` under both firmwares and planted
  red (§4.5). The boot then goes on without SATA disks and the
  photograph names why.

### 5.2 Checklist

- [x] The driver, the names, the nodes and the identity files; `--ahci`
      and `--boot-ahci` (§4.1, docs/BOOT.md "SATA disks").
- [x] Every row of tests/mpx6-ahci on all four legs at the final head
      (§4.1); the first lane's legs at `9355a03f`.
- [x] The no-write row: three AHCI disks and an NVMe disk through login
      and the installer's inventory, every sha256 unchanged (A6).
- [x] LBA48 past sector 2^32 (A7); 1 GiB both ways with its throughput
      (A11, §4.2); `/` and `/etc/fstab` by PARTUUID on AHCI (A12).
- [x] Two controllers with gaps: Linux and PAX both name `sda`, `sdb`,
      `sdc` (A2).
- [x] The boot lines for px77 (§4.3, docs/BOOT.md).
- [x] The nodes regression found and the disk suites run (§4.4).
- [x] Three plants red by name (§4.5).
- [x] R-px75b-6 measured and wired: `.github/workflows/ci.yml`
      (`mpx5-users-ahci`), `tools/ci-tiers.map`, `tests/ci-plan`
      (PASS, `logs/b4a-ci-plan.log`), `tests/ci-budgets.py` (§4.6).
- [x] docs/SOURCES.md (px75b), README (the disks paragraph, the suite,
      the commands, the budgets), this note.
- [ ] The PR's run green at the head (its FULL paths, tools/qemu-run and
      tools/qemu-halt, make every run `tier all`, the superset of `tier
      full`); the orchestrator's label (cross-cutting: CI itself changed).

### 5.3 Departures and limits named

- The BIOS/OS handoff (§10.6.3) is not exercised: QEMU reports BOH=0.
  The code is read against the clause and is the conservative reading:
  after its 25 ms it waits up to 2 s for both BOS and BB to clear and
  refuses the controller by name otherwise (step 5 would let the OS take
  a controller whose BIOS never set BB).
- An Intel controller in RST (RAID, class 01.04) mode is neither driven
  nor named: no line at all (px75's note §7 recommended naming it).
- One slot, no NCQ, no hotplug, no port multipliers (named and skipped),
  no interrupts. Four disks in kernel/block in all: kasumi's NVMe, its
  two SATA disks and the install target fill the table exactly; a fifth
  is refused by name (`block disk table full`).
- `ahci_clock`'s wrap detection assumes a poll within each 10 ms PIT
  period; a longer gap undercounts, so a wait runs longer, never
  shorter.
- Linux's controller probe order was predicted to race; one recorded
  order was measured, not a distribution.
- The shim is px75b's until px76's `kernel/clock` merges; whichever lane
  merges second deletes `kernel/ahci_clock` and points kernel/ahci at
  the shared API (the same five names).

### 5.4 Issues to file (not filed by the lane)

- pax: kernel/ahci should name an Intel RST (class 01.04.00) controller
  and refuse it, so a photograph says "set the firmware to AHCI".
- pax: the disk suites' `kernel_readable` (mpx6-nodes, -part, -ext2,
  -root, -journal, -nvme) take the live path whenever a kernel is
  readable; `PAX_LINUX=recorded` (which a rig may set) is not read, and a
  missing guest log ends in a Python traceback instead of a named FAIL.
- pax: the AHCI-root job's budget rests on one CI observation and a scaled
  one; the next CI budget lane adds the rest to `tests/ci-budgets.d`.
- After px76 merges: delete `kernel/ahci_clock` (the second to merge).
- px84's past-2-TiB AHCI leg waits on this merge.

### 5.5 To prune

On hasu, `~/lanes/px75b/`: `build*`, `plant-*`, `qualify`, `regress3`,
`b4a`, `b4b`, `timing*`, `tmp` (the logs, the rig and the cache kept
until the merge); the image `localhost/px75b-ubuntu:1`. On GitHub: the
draft plant PRs pax#229, #230 and #232 and their `px75b-plant-*`
branches, closed unmerged by the orchestrator.
