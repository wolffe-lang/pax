# Read-only ext4 extent trees in the kernel (written before the first change)

Base: trunk `ce322118`. The user-space half of ext4 extents is merged: `paxext2 --extents` makes extent trees and
`fsck.ext2` checks them, both held to pinned e2fsprogs. This change is the kernel's first half: an explicit `ext4`
mount that reads the ext3-plus-extents profile and writes nothing. Writing extent trees is later work, behind a
separately reviewed orphan stage.

## What it adds
- **The type.** `ext4` in `mount(2)`, fstab and `rootfstype=`; `/proc/self/mounts`, mountinfo and the boot lines name
  it. An `ext2` or `ext3` ask of an extent volume keeps today's refusal, word for word. An `ext4` ask of a volume
  without the extent feature is refused by name. A root with no `rootfstype=` keeps today's refusal: an ext4 root
  needs `rootfstype=ext4`. The unknown-type refusals name ext4 among the types PAX mounts.
- **The profile.** INCOMPAT filetype and extent; COMPAT has_journal or nothing; RO_COMPAT within sparse_super and
  large_file; 1, 2 or 4 KiB blocks; groups of eight times the block size with their metadata at the group's start.
  Every other bit is refused by its published name, read-only too: 64bit, flex_bg, metadata_csum and its seed,
  inline_data, huge_file and the rest. The mount is read-only whatever it asked (a read-write ask says so; a
  read-write remount is EROFS) and writes nothing to the disk.
- **Clean volumes only.** A volume that needs recovery, holds journal transactions, has an orphan list, records errors
  or was not cleanly unmounted is refused unchanged, with the instruction to check it offline. The journal is mapped
  and checked but never begun and never replayed.
- **The walk.** An inode with EXTENTS_FL maps through its tree; one without keeps the block map. A lookup visits at
  most six nodes by a loop, never by recursion or allocation. Each node is checked whole before its child is
  fetched: magic 0xf30a; eh_max at most the node's room and at least two under it (the values pinned e2fsck accepts,
  measured at rooms 4, 84 and 340, and Linux reads); entries at most eh_max; depth at most 5 and exactly one under the
  parent's; keys increasing inside the range the parent gave; no block twice on the path; every extent of 1 to 32768
  blocks inside the volume, off the group metadata and off the journal's blocks. Holes and unwritten extents read as
  zeros; an unwritten extent's disk bytes are never returned.
- **Damage is EIO.** A damaged path answers EIO with a line naming the device and inode: a file's read, a directory's
  lookup or listing (never absence, never a short listing) and a link's resolution. For ext4 only; ext2 and ext3
  answer as they do today.
- **kernel/journal** gains one read-only query, whether blocks are the journal's, for the walk's last check. No
  journal behaviour changes.

## What it does not do
- Write anything, replay anything, or admit any feature beyond the profile.
- Change a single ext2 or ext3 line, default or transcript. ext3 stays the installer's default.
- Answer SIGBUS for a mapped page whose blocks cannot be read. Such a page maps as zeros, on ext4 as on ext2 and
  ext3 today; Linux answers SIGBUS. That fix touches the memory code and comes as its own change (pax#571).

## Rows, red first
Every row lives in `tests/mpx6-ext2.d` and runs in `tests/mpx6-ext2` after its existing rows, which stay as they are.
Fixtures are paxext2's own output and pinned mke2fs's, held to pinned e2fsck and debugfs, with damage made as byte
edits of copies; e2fsck's verdict on each copy is saved, never assumed.

All rows are committed before any kernel change. At that point every row that needs an `ext4` mount must be red,
because trunk answers ENODEV, refuses an fstab `ext4` line and refuses `rootfstype=ext4`; a row red for any other
reason (a missing file, program or fixture) is a fault in the rows. The rows already green there are trunk's own
answers: the ext2 and ext3 refusals of extent media, a root with no type, and every image unchanged after its boot.

The row groups: the type and its lines (mount, fstab, root, mounts, mountinfo, the unknown-type text); read-only
(every write refused, the disk byte-identical after every boot); reads at every extent and index boundary at depths
0, 1 and 2; degenerate chains of depth 3, 4 and 5; an extent whose length field is 32768 (initialized, so on this
profile it always meets a group's metadata and is refused, where reading it as unwritten would give zeros);
unwritten ranges; a 5 GiB sparse file; a file in a second block group; 1 KiB blocks; an indirect inode beside
extent inodes; directories, fast and slow links; the journal accepted clean, and refused holed, unwritten, past 64
runs or on metadata; every refused feature bit and unclean state, by name, for read-only and read-write asks; a
default `mke2fs -t ext4` image, refused naming its incompat bits; every damage case; the buffer cache past 512
buffers; the same boots at four processors with two readers at once; and files a live Linux kernel made
(contiguous, sparse to depth 2, fallocated, a directory, both link kinds) read back byte for byte.

The three layout rows (the deep chains, the extent of length 32768, the mixed volume) get their expectations only after
pinned e2fsck and Linux have been run on their fixtures.

## Plants
Each is one hunk on a branch of its own, never merged, red by name:
- the parent-child depth rule dropped: the damage row only that rule catches;
- an unwritten extent's disk block returned: the unwritten rows and the unwritten journal's refusal;
- metadata_csum admitted: its three feature rows;
- a damaged directory's mapping read as a hole: the directory EIO rows;
- eh_max one past the room admitted: that damage row;
- any eh_max under the room admitted: the four rows below the floor;
- every inode of an ext4 volume mapped through a tree: the mixed row;
- `ee_len` 32768 read as unwritten: the row of that extent;
- the walk stopped after two index levels: the depth 3, 4 and 5 rows;
- the group-metadata test dropped: the metadata damage row and the journal on metadata.

## Prediction and what would falsify it
- The extent rows are green at the head on native BIOS at one and four processors, then on the other three legs;
  the ext2, journal, cache, root, partition, nodes and fsck suites are green with their lines unchanged; the census
  moves sites and adds none; the seam keeps its two rows with one more constant.
- No fixture image changes in any boot.
- Each plant reddens exactly its rows.
- Falsified by: a row red at the red point for a reason other than the type or feature refusal; an oracle refusing a
  layout fixture; Linux's writes leaving the profile; any ext2 or ext3 line changing; any image written by a boot; a
  plant missing a row or reddening one more; the four-processor boots differing from one processor's.

## When the work stops
At the first falsifier, with the take that showed it. No take is repeated for a different answer. A row whose
expected value is a layout choice waits for its oracle. Nothing here touches the memory, paging, scheduler or lock
code; a need to would stop the work.
