# px68 — the journal: `/` survives a power cut (pax#150)

Crawl 54, Opus 5.5. Contract `sprints/pax/68-the-journal/px68-the-journal.md`
(pax#150). The prediction was committed first (`a594343c`,
`notes/px68/prediction.txt`). Branch `px68` from `origin/trunk`
`54570380` (px67's merge). The final head, its `tier pr` run and the
lane-audit line are the PR's; this note is the lane's record of what was
built, measured and seen red.

## 1. Forbidden, and what was read

No kernel's source: none of Linux's `fs/jbd2`, `fs/ext3`, `fs/ext4` or
`fs/ext2`, no other kernel's journal or file-system code, and no
e2fsprogs source (`lib/ext2fs`, `e2fsck/`, `debugfs/`, `misc/`).
`Documentation/filesystems/journalling.rst` (jbd2's in-kernel API) and
`ext3.rst` were not opened: the on-disk layout's pages only. What was
read is in `docs/SOURCES.md` (px68): `Documentation/filesystems/ext4/
journal.rst` (the journal's whole layout), `super.rst` (has_journal,
needs_recovery, journal_dev, s_journal_inum, every INCOMPAT and RO_COMPAT
bit's name), `special_inodes.rst`, `inodes.rst` and `blockmap.rst` (inode
8's blocks), the man pages mke2fs(8), debugfs(8), e2fsck(8), dumpe2fs(8),
and the VIRTIO 1.2 specification's FLUSH. e2fsprogs 1.47.0 (the image
tools/e2fs pins), QEMU 11.1.2 (and its trace events' names, read from
`-trace help`) and kasumi's Linux 7.3.0 on QEMU ran as black boxes.
Builds in `px13-ubuntu` on kasumi CPUs 0-3 under `flock
~/lanes/kasumi-cores-0-3.lock`; QEMU under `taskset -c 0-3`, `ulimit -c
0`; long jobs by `setsid -f` with pid files; nothing installed on any
host (Ubuntu 24.04's qemu-system-x86 package was downloaded once into a
throwaway container, unpacked and grepped for its trace events' names,
never installed); nothing built on nomad. No merge, tag, label, issue
filed or closed. Clean-room paragraph, px67's word for word: no Linux
source, no other kernel's mount, boot or file-system code, no source of
any init system or mount tool, of e2fsprogs, dosfstools or Limine.

## 2. Inputs, re-derived

| input | found |
|---|---|
| pax trunk | `54570380` (px67's merge, its `tier full` 40119925479) |
| `kernel/ext2` | px63's: INCOMPAT FILETYPE only, anything else refused (RECOVER among them); has_journal a COMPAT feature changing nothing (the journal a file never opened); a read-write mount clears VALID and writes the superblock at once (px66), the unmount writes the clean state last |
| `kernel/block` | px63's buffer cache: 512 buffers of a frame each, write-back or write-through (a global word), `sync` writes every dirty buffer of a device in slot order then FLUSHes; the clock hand writes a dirty buffer it takes. FLUSH is VIRTIO_BLK_T_FLUSH when the device offers it (QEMU's does: the books count it) |
| the flusher | kernel/fstab's `pax_flushd`: every 500 ticks (5 s, measured by the crash row's commits, §6: one each 250 operations of 20 ms), with IF clear, `tree.sync_all` when the cache has a dirty block |
| px67's crash row | 20 lost writes, 4 counts (kill 11 a free-blocks count; kills 22-24 `Block bitmap differences: -1942 -1973`), 0 orphans, 0 worse: the counts from the clock hand writing a bitmap or a descriptor between two steps of one call, and the flusher writing what a call left half done |
| e2fsprogs 1.47.0 `mke2fs -t ext3` (measured, notes/px68/guest.sh and `tools/mkdisk --journal`) | `has_journal ext_attr resize_inode dir_index filetype sparse_super large_file`; inode 8 the journal; 1024 blocks of 4 KiB under 32768 blocks, 4096 for 448 MiB; a v2 superblock, no journal feature (8-byte tags, no checksums), sequence 1, start 0, s_uuid the volume's; the journal in 2 to 5 runs, its indirect blocks between |
| e2fsck's replay (notes/px68/oracle.sh, journals tools/mkjournal wrote) | a revocation suppresses a tag of its own transaction or an earlier one (`>=`), with or without the revoke feature flag; a later tag of the block is replayed; an escaped block's magic restored; a torn commit (its first sector zero) and an open transaction dropped whole; a wrapped log followed; after the replay `s_start 0`, `s_sequence` one past the first sequence not committed; needs_recovery with `s_start 0` replays nothing |
| the Linux guest | kasumi's running kernel is 7.2.8, but its modules directory was removed by the 2026-10-24 upgrade to 7.3.0-4 (`/usr/lib/modules/7.2.8-1-cachyos` gone): the guest is the installed 7.3.0-4-cachyos image (ext4, jbd2, virtio_blk built in). It mounts an ext3 root `using the ext4 subsystem … r/w with ordered data mode`, names it `ext3` (and `ext2` when `rootfstype=ext2` asks, the journal still used), keeps it `clean` with needs_recovery while mounted and after a power cut, says `recovery complete` once at the next boot, refuses an unknown incompatible bit with `Couldn't mount because of unsupported optional features (80000000)` |
| QEMU | 11.1.2 on kasumi; 8.2.2 on the CI runner; both have the trace events `virtio_blk_handle_write`, `_read` and `virtio_blk_req_complete` |

## 3. Prediction, scored (first pass: the kernel's lines and the crash row are in; the oracle row's order is §6's)

| predicted | measured | score |
|---|---|---|
| about 1,300 kernel lines: kernel/journal ~900, ext2 ~200, block ~120, tree/fstab/user ~40, kmain ~30 | 1,863 inserted, 67 deleted at the first hand-back: kernel/journal 1,213 (with its header), ext2 +466/-~50, block +143, fstab +56, files +20, kmain_console +23, tree +9 | wrong: 1.4 times; the journal module 1.35 times, ext2 twice (the features' names, the journal's opening and its refusals) |
| the crash row: counts 0, orphans 0, worse 0 on all 24; lost writes on ~20, none on the rest | 24 kills, 0 counts, 0 orphans, 0 worse; every disk within the last commit's bound and its tree e2fsck -fy's; the torn row held (notes/px68/crash/c1-journal.txt; the first run's classes put a kill before any commit under `none`, 9 of them: since fixed, a kill's class is against the operations done, so those are lost writes: the final row in §6) | right on the gate |
| the session's cost within 10% of px67's (1.05 times) | 30.11, 30.09, 30.14 s against the same kernel's ext2 30.08, 30.05, 30.07 s (and px67's 30.09): 1.001 times; the halt 0.061 s against 0.041 to 0.061 s | right, and closer than guessed |
| replay at boot not visible, under 50 ms | PENDING-rt (§6: QEMU's timestamped trace, the journal superblock's read to the FLUSH after its rewrite) | PENDING-rt |
| the first oracle row to disagree: e2fsck -fn on PAX's first clean unmount, about the journal superblock or needs_recovery | none disagreed: the first smoke boots' e2fsck -fn and e2fsck -fy found nothing on PAX's disks; the first red was the crash tool's own classification (above) | wrong |

## 4. What was built

**kernel/journal** (new): the journal of a volume of kernel/ext2's, its
header the design in full. The format as §2 measured it; the running
transaction (a list of the metadata blocks kernel/block holds for it,
B_JRUN: never written home or evicted); the commit (ordered data first,
then, when the log is empty, the superblock with s_start, the
descriptors, the logged blocks (escaped where they begin with the
magic), the revocation blocks, a FLUSH, the commit block with the close's
wall-clock time, a FLUSH); the checkpoint (committed blocks home, FLUSH,
s_start 0, FLUSH) after a commit that leaves less room than the largest
transaction the cache can hold (RESERVE: 512 buffers, their descriptors,
a full revocation list, the commit), or 4,096 distinct blocks logged, or
an overflow, and at every unmount; revocation (a block logged since the
last checkpoint and freed gets a record; a block logged again loses its
pending one); a freed block is not reallocated before its transaction
commits (the group's bitmap kept from before its first free, honoured by
allocation); the replay (scan, revocations, replay; e2fsck's rules).

**kernel/block**: B_JRUN and B_JMETA; `jdirty`, `jforget`, `jdone`,
`buffer_pa`, `write_data` (ordered data), `checkpoint`; the clock hand
passes over B_JRUN; `sync` and write-through leave them to the journal;
a miss with every buffer held is said once.

**kernel/ext2**: has_journal with its inode is ext3's: the inode's
blocks as runs, the journal's superblock checked, a log with
transactions replayed before the volume is used (one line), the
superblock re-read; needs_recovery served (set at a read-write mount,
cleared at the unmount once the log is empty; the state's VALID bit left
alone, as Linux leaves it); metadata through the journal (`dirty`), data
not (`ddirty`, `wrote`); a directory's new block and a slow link's block
are metadata; an indirect block freed whole keeps its pointers (so a
large delete holds none of them); statfs leaves the journal out of
f_blocks; the mount line's `journal of N blocks in R runs,
data=ordered`; the incompatible and read-only-compatible features named
(super.rst), refused in Linux's words; an external journal refused.

**kernel/fstab, kernel/files**: `ext3, read-write, data=ordered` in the
root's and the table's lines; `rootfstype=ext3` and fstab's `ext3`
(refused for a volume with no journal, as Linux refuses it); the mount
tables name a journalled volume `ext3` (`ext2` when asked); mount(2)
takes `ext3`. **kernel/tree**: a call's start commits a transaction of
128 blocks or more; the syncs pass the wall clock. **kernel/kmain_console**:
`init=PATH` (bootparam(7)) runs one command in place of the run list.

**Tools.** `tools/mkdisk --journal` (and `--gpt --root` journalled by
default, `--no-journal` for ext2: R-px68-3); `tools/mkjournal` (writes
transactions into an ext3 journal from the documented layout, dumps a
journal as a replay's scan reads it, lists every commit block, tears
one); `tools/jorder` (the order a journal's writes and FLUSHes reached
the disk, from QEMU's trace); `tools/root-crash` gated (PAX replays each
killed disk, e2fsck -fy repairs a copy, the last commit's bound, the
torn row, `--check`); `tools/linux-root --fstype`. The probe
(`user/elf/mounts.c`): churn prints the realtime clock after each
operation and takes a sync interval; `revoke`.

**Tests.** `tests/mpx6-journal` (J0-J10: the format; the session's
commits in order by QEMU's trace; a power cut and the next boot; the
replay against e2fsck's on 13 crafted journals and in order; the
refusals; the guest's lines; the crash row gated; the books; PAX's own
revocation; a replay cut short by a failed write (QEMU's blkdebug,
`-set drive.d0.file=blkdebug:…`) and the boot after, which is the row
that holds "the log is emptied only after the blocks are home" to
e2fsck). `tests/mpx6-root` on the journalled root, its guest an
ext3 root (R8 the journal's power cut; R8e px67's on ext2). CI job
`mpx6-journal`; `tools/ci-tiers.map` and `tests/ci-plan`.

## 5. Rulings asked (recommended, implemented, not decided)

**R-px68-1: the data mode.** Recommended, implemented: **(A) ordered**:
a file's data is not journalled, and every dirty data block of the disk
is written before the log blocks of the commit that names it (a superset
of "the blocks that transaction names": the whole disk's dirty data, the
simple rule). Linux's ext3 default (its mount line `with ordered data
mode`, measured). What it rewards, measured: the crash row's lost
writes are bounded by the last commit (§6), no file the last commit
names holds another file's old data (a block freed by a transaction is
not reused before it commits). (B) writeback would skip the data's
write before the commit (faster at each commit; a file the commit names
may then hold stale or another file's bytes after a cut); (C) journal
would log the data too (twice the writes). Reversible: one call in
kernel/journal's `commit`.

**R-px68-2: the commit interval.** Recommended, implemented: **(A) the
flusher's 5 s** (px63's FLUSH_TICKS 500, measured: one commit per 250
operations of the 20 ms churn), plus every sync point (`sync`, `fsync`,
`fdatasync`, `syncfs`, `msync`, a remount read-only, the unmount, the
halt) and, so a transaction never holds the cache, a call's start when it
holds 128 blocks. Measured cost: none visible (30.11 s against 30.08 s
for the same session on ext2, §6); what a cut loses: up to the last 5 s
(17 to 231 operations of the churn, §6). (B) a shorter interval would
bound the loss lower at the price of more commits (each 2 FLUSHes and the
journal's superblock when the log was empty); not measured, as (A) costs
nothing to measure against.

**R-px68-3: the playground's disk.** Recommended, implemented: **(A)
journalled by default** (`tools/mkdisk --gpt --root` makes ext3,
`--no-journal` px67's ext2); this lane ships
`~/pax-playground/pax-disk.img.px68` (§7), and at the merge the
maintainer's current `pax-disk.img` (px67's ext2) would become
`pax-disk.img.ext2` for a session (the orchestrator's step: this lane
touches no file of the maintainer's). (B) both built: an ext2 disk beside
it, which nothing in the playground needs.

**R-px68-4 (new): the plain `tools/mkdisk`'s default.** The contract says
"the default disk becomes journalled". Recommended, implemented: **(A)
the root's** (`--gpt --root`, the playground's and the suites' root
disks) journalled by default; the plain path (`mkdisk [--from DIR]`,
`--home`, `--gpt` without `--root`) stays ext2, because mpx6-ext2's and
mpx6-part's fixtures and recordings are ext2's (their disks' digests are
recorded: changing the type would be editing their goldens); `--journal`
makes any of them ext3. (B) every default journalled, those suites'
fixtures re-made and their recordings re-taken from the guest.

**R-px68-5 (new): the guest's version.** kasumi's 7.2.8 image is gone
(its modules directory removed by the 2026-10-24 upgrade; the running
kernel is still 7.2.8). Recommended, implemented: **(A) the installed
7.3.0-4 image is the guest** for this lane's records (`tests/mpx6-journal.d/linux/`,
and `tests/mpx6-root.d/linux/` re-recorded by its own `--record` with an
ext3 root, the record's diff in §6), named in each record's meta. (B)
wait for a 7.2.8 image (none is on any host; it would need a package).

**R-px68-6 (new): the orphan list.** A file unlinked while it is open
lives until its last close (px27); a power cut in between leaves an
inode with no name and no links, which e2fsck calls an orphan (none of
the crash row's operations does that, so its orphans are 0 by the
workload, not by a mechanism). ext3's answer is the superblock's orphan
list (s_last_orphan, super.rst), processed at the mount. Recommended:
**(A) its own lane**, before or with fsck (px72, §11's draft), with a
probe that unlinks an open file and a cut; not implemented here.

## 6. Witnesses and measurements

**The crash row**, `tools/root-crash --n 24 --seed 67 --ops 1500 --times
3 --torn --check`, kasumi, SeaBIOS, then the same kernel and probe with
`--no-journal` (`notes/px68/crash.sh`). Two runs: c1 with
`660656e3`'s kernel and the first classification (a kill before any
commit counted `none`), c2 with the head's kernel and probe and the
fixed classification (a kill's class against the operations done, the
bound apart), `notes/px68/crash/c{1,2}-{journal,ext2}.txt`:

| class | px67 (ext2, its kernel) | c2: the head's kernel, ext2 | c1: ext3 | c2: the head's kernel, ext3 |
|---|---|---|---|---|
| none | 0 | PENDING-c2 | 9 (before the first commit) | PENDING-c2 |
| lost writes | 20 | PENDING-c2 | 15 | PENDING-c2 |
| counts | 4 | PENDING-c2 | **0** | PENDING-c2 |
| orphans | 0 | PENDING-c2 | **0** | PENDING-c2 |
| worse | 0 | PENDING-c2 | **0** | PENDING-c2 |
| the torn row | — | — | commit 2 of the kill at 12.07 s torn: the tree is commit 1's | PENDING-c2 |

c1's ext2 at the same kernel was px67's row exactly: 20 lost writes, 4
counts (kill 11 `Free blocks count wrong for group #0`, kills 22-24
`Block bitmap differences: -1942 -1973`), 0, 0.

