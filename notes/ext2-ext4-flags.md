# Ext4's inode flags on ext2 and ext3 volumes (written before the first record take)

Base: trunk `02ad2cbb`, with read-only ext4 extent trees merged. pax#549: on a volume without the extent feature,
kernel/ext2 maps every inode through its block map and never looks at its flags, so an inode carrying EXTENTS_FL
(0x80000) or INLINE_DATA_FL (0x10000000) has its 60 bytes of i_block read as fifteen block pointers. This change
calls either flag damage there. It touches kernel/ext2 alone.

## What was measured first
Copies of small ext2 and ext3 images (pinned mke2fs, 1 KiB blocks, a file, a sibling, a directory with an entry, a
slow and a fast link), one inode's flags set per copy by pinned debugfs, its pointers left valid: the file, the
directory, the slow link, the fast link, the root, and ext3's journal inode, each with either flag.
- **Pinned e2fsck** (1.47.0) calls every copy damage, exit 4, on two hosts alike: `Inode 14 has EXTENTS_FL flag set on
  filesystem without extents support`, `Inode 14 has INLINE_DATA_FL flag on filesystem without inline data
  support`, and the root's and journal's consequences.
- **Linux through ext4's subsystem** (which mounts ext3 everywhere, and ext2 on a kernel built without the ext2
  driver; 6.8 and 7.2.4 alike): EXTENTS_FL on a file, directory or slow link answers EUCLEAN at the lookup
  (`EXT4-fs error … ext4_ext_check_inode … bad header/extent: invalid magic`), and on the root or the journal the
  mount fails; each of these records the error on the disk, read-only mounts too. A fast link carrying EXTENTS_FL is
  read (its target, no kernel line). INLINE_DATA_FL is ignored on every inode, root and journal included. Read-write,
  removing the extent-flagged file fails; removing the inline-flagged one succeeds.
- **Linux through its own ext2 driver** (7.2.4, where ext2 is a module): both flags ignored on every inode, the root
  included; every copy reads as if unflagged, the disk unchanged; read-write, both files are removed.

## What it changes
- On an ext2 or ext3 mount, a name whose inode carries either flag answers EIO at its lookup, with a line naming the
  device, the inode and the flag (`ext2: vda: inode 14: EXTENTS_FL on a volume without the extent feature, i_flags
  0x…`), counted in the volume's books. It is never read as block pointers and never answers absence. A listing
  still names it.
- A root or ext3 journal inode carrying either flag refuses the mount by name (`ext2: refused: vda: inode 2 (the
  root) carries …`), as a root that is no directory is refused today.
- A read-only mount writes nothing. A read-write unmount after such damage leaves an ext2 volume not cleanly
  unmounted. A journalled volume's state is left as it was, as it is today for every damage kernel/ext2 names; that
  is noted by the rows, not changed here.
- Valid ext2 and ext3 volumes carry neither flag, so no valid image reads differently. Extent volumes keep their
  own checks unchanged.

Where Linux differs, PAX answers EIO on purpose, as e2fsck calls it: the fast link with EXTENTS_FL and every inode with
INLINE_DATA_FL (against ext4's subsystem), every flagged inode (against the ext2 driver), and Linux's EUCLEAN.

## Rows, red first
The flag rows (XF) run in `tests/mpx6-ext2`'s extent rows, at one processor and at four on each leg: 22 flagged
copies (fixture set G), six read-only boots of four copies and one read-write boot of the file's four copies. 168
rows a pass and seven boot-end rows. Committed before the kernel change; at that point exactly 86 must be red, each by
its own check, because trunk reads every flagged inode's pointers (valid in these copies):
- for each of the 16 read-only copies of a file, directory or link, its flagged item's EIO rows (stat and read; stat,
  listing and a lookup inside; stat and readlink) and its damage line: 52;
- the four root copies' and two journal copies' refusals and refusal lines: 12;
- for the four read-write copies, the stat and the unlink (EIO), the listing still naming the file, the damage line
  and the inode kept on the disk, and the two ext2 copies left not clean: 22.
Every other flag row passes on trunk: each copy's mount and unmount, every other name read as made, the read-write
sibling, and every read-only copy byte-identical after its boot. Every existing extent row passes on trunk and at the
head.

## The plant
One hunk on its own branch, never merged: the helper never says damage. It must redden exactly the 86 rows.

## Prediction and what would falsify it
- The extent rows, the flag rows with them, green at the head on all four legs at one and four processors; the ext2,
  journal, cache, root, partition and nodes suites green with their lines unchanged; the census moves sites and
  adds none; the seam's rows unchanged.
- Falsified by: a flag row red at the red point for another reason, or one of the 86 green there; any valid ext2 or
  ext3 line changing; a flagged inode read as pointers on any path; a sibling or a listing changing; a read-only
  copy written; the plant missing a row or reddening one more.
