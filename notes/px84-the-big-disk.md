# px84 — the big disk: a real SSD's capacity, end to end (P6, pax#179)

Crawl 54. Contract `sprints/pax/84-the-big-disk/px84-the-big-disk.md`, with
its two corrections of 2026-10-28: the installer writes no journal, so
R-px84-4 is withdrawn, and fsck at size is R-px84-5. Branch `px84` from
trunk `6ccfe3fe`. A Codex lane (GPT-6-Astra) did the work through the 4 TB
install (`faa710d8`..`98b83c52`; `4faa84f7` before the rebase) and stopped
at its weekly limit. An Opus 5.5 lane finished it: it synced the kasumi
clone, added the 4Kn witness, reran the storage suites at the head and
wrote this note and the README.
The prediction was committed first (`faa710d8`, `notes/px84/prediction.txt`,
21:55 on 2026-10-28), before the first test (`bd7687d5`, 22:03) and the
first formatter change (`6b9423b8`, 22:11).

Before this lane, `paxext2` stopped at 4 GiB (`main.lu:195`), and the
installer refused any target whose root would be larger (`plan.lu:17`,
`ROOT_MAX`; `too_large`). Every SSD that could be the install target is
bigger than that. Now the formatter goes to the ext2 ceiling, the
installer caps the root there and names the rest, and a 500 GB and a 4 TB
install each boot alone under SeaBIOS and OVMF.

## 1. Forbidden, and what was read

No kernel, e2fsprogs, partition-tool, FAT-tool, bootloader or emulator
source was read: not Linux's `fs/ext2/` or `block/`, not e2fsprogs'
`lib/ext2fs` or `misc/mke2fs.c`, not gdisk's or dosfstools' sources, not
QEMU's. Read: the ext2 layout documents `docs/SOURCES.md` already cites for
px67–px72 (`Documentation/filesystems/ext4/group_descr.rst`,
`blockgroup.rst`, from the sparse allowed checkout), the UEFI
specification's GPT chapter and Microsoft's FAT32 specification, both
cited since px69. Run as black boxes and cited by their output only:
e2fsprogs 1.47.0 (`mke2fs -n`, `e2fsck -fn`, `dumpe2fs -h`, and the
installed `/etc/mke2fs.conf`, which is documentation of its defaults),
`sgdisk` 1.0.10, `fsck.fat` 4.2, QEMU 8.2.2, and Linux 7.3.0-4-cachyos as a
guest through `tools/linux-blk`. PAX's own formatter, installer, checker and
storage kernel modules were read and audited (§4.2). The entry is
`docs/SOURCES.md`, "px84 — large ext2 volumes".

