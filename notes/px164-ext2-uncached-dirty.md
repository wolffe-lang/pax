# px164 — ext2 dirtied an uncached block: an inode's change lost under write-back

An installed machine, idle at its shell prompt with its root on plain ext2 (no journal) under write-back, printed:

    ext2: sda2: an I/O error writing block 328169 (said once; the books count every one)

There was no block-layer or AHCI line near it. The disk was not at fault. The words come from ext2's `corrupt`, called
from `dirty` when kernel/block's `dirty_meta` answered nonzero. Under write-back that answer can only be -ENOSPC,
which means the block is not in the cache: ext2 marked dirty a block whose buffer the cache had already taken back.

## 1. Forbidden, and what was read

- **Clean room.** No other kernel's, file system's or e2fsprogs' source. e2fsprogs is run as a black box.
- **Read:** `kernel/ext2/ext2.lu`, `kernel/block/block.lu`, `kernel/tree/tree.lu` (the read and write paths, the
  access time), `kernel/fstab/fstab.lu` (the flusher), `kernel/signal/signal.lu`, `kernel/sched/sched.lu` (who
  raises SIGKILL), `user/init/init.lu`, `user/disktools/paxext2/main.lu` (the installed root's layout).
- **References:** the ext2 layout documents the module's header names; `chmod(2)`, `getdents64(2)`, `sync(2)`.

## 2. Inputs, verified

- **Base:** the branch of pax#455 (`44fb9937`), whose kernel/block and kernel/ext2 are byte for byte the installed
  image's (`f2ae1a31`). The rows were also run at that image head.
- **The machine's facts** (from its boot log): the root is 244,173,745 blocks of 4096 bytes in 7,452 groups,
  61,046,784 inodes of 256 bytes (8,192 a group), mounted read-write and write-back. With 32,768 blocks a group and
  512 inode-table blocks a group (the installer's layout), block 328,169 is table block 487 of group 10: inodes
  89,713 to 89,728.

## 3. Prediction

Written before the first change (2026-11-18):

- **P1, the cause.** `idirty(v, ino)` finds the inode's block through `iloc`, and `iloc` reads the group
  descriptor's inode-table word with a `get` of the descriptor block. Every caller writes the inode's bytes into the
  buffer that `inode()` returned and then calls `idirty`, so a `get` runs between the change and its mark. That
  breaks the cache's rule ("an address is good until the next `get` or `fresh`"). When the descriptor block is not
  cached, the clock hand runs. Under write-back since pax#455 it passes every dirty metadata buffer by, so it chooses
  among the clean and data buffers only. The inode's block, clean until this mark, is one of them. Taken back, its
  frame receives the descriptor block's bytes, the change is gone, and `dirty_meta` answers -ENOSPC. The line names
  the inode-table block. The fewer buffers the hand may take, the likelier this is: many inodes changed between two
  of the flusher's turns (a large walk's access times, a log's appends) leave few.
- **P2, the rows red at the base.** On a write-back mount, a walk of 12,000 files beside an appender (the scene row),
  and chmod of every file (the modes row), print `ext2: vda: an I/O error writing block N` with N in an inode table.
  Some access times or modes are not on the disk afterwards. If a lost change was the log's size, `/log/app.log`
  loses lines and `e2fsck -fn` finds the size or block count wrong. This is likely, not certain: the hand's position
  and the flusher's turns move it.
- **P3, memory pressure changes nothing.** The cache's buffers are made once and kept, and frames are never taken
  back from it, so the pressure row is the scene row's result.
- **P4, the fix.** The inode writers keep the block their `inode()` read. The mark then needs no lookup, nothing runs
  between a change and its mark, and every row is green.
- **P5, a write through a stale buffer.** In this path the change is written before the buffer is taken, so it is
  lost, not misdirected: the frame is then filled with the descriptor block's bytes from the disk, and no caller
  writes through the old address after `idirty`. A check at every mark (the address written through must still be
  the block's buffer) makes any other case loud.