Every journalled disk: `clean, needs_recovery` after the kill, `clean`
after PAX's replay and halt; its tree within the last commit's bound
(the operations up to the last whose clock read came before the commit's
time, or the next); e2fsck -fy of a copy replayed the same journal and
fixed nothing else, its /churn the same as PAX's field for field. The
replays: 0 to 5 transactions, 35 to 335 blocks, 0 revoked (the churn
frees no logged block: J9 is the row that does). Lost after the last
commit: 17 to 231 operations (the flusher's 5 s).

**Cost** (`--times 3`, the uncut session `churn: begin` to `churn: end`,
then to `halt`, the host's clock):

| | session (s) | halt (s) |
|---|---|---|
| px67 (ext2, its kernel) | 30.09 | — |
| c1: ext2, `660656e3` | 30.08, 30.05, 30.07 | 0.041, 0.061, 0.061 |
| c1: ext3, `660656e3` | 30.11, 30.09, 30.14 | 0.061, 0.061, 0.062 |
| c2: ext2, the head | PENDING-c2 | PENDING-c2 |
| c2: ext3, the head | PENDING-c2 | PENDING-c2 |

**The replay's time** (`notes/px68/replay-time.sh`: a journal-suite cut
disk killed 7, 15 and 25 s into `mounts churn 1500`, booted again under
QEMU's trace with `-msg timestamp=on`; TCG, the host's clock):
PENDING-rt

**The suites on kasumi** (`notes/px68/run-suite.sh`, the build in
`px13-ubuntu`, the boots native SeaBIOS, `notes/px68/batch.sh`):

| batch | suite | tree | result |
|---|---|---|---|
| b1 | mpx6-journal (Linux side recorded) | `e15979b9` | 20 PASS, 0 FAIL, 1,283 s (J7 the 12-kill row with the torn one: 12 lost writes, 0 counts, 0 orphans, 0 worse) |
| b1 | mpx6-root (Linux side re-recorded) | `e15979b9` | 27 PASS, 2 rows red: R6 (the guest's ext3 remount prints `EXT4-fs (vda2): re-mounted <uuid> r/w.` on the console in the middle of the probe's `mount(…) = 0` line, which ext2 under 7.2.8 never did: `ba9fdaf4` takes such a message out of the probe's lines) and R8 (its recovery-line count was a basic expression with `+` and `?`: `90147bc9`) |
| b1 | mpx6-ext2, mpx6-part, mpx6-blk | `e15979b9` | 18, 93 and 14 PASS, 0 FAIL |
| b3 | mpx6-root (Linux side re-recorded again) | PENDING-b3 | PENDING-b3 |

**The guest's records.** `tests/mpx6-journal.d/linux/` (new: Linux
7.3.0-4 with an ext3 root: the mount's lines, the table's `/`, a power
cut's needs_recovery and `clean`, `recovery complete` at the next boot,
the refusal of bit 0x80000000). `tests/mpx6-root.d/linux/` re-recorded
by the suite's own `--record` (R-px68-5), never edited; its diff against
px67's 7.2.8 ext2 record: PENDING-b3

## 7. The playground

PENDING-b2

## 8. CI

Dispatches `-f tier=pr -f suites=mpx6-journal` (a partial run: the
`all` rows, 12 kills of 1,500 operations and the torn row):

| run | job | head | what |
|---|---|---|---|
| 40135485369 | — | `6868cbfe` | control before J10: green (CI's QEMU 8.2.2 traces the disk; the record read) |
| 40135993221 | 120997734110 | `39775f58` | control with J10: green, every row J0-J10, the job 13.5 min |
| 40135994966 | 120997741217 | `91d3de3f` | px68-plant-order: red (§9) |
| 40135996743 | 120997736687 | `26f5f020` | px68-plant-revoke: red (§9) |
| 40135998828 | 120997712108 | `dd789a85` | px68-plant-clean: red (§9) |

The PR's `tier pr` (its run id in the PR) runs every suite on native
BIOS, since kernel/ext2 and kernel/block are ALL paths, with J7's pr
rows (4 kills of 600 operations).

## 9. Seen red

Each plant is one commit on the head of its run (`39775f58`), on a
`px68-plant-*` branch, never merged. In every run the other rows stayed
green, J7's crash row among them: none of the three faults opens a
window a kill at the crash row's points lands in, which is why the order
is read from QEMU's trace and why J10 cuts a replay on purpose.

- **px68-plant-order** (`91d3de3f`: the commit block written at its
  place before the transaction's log blocks), run 40135994966 job
  120997741217: **J2 red**, `jorder: 7 commits, OUT OF ORDER: 1 2 3 4 5 6
  7`; J1, J3-J10 green.
- **px68-plant-revoke** (`26f5f020`: the replay finds no revocation),
  run 40135996743 job 120997736687: **J4 red** on exactly the revoked
  cases (B, Bnf, C, C2: PAX `b1b1b1b1` where e2fsck leaves `00000000`)
  and **J9 red** (`2 transactions …, 15 blocks written home, 0 revoked`;
  block 2284 PAX `ed080000`, e2fsck -fy `00000000`).
- **px68-plant-clean** (`dd789a85`: the log emptied, flushed, before the
  replay writes home), run 40135998828 job 120997712108: **J10 red**, the
  e2fsck row: `the replay that stopped short left the log emptied (start
  0); e2fsck -fn: Entry 'f196' in /churn (23) has deleted/unused inode
  68 … has an incorrect filetype …; PAX's tree is not e2fsck -fy's (67
  lines)`; and **J4 red** on every case with a block to replay (A, D, D2,
  E, F, H, I: `jorder: replay: OUT OF ORDER: the log emptied before …`).
  The contract names the e2fsck row; a replay that runs to its end
  leaves the same disk whatever its order, so J3's e2fsck stays green
  under this plant, and J10 was added (`39775f58`) to make the row the
  contract names: a replay cut part-way by QEMU's blkdebug failing one
  block's write, then e2fsck -fn and the tree after the next boot.

## 10. Limits named

- **`sync` on a journalled volume** (fstab's option, write-through):
  its file data is written through; its metadata reaches the disk at the
  journal's commits (the flusher's turn, the syncs, a call's start at 128
  blocks), not before each call returns.
- **One call's transaction** holds at most what the cache can (512
  buffers): a single call that changes more than about 380 metadata
  blocks (a write of more than about 1.5 GiB of new blocks in one
  `write(2)`) finds no buffer to take, said once (`block: no buffer to be
  had`), and fails with -EIO. Freeing is not such a call (a freed
  indirect block is not changed).
- **The orphan list** (R-px68-6) is not kept.
- **The journal's features**: v2 with no feature but revocation; 64-bit
  tags, checksums (v1, v2, v3), asynchronous commits and fast commits are
  refused by name (the volume does not mount), as is an external journal.
- **Volumes past 512 groups** (64 GiB of 4 KiB blocks) keep no freed-block
  guard for the groups past the 512th (`COPIES`).
- **Lazy free counts**: the superblock's counts are journalled with every
  allocation (so e2fsck -fy finds nothing to fix after PAX's replay, where
  Linux's own leaves its free counts for e2fsck: measured, notes/px68/guest.sh g5).

## 11. Issues, fsck's lane, and what to prune

Issues to close: pax#150 (at the merge). To file (none filed here: RULES
§3):
- **the orphan list** (R-px68-6): a file unlinked while open and a power
  cut before its last close leave an inode with no name; ext3 keeps
  s_last_orphan for it, PAX keeps none;
- **the `sync` option's metadata on a journalled volume** (§10): data
  written through, metadata at the journal's next commit;
- **one call's transaction past the cache** (§10): a `write(2)` of more
  than about 1.5 GiB of new blocks fails with -EIO rather than committing
  part-way.

fsck's lane (px72, pax#151): drafted in full in §12.

Prune (at the merge): kasumi `~/lanes/px68/` (the clone, `kb/`, `kc/`,
`kfinal/`, `rec-b1/`, `rt/`, `smoke/`, `crash/`, `guest/`, `oracle/`,
`measure/`, `build/`, `cache/`, `tmp/`, `snap/`, `play/` but the shipped
disk, `lope/`, `logs/`, the plant worktrees `plant-order`, `plant-revoke`,
`plant-clean`, `b1.sh`, `b3.sh`); the branches `px68-plant-order`,
`-revoke`, `-clean` on origin; this Mac's worktrees
`/Users/mfwolffe/lanes/px68/pax` and `/Users/mfwolffe/lanes/px68/plant-*`.

## 12. fsck's lane, drafted (px72, pax#151)

A draft for the orchestrator to edit into `sprints/pax/72-fsck/`; nothing
in it is decided.

### px72 — fsck: check and repair an ext2 or ext3 volume on PAX (pax#151)

**Model: the orchestrator's (a user-space program; the boot hook is a
few lines of kernel/fstab, item 4). Launches on px68's merge, kasumi
cores 0–3.** px67 measured what a power cut costs an ext2 root (24 kills:
20 lost writes, 4 counts) and px68 gave `/` a journal: on ext3 the same
24 kills give 0 counts, 0 orphans, 0 worse, the replay is e2fsck's, and
a host's `e2fsck -fy` after PAX's replay fixes nothing
(`notes/px68-the-journal.md` §6). So the journal leaves fsck less to do
than pax#151 named: not the crash row on `/`, but everything a replay
cannot mend: an ext2 volume (`tools/mkdisk`'s plain path, `--home`,
`--no-journal`, mpx6-ext2's and mpx6-part's disks), an orphan (an
inode unlinked while open when the power went: R-px68-6, no orphan list
kept), a journal the kernel refuses (a tag past the volume's end, a
revocation block's count wrong, a feature it does not serve: the volume
does not mount, §10), and damage no crash makes (a bad disk, a bug).
PAX has no fsck: a damaged volume stays damaged until a host runs
e2fsck on the image.

#### Launch facts
- **Host:** kasumi CPUs 0–3 under `flock ~/lanes/kasumi-cores-0-3.lock`,
  the lane's own `px13-ubuntu` container, QEMU under `taskset -c 0-3`
  with `ulimit -c 0`, long jobs `setsid -f` with a pid file.
- **Branch** `px72` from pax trunk at px68's merge.
- **Read before editing:** px63's, px67's and px68's notes; `kernel/ext2`
  (what PAX serves: rev 1, FILETYPE, sparse_super, large_file,
  resize_inode, dir_index read linear and cleared on a change, ext_attr
  blocks left alone, has_journal with needs_recovery); `tools/e2fs`,
  `tools/e2tree`, `tools/root-crash`, `tools/mkjournal`; `user/su` (a
  wolf program in PAX's tree, built by the pin).

#### Items
1. **The checks, from the manual and the layout.** e2fsck(8)'s passes
   as its prose describes them (inodes and their blocks; the directory
   structure; connectivity; reference counts; the group summaries), for
   the format kernel/ext2 serves and nothing past it (a volume with a
   feature kernel/ext2 refuses is refused by name, as the kernel words
   it). `fsck.ext2 [-n|-y|-p] [-f] DEVICE`, e2fsck's exit codes (0, 1,
   2, 4, 8, 16: e2fsck(8)), one line a problem, a summary line.
2. **The repairs, held to e2fsck -fy.** Every fixture (item 3) repaired
   by PAX's `fsck.ext2 -fy` on PAX and by the host's `e2fsck -fy` on a
   copy: the trees equal field for field (`tools/e2tree`), the host's
   `e2fsck -fn` clean after PAX's repair, PAX's exit code e2fsck's. A
   repair e2fsck makes that PAX's does not (or the other way) is a row
   red with the diff, never a golden edited.
3. **The fixtures.** (a) The ext2 crash disks: `tools/root-crash
   --no-journal --seed 67 --n 24 --ops 1500` gives px67's four counts
   kills again (kill 11 `Free blocks count wrong for group #0`, kills
   22–24 `Block bitmap differences: -1942 -1973`: px68's c1-ext2, the
   same as px67's), and its 20 lost-writes disks, which fsck must leave
   as they are; (b) damage made by `debugfs -w` on a clean disk, one a
   class: a block bitmap bit set and one cleared, a free count, an inode
   bitmap bit, a link count, a directory entry naming a freed inode, a
   block claimed by two files, a directory's size, an inode with no
   name (to lost+found), an orphan (links 0, dtime 0); (c) the journal's
   (tools/mkjournal): a log the kernel refuses (a tag past the end, a
   revocation block's count wrong, CSUM_V3), and a log with transactions
   (fsck on a volume needing recovery: R-px72-2).
4. **At boot** (R-px72-1): the root's not-clean path (R-px67-5's warning
   today) runs `fsck.ext2 -p` before the root is written, one console line
   for its verdict; then the crash row with `--no-journal`, gated: counts
   0, orphans 0, worse 0 after PAX's own fsck, as px68 gated the
   journal's.
5. **Cost:** the check's time on the 128 MiB suite disk and on the
   playground's 448 MiB root, thrice; the boot's time with and without a
   check.
6. **Docs, rows, plants:** `docs/SOURCES.md` (e2fsck(8), the layout
   pages); `docs/BOOT.md` and the README; `tests/mpx6-fsck` (or the name
   ci-tiers.map wants), in `tier pr` if it fits. Plants: pass 5 skipped
   (the counts fixtures red); an orphan's blocks freed but its inode left
   (e2fsck -fn red after the repair); a duplicate block given to both
   files (the tree row red). The note; the PR with pax#126's five
   headings and its Footprint line; lane-audit's last line quoted.

#### Rulings (recommend in the note, the orchestrator decides)
- **R-px72-1 where fsck runs at boot:** (A) Linux's classic order: the
  kernel mounts a not-clean root read-only (px67's `ro`), the run list's
  first command is `fsck.ext2 -p /dev/vda2`, then `mount -o remount,rw /`
  (px67's remount), the kernel forgetting the device's cached blocks at
  that remount as px68's replay does (recommended: no archive needed on
  the disk, and every piece but fsck is there); (B) pax#151's words: the
  kernel leaves a not-clean root unmounted when Limine loaded the rescue
  archive (R-px67-2), the archive's run list checks `/dev/vda2`, then
  reboot(2) (every disk then carries the archive).
- **R-px72-2 a journal at fsck's time:** (A) fsck replays nothing: on a
  volume whose log holds transactions it says so and exits 4 ("mount it:
  the kernel replays"), since with R-px72-1 (A) the kernel has replayed
  before fsck runs; a log the kernel refused is cleared with the user's
  yes (`-y`), the journal re-made empty as mke2fs makes it, has_journal
  kept (recommended: one replay, the kernel's, already held to e2fsck's);
  (B) fsck replays too, e2fsck's way (a second implementation of px68's
  rules in user space, J4's thirteen journals its fixtures).
- **R-px72-3 the orphan list:** (A) px72 clears orphans as e2fsck -fy
  does (the blocks freed, the inode cleared), and the orphan list itself
  (s_last_orphan, kept by the kernel at unlink-while-open and processed at
  mount) stays R-px68-6's own lane (recommended); (B) both here.
- **R-px72-4 where it lives:** (A) `user/fsck` in pax's tree, built by
  the pinned wolf like `user/su` (recommended: it reads the volume
  kernel/ext2 writes, and both move together); (B) a repo of its own
  like boreutils.

#### Forbidden / rules
**Clean-room (ruling #22)**, as px68's: never e2fsprogs' source
(`e2fsck/`, `lib/ext2fs`, `debugfs/`, `misc/`), never any kernel's or
other file system's source, never another fsck's (BSD's fsck_ffs,
Minix's, busybox's). Allowed: e2fsck(8), mke2fs(8), debugfs(8),
dumpe2fs(8), the ext4 layout documentation's prose
(`Documentation/filesystems/ext4/`), and the pinned e2fsprogs binaries as
oracles (`tools/e2fs`). No golden edited: a disagreement with e2fsck is a
STOP with the diff. RULES §1–§10.

#### Inputs (re-derive)
px68's note §6 and §10 (what the journal mends and what it leaves);
`notes/px68/crash/c1-ext2.txt` (the ext2 fixtures' kills); px67's crash
row; `kernel/ext2`'s served features at trunk; the pinned e2fsprogs's
messages for each fixture (`e2fsck -fn`, measured, never read from its
source).

#### Prediction (write before the first change)
How many lines of wolf; which pass's repair first disagrees with
e2fsck -fy, and on which fixture; the check's time on 448 MiB; whether
any of the 20 lost-writes ext2 disks is not clean to e2fsck -fn after the
fsck (none, if the counts are the only damage a cut leaves).

#### Done-when
Items 1–6 with their rows; every fixture repaired as e2fsck -fy repairs
it; the ext2 crash row gated green after PAX's own fsck; plants red by
run id; CI green at the head (`tier pr`); the note and the PR as RULES
§6; hand back with the run id, the issues to close (pax#151) and to file,
the prune list.