Work ran on kasumi, cores 4–7, under
`flock /home/mfwolffe/lanes/kasumi-cores-4-7.lock`, everything under
`/mnt/steamlib/lanes/px84/` (the maintainer's grant). The lane's real
use of that disk peaked at about 140 GB, during the 16 TiB density row,
and is 4.5 GB now. Every large image was sparse and was deleted as soon
as its row was recorded. Nothing was installed on any
host, and nothing of the maintainer's was touched. The Mac worktree
`~/lanes/px84/pax` was used for git only. No merge, tag, label, release,
or issue filed or closed.

## 2. Inputs, verified

- **Base:** trunk `6ccfe3fe` (px75's record). The final head is rebased onto
  `96b7f90f` (px77a's merge), whose three commits touch `notes/` only.
- **wolf 0.2.35**, the release archive by digest (`kernel/wolf.pin`: sha256
  `4cc4045bbbb605c0…`, pin commit `cf0c13d`), read by `tools/fetch-wolf` on
  every job ("wolf 0.2.35 (wolfgang, pin cf0c13d)" in each log).
- **The container** `localhost/px80-ubuntu` (px80's Ubuntu 24.04 image,
  reused, not changed). Its e2fsprogs is `1.47.0-2.4~exp1ubuntu4.1`,
  the same package as `tools/e2fs`'s pinned image
  `ubuntu@sha256:534baea6…` (both read with `dpkg-query -W` on
  2026-10-29). Its QEMU is 8.2.2, CI's.
- **The partition and FAT oracles:** `user/disktools.pin`'s seven Ubuntu
  packages, each sha256 checked before extraction (`notes/px84/oracles.log`).
  They were extracted without package scripts and run through wrappers.
  `sgdisk` 1.0.10, `fsck.fat` 4.2.
- **The Linux guest:** kasumi's `/usr/lib/modules/7.3.0-4-cachyos`
  (vmlinuz and modules, read-only), with the container's static busybox.
- **The kasumi clone** sat at `6ccfe3fe` with the predecessor's edits as
  modified and untracked files. Each was compared with the pushed branch
  (`4faa84f7`, now `98b83c52`). Every one was either identical or an older
  state of a branch commit: `big.py` was `16c6581d`'s, and `ci-plan` and
  `ci-tiers.map` were `cf2318fc`'s. `tests/mpx6-disktools` was the
  branch's version without the `bounds.py` call. Nothing existed only on
  kasumi. The diffs are kept at
  `/mnt/steamlib/lanes/px84/presync/`, and the clone was reset to the
  branch.

## 3. Prediction, scored

The prediction (`notes/px84/prediction.txt`) against what was found:

| Predicted | Found |
|---|---|
| Group-table indexing and allocation limits hide more 32-bit assumptions than the block transport | **Right.** Every limit was in the userspace formatter: the 4 GiB cap, a fixed 32,768 blocks per group in every offset, and two 4 KiB bitmaps per group held in memory (1 GiB at 131,072 groups). The kernel's transport needed no change (§4.2). |
| `0xffffffff * 512` (`kernel/ext2/ext2.lu:2373`) caps a sector-count interface, not ext2 block numbers | **Half right.** It does not bound block numbers. It is not a sector interface either. It bounds one file's size by `i_blocks`, a 32-bit count of 512-byte units: 2 TiB less 512 bytes per file. |
| A 4 TB format takes about 8 minutes with every inode table written | **Wrong by 2.9×:** 163.6 s (`notes/px84/formatter-density.log`). |
| The 16 TiB-less-a-block volume fails its first `e2fsck -fn` on boundary geometry | **Wrong.** The first run that reached it was clean (`formatter-sparse.log`, 22:11). |
| A 500 GB install takes about 6 minutes | **Close:** 231.95 s, or 244.02 s with verification (`install-500gb/install-timing.json`). |

## 4. Evidence index

### 4.1 What was built

- **`paxext2` up to the ext2 ceiling** (`6b9423b8`). With 4 KiB blocks
  and 32-bit block numbers, the ceiling is 17,592,186,040,320 bytes:
  2^32 − 1 blocks, or 16 TiB less one block. Anything larger is refused as
  `too_large` before the target is opened. The changes:
  - The group descriptor table spans as many blocks as it needs.
  - Superblock and descriptor backups are written in every group the
    `sparse_super` rule names (0, 1 and the powers of 3, 5 and 7).
  - The last partial group's padding bits are set.
  - Allocation is a monotonic prefix per group, so the bitmaps are built
    one group at a time when the volume is finished, not held for the
    whole volume.
  - If 32,768-block groups would leave a final group too short for its
    metadata, the group size shrinks in steps of 8 blocks rather than
    dropping capacity.
  - Inode tables are zeroed in 1 MiB writes.
  - Density follows R-px84-2.
- **The installer** (`c4e972d4`, `e583e88c`). `ROOT_MAX` is the ext2
  ceiling. A larger target gets a root at the ceiling, and the plan names
  the rest as `unused_bytes`; `too_large` is gone from the planner. The
  executor's `--inodes 16384` override is removed: it came in with
  `61949606`, no motive was recorded, and the root now takes Linux's
  measured density.
- **`fsck.ext2`** (`16c6581d`, R-px84-5). A volume past 4,194,304 blocks,
  1,048,576 inodes or 512 groups is refused as `unsupported: volume
  exceeds checker capacity`, with exit 8. The refusal comes before any
  allocation, replay or write, and the image is unchanged in all three
  modes (`-n`, `-y`, `-p`).
- **Tests.**
  - `tests/mpx6-disktools.d/big.py`: geometry at the five sizes, the
    named refusals past the ceiling, and real `e2fsck -fn` and
    `dumpe2fs -h` on each volume.
  - `bounds.py`: a 3 TiB GPT with an unchanged 64 MiB FAT32 ESP.
  - `high.py` and `high-fixture.py`, with `user/elf/bigdisk.c`: one
    file's inode and both data blocks past 2 TiB, through virtio and
    NVMe, optionally round-tripped with Linux.
  - `tests/mpx6-fsck.d/refusals.py`: the F-capacity rows.
  - `tests/mpx6-install.d/planner.lu`: I-big-plan at 8 GiB, 64 GiB,
    500 GB, 4 TB, 17 TiB and 2^63 − 512.
  - `big-run` and `big-boot.py`: a full-density install onto a sparse
    500 GB or 4 TB target, then the target booted alone under both
    firmwares.
  - The I-4kn-refused row (`382b1c71`, `9fead7f3`, R-px84-1).

### 4.2 The kernel past 4 GiB and past 2 TiB: the 32-bit audit

The kernel needed no change. Every offset and sector number already
travels in 64 bits, and `high.py` proves it on both transports. The
narrowings found, and what each one bounds:

| Site | What it computes | What it bounds |
|---|---|---|
| `kernel/ext2/ext2.lu:2373` `0xffffffff * 512` | `max_size`: the smaller of three indirect levels' reach (about 4 TiB with 4 KiB blocks) and what `i_blocks` can count | **one file**, to 2 TiB less 512 bytes; not the volume |
| `kernel/ext2/ext2.lu:1758`, `:1788` `w32` of block numbers | block pointers in the inode and in indirect blocks | the format's own 32-bit block numbers, the ceiling above |
| `kernel/journal/journal.lu:596`, `:719`, `:1001` `w32(…, b + 1)` | the logged set and the revocation table store block + 1 in 32 bits | exact at the ceiling: the largest block is 2^32 − 2, so b + 1 still fits; ext3's journal tags are 32-bit without the 64bit feature |
| `kernel/block/block.lu:1953` `blk & 0xffffffffffff` | the block cache's key keeps 48 bits of block number | 2^48 cache blocks, far past ext2's 2^32 |
| `kernel/block/block.lu:947` `rw(…, sector: u64, …)`, `request` | sectors, counts and the capacity check | 64-bit throughout |
| `kernel/vblk/vblk.lu:522` `w64(h + 8, sector)` | the virtio-blk request header's sector | 64-bit (virtio 1.x's request header) |
| `kernel/nvme/nvme.lu:1094` `lba & 0xffffffff`, `lba >> 32` | SLBA split into CDW10 and CDW11 | 64-bit starting LBA |
| `kernel/block/block.lu:452` | GPT entries' LBAs read as le64 | 64-bit |

**AHCI's LBA48** (`kernel/ahci`, px75b) is pending px75b's merge. The
past-2-TiB leg on AHCI is owed by whichever lane lands after both. The
`high.py` witness takes a transport name, so the leg is one more row.

### 4.3 Rulings (recommended and implemented, not decided)

- **R-px84-1 (A): 4 KiB logical sectors stay refused, by name.**
  - The planner refuses `sector_size` (I-refusals, `planner.lu`).
  - Under QEMU, the I-4kn-refused row gives the installer a virtio target
    with `logical_block_size=4096,physical_block_size=4096`. The kernel
    names the 4096-byte blocks and leaves vdb whole. The installer prints
    `pax-install: refused: sector_size` and exits 1, and the target's
    sha256 is unchanged.
  - The row was seen red against a planner planted to accept 4096-byte
    sectors (§4.4).
  - The 4Kn half of pax#179 is filed as its own issue (§5).
- **R-px84-2 (A): a tiered bytes-per-inode, from `mke2fs` 1.47.0's
  documented defaults.** 4,096 below 512 MiB (`small`), 16,384 below
  4 TiB (`default`) and 32,768 from 4 TiB (`big`). `huge` (65,536, from
  16 TiB) is out of reach below the 32-bit ceiling. `mke2fs -n -t ext2
  -b 4096` agrees (`notes/px84/regress/r8-mke2fs.log`):

  | Size | Inodes | Bytes per inode |
  |---|---|---|
  | 512 MiB less 4 KiB | 131,072 | 4,096 |
  | 512 MiB | 32,768 | 16,384 |
  | 4 TiB less 4 KiB | 268,435,456 | 16,384 |
  | 4 TiB | 134,217,728 | 32,768 |
  | 16 TiB less 4 KiB | 536,870,912 | 32,768 |

  At 500 GB and 4 TB, `paxext2`'s inode counts equal `mke2fs`'s exactly:
  30,523,392 and 244,146,176 (`formatter-density.log`).
- **R-px84-3 (A): every inode table is written at format time.** The
  formatter alone (host, sparse file, `formatter-density.log`) took:

  | Volume | Format time | Written |
  |---|---|---|
  | 8 GiB | 0.30 s | 134.8 MB |
  | 64 GiB | 2.72 s | 1.08 GB |
  | 500 GB | 20.50 s | 7.85 GB |
  | 4 TB | 163.56 s | 62.8 GB |
  | 16 TiB less a block | 352.51 s | 138.6 GB |

  Inside the installer, in a TCG guest, the 4 TB install took 1,625.83 s;
  the 512 MiB smoke install takes about 19 s. So at 4 TB the table writes
  take longer than the rest of the install, which is the condition the
  contract names for (B). (A) is implemented as recommended, and the
  number is the maintainer's to weigh. On metal the writes run at the
  SSD's speed: 62.5 GB is about two minutes at 500 MB/s.
- **R-px84-4** was withdrawn on 2026-10-28: the installer writes no
  journal.
- **R-px84-5: fsck at size goes to a second PR.** That PR is a
  bitmap-based checker: one bit per block for ownership, 128 MiB at
  4 TB. Meanwhile the checker refuses big volumes by name (§4.1). Item
  3's sized runs belong to that PR: the five volumes clean, a planted
  bitmap error past 4 GiB repaired, and the 4 TB run time. Linux's
  `e2fsck -fn` times on the density volumes, for scale: 174.4 s at
  4 TB and 373.9 s at 16 TiB less a block.

### 4.4 Seen red

- **px84-plant-offset** (`8b2110c2`, draft pax#227) multiplies a block
  number into its byte offset in 32 bits. Run 40808409507, job
  mpx6-disktools: `B-8589934592-e2fsck` failed with exit 4 ("Deleted
  inode 273 has zero dtime"). That is the 8 GiB volume, the first past
  4 GiB. Every ext2 differential row below 4 GiB (E1–E13) passed in the
  same job.
- **px84-plant-partial** (`81332d51`, draft pax#228) computes the group
  count by truncating division above 1,048,576 blocks, which drops the
  last partial group. Run 40808412517: the 8 GiB and 64 GiB rows have no
  partial group and passed; `B-500000000000-e2fsck` failed with exit 12
  ("The ext2 superblock is corrupt").
- **The 4Kn row, locally on kasumi.** The tree was planted with
  `t.sector % 512 != 0` in `user/install/plan.lu:86`, so 4096-byte
  sectors were accepted, and the installer was built from it. The
  committed I-4kn row failed against it at `install.py:148`: the named
  `pax-install: refused: sector_size` was absent. The planted installer
  went on past the plan: the kernel counted 16 writes (128 sectors) and
  one error on vdb, and the image's bytes came out unchanged (the row's
  sha check passed). It printed `stopped: io`
  (`notes/px84/regress/r7-4kn-red.log`, `r7-4kn-red.out`). The fixed
  tree passed the same row in r5b (§4.6).

### 4.5 CI's tiers

- **mpx6-disktools**, every tier that selects it:
  - `big.py` runs its five sizes with a 16-inode budget, so only metadata
    is written: 1.7 GB of real blocks at 16 TiB.
  - `bounds.py` runs in the Linux phase.
  - `high.py` runs in the PAX phase, with the deterministic byte oracle
    and real `e2fsck`; the Linux round trip is the lane's local evidence.
- **mpx6-install**: `PAX_INSTALL_BIG_ROWS` is `none` in `tier pr`,
  `500gb` in `tier full` (the merge gate), and both 500 GB and 4 TB in
  `tier all`. The job's budget is 120 minutes in `tier all`, 60
  otherwise. The big installs use QEMU's
  `detect-zeroes=unmap,discard=unmap` on the sparse backing file. That
  bounds the runner's disk, not the guest's writes: every inode table is
  still written by the guest.
- **Headroom.** The merge gate's mpx6-install took 19.5 and 45 minutes in
  the last two `tier full` runs (40532219747, 40620130831). The 500 GB
  row adds about 4–5 minutes on kasumi and more on a runner. If the
  merge gate ever passes 60 minutes, the full tier's budget is the line
  to move.

### 4.6 The final regression, at `09f8fd3d` (kasumi, cores 4–7)

`09f8fd3d` is `9fead7f3` before the rebase. The rebase onto `96b7f90f`
adds only px77a's notes, and the head differs from what ran only in
`README.md`, `docs/BOOT.md` and `notes/`. The logs are under
`notes/px84/regress/`:

Every row ran in `localhost/px80-ubuntu` under the lock, except r2b,
which ran on the host as CI's runner does: `tools/e2fs` runs its pinned
image there. The suites' engine-backed steps (`tools/mkdisk`,
`tools/e2fs`) ran inside the container through px75's engine shim
(`notes/px75/rig/shim-podman`), which is the pinned image's release. The
scripts are in `notes/px84/regress/rig/`.

| Row | What | Result |
|---|---|---|
| r1 | `tests/ci-plan` | PASS, 294 rows, including P4's big-install tiers and the `.geometry` artifact |
| r2 | `mpx6-disktools`: build, GPT (24), FAT (12) | PASS. Its ext2 step needs an engine, so it was run as r2b–r2d |
| r2b | `ext2.py` on the host, against the pinned image | 13 PASS, 0 SKIP |
| r2c | `big.py` (five sizes and B-limit), `bounds.py` (B-gpt-fat) | PASS, 0 SKIP; 16 TiB format 5.7 s with a 16-inode budget |
| r2d | `mpx6-disktools --only pax` (D-PAX, D-LIMINE, D-DISK, D-BOOT; B-high-virtio, B-high-nvme) | PASS, 0 SKIP |
| r3 | `high.py` with the Linux guest | B-high-linux-virtio and B-high-linux-nvme PASS, both directions |
| r4b, r4c | `mpx6-fsck`: Linux corpus, journal, refusals (F-capacity-*), rescue (BIOS), PAX corpus | PASS; corpus 21 parity rows, 1 unsupported (`bad-directory-record`, as on trunk) |
| r5b | `mpx6-install`, every smoke row and all 13 fault rows | PASS, 0 SKIP; I-4kn-refused PASS |
| r6 | the 500 GB install | install 247.13 s; I-big-boot-bios and I-big-boot-uefi PASS |
| r7 | the 4Kn row against the planted planner | red as planted (§4.4) |
| r8 | `mke2fs -n` density probe | R-px84-2's table (§4.3) |
| r9 | `mpx6-root --fstype ext2` with `PAX_EXT2_WRITER` set to paxext2, CI's step in the same job | PASS; 1 SKIP by design (R8: ext2 has no journal; R8e is its crash row) |

r2's ext2 step (`r2-disktools.log`), r4 (`r4-fsck.log`) and r5
(`r5-install.log`) failed on the rig, not the code: no engine for
`tools/e2fs`, and no `sgdisk` on PATH, which CI's job installs with apt.
Each was rerun with the tool supplied, as r2b–r2d, r4b–r4c and r5b.

### 4.7 Earlier evidence, kept

All of it is under `notes/px84/`:
- the formatter runs: `formatter-small.log`, `formatter-sparse.log`,
  `formatter-density.log`, and `density/` (every volume's `e2fsck -fn` and
  `dumpe2fs -h`);
- the transport runs: `high-03.log` and `high-linux.log`, with `high/`
  (every serial and Linux transcript);
- the installs: `install-500gb.log` with `install-500gb/` (timing, phases,
  `root.fsck`, `root.geometry`, both boots), and `install-4tb.log` with
  `install-4tb/`, the same set at 4 TB: install 1,625.83 s, booted alone
  under BIOS and UEFI, images reclaimed;
- the runs that failed on the way: `baseline.log` (red at B-limit: the old
  4 GiB cap answered `invalid`, not `too_large`), `bounds-02.log` (a
  wrong oracle path) and `fsck-bounds.log` (an exit status asserted as 4,
  corrected to 8 in `cf2318fc`).

## 5. Done-when

- [x] Items 1, 2, 4 and 5 as above. Item 2's AHCI leg is pending px75b.
  Item 3 is R-px84-5's second PR, with the named refusal in this one.
- [x] Item 6: R-px84-1 (A), the refusal tested by name in the planner and
  under QEMU.
- [x] Item 7: two plants red by name in CI, README refreshed (`85d7ebb0`,
  README only), `docs/BOOT.md` (`3d27d081`), this note.
- [x] The prediction committed first and scored (§3).
- [x] The final regression of the storage suites and the installer at
  the head's code (§4.6).
- [ ] The PR's `tier pr` run green at the head; the orchestrator labels
  `full-matrix` and watches `tier full`.

**Issues.**
- pax#179: close its capacity half by hand at the merge (the PR body
  says so; `(#N closes)` does not auto-close).
- To file: the 4Kn half (R-px84-1: "4096-byte logical sectors refused by
  name; support in paxgpt, paxext2, the installer and kernel/block").
- To file: R-px84-5's follow-on (the bitmap-based checker).
- To close unmerged: draft PRs pax#227 and pax#228, the plants.

**To prune** after the merge, on kasumi:
- `/mnt/steamlib/lanes/px84/build/` (about 4 GB) and `plant-4kn/`;
- `oracle-downloads/`, `oracles/` and `cache/`;
- keep `runs/` and `presync/` until the orchestrator says otherwise.
