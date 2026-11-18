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

## 4. The red, and where the window opens

`tests/mpx6-ext2-cache` (its rows in `tests/mpx6-ext2-cache.d/rows.py`, its probe `user/elf/churn.c`) boots
kmain_console with a 20 GiB sparse ext2 volume (160 groups of 32,768 blocks, 256 inodes a group, so 12,121 inodes
over about 50 groups' tables and two descriptor blocks) at /mnt, write-back. Every take below ran native BIOS under
KVM, one light slot, from a commit.

| take | head | scene | modes | pressure |
|---|---|---|---|---|
| red62-a | the image head with the rows (`1d36c092`) | green | **red**: `ext2: vda: an I/O error writing block 1015825 (said once; …)`; 793 of 12,000 modes lost | red by the probe, not the kernel: its fork found no frames for a copy of the memory it held (fixed since: the appender is forked first) |
| red62-b | the image head with the rows (`ebbe35f8`) | green | **red**: the same line; 801 lost | green |
| check-3dda6f83 | the check alone | green | **red**: `ext2: vda: a kernel bug: ext2 dirtied an uncached block 1015825; the change is lost (not a disk error)`, eight times, then counted; 884 lost | green |
| fix-ff3f7aec | the fix | green | green: every file 0600 | green |

- **Block 1015825** is group 31's last inode-table block, as the installed root's 328169 is group 10's table block
  487. `e2fsck -fn` was clean after every take: a lost mode or time breaks nothing e2fsck checks.
- **The scene row stays green at the base.** The walk reads each file, and relatime's access time is set by `touch`
  right after `time()` read the same inode, so the inode's block and its group's descriptor block are both cached
  when `idirty` asks. The window opens when the change's own `inode()` misses: the hand may then take the
  descriptor block for the inode's block, and `idirty`'s `get` takes the inode's block back for the descriptor.
  chmod after a walk (the modes row), an append whose inode block went clean at the flusher's last turn, and a
  create or truncate in a cold group all do. The scene row is kept as the workload the installed machine ran.
- **P3 held.** Memory pressure (the probe held all but 48 MiB) moved nothing: the cache's 512 buffers are made once
  and kept, and frames are never taken back from it.
- **P5 held.** No stale-buffer line came in any take: every lost change was written before its buffer was taken,
  then overwritten by the descriptor block's bytes from the disk.

## 5. The fix

- **`inode_w` and `imark`** (`kernel/ext2/ext2.lu`). `inode_w(v, ino)` answers the inode's address and its table
  block. Every writer (`touch`, `set_times`, `set_mode`, `set_nlink`, `set_owner`, `set_size`, `add_blocks`,
  `unindex`, `ialloc`, `ifree`, `bmap`'s new pointer, `truncate`'s cleared pointers, a short link's target) keeps
  the block and marks it with `imark(v, ib, a)`, which asks for nothing. `idirty` is gone, so no caller can find
  the block again between a change and its mark.
- **`written` and `stray`** (`kernel/block/block.lu`). `written(d, blk, bsize, va)` answers 0 when the cache holds
  the block and `va` is inside its buffer, -ENOSPC when the cache holds no such block, and -ESTALE when `va` is
  elsewhere. `stray(va)` names the block whose buffer `va` is in, and forgets that buffer when it is clean, so stray
  bytes never reach its disk.
- **`landed`** (`kernel/ext2/ext2.lu`). `dirty` and `ddirty` take the address the change went through (`wrote`
  takes the last `wspan`'s). Before marking, they ask `written`. A change that did not land is said as a kernel bug
  (the module's header gives both lines), counted in the structures found wrong (so the unmount does not mark the
  volume clean), and not marked. The first eight a volume are said; one line says when the rest are only counted.
  The disk's own write errors keep their line.

## 6. Decisions

- **R-px164-1: the base.** Options: trunk; #455's branch. Recommended and ruled: #455's branch (`44fb9937`). The
  window has existed on trunk since px63, but only #455's skip makes it reachable, and the next image carries
  #455. The branch is restacked when #455 rebases.
- **R-px164-2: a lost change's line.** Options: keep `corrupt`'s once-a-volume line with new words; a line for each
  loss; the first eight, then a count. Recommended and implemented: the first eight a volume. Each loss is a change
  gone, so one line hides the rest (the installed machine said one and may have lost more), and a regression must
  not flood a polled console.
- **R-px164-3: the stale-buffer case.** Options: say it only; also forget the buffer the bytes went into.
  Recommended and implemented: forget it when it is clean, so the stray bytes never reach its disk. When it is
  dirty they cannot be told from its own changes, and the line says that it is dirty.
- **R-px164-4: the scene row's green at the base.** Options: drop it; keep it as a workload row beside the modes row.
  Recommended and implemented: keep it. It is the installed machine's load (a large walk beside a log writer and the
  flusher's turns), and it holds the appended log whole after the fix. The modes row is the red-first row and the
  plant's.

## 7. What a lost change leaves on a plain ext2 volume

The disk keeps the inode as it was before the change, and so does the kernel from then on: the next `get` reads the
old bytes back. By the change lost:

| change lost | what the disk holds | `e2fsck -fn` |
|---|---|---|
| an access, modification or change time | the old time | nothing to see |
| a mode or an owner (chmod, chown) | the old mode or owner, silently: a file made private can stay readable | nothing to see |
| a size (an append, a truncation, an extension) | the old size; the bytes past it are unreachable, and the next append writes over them | `i_size is X, should be Y` when blocks lie past the old size |
| `i_blocks` | the old count | `i_blocks is X, should be Y` |
| a new block's pointer (`bmap`) | a hole where the data went; the block allocated and leaked. For an indirect block, every data block under it | block bitmap differences, free counts |
| a cleared pointer (`truncate`) | the inode still points at a block that is then freed and may be given to another file: two files on one block | multiply-claimed blocks, or bitmap differences before the reuse |
| a link count | too high: a leak when the last name goes; too low: the inode freed while a name still leads to it | inode ref count wrong; an entry naming a deleted or unused inode |
| a new inode's whole first write (`ialloc`) | its bit set, the inode on the disk as it was (zeros, or a deleted inode's bytes), and then a name of it | an entry naming a deleted or unused inode; an inode bitmap difference |
| a freed inode's links and dtime (`ifree`) | an inode that looks live, its bit then cleared | an unattached or deleted inode; bitmap differences |

A volume that has said the line once has said nothing about any later loss in the same boot: only the first was
printed, and the rest were counted in the volume's books, which nothing shows.

## 8. Not done

- The rows ran on native BIOS only. The release tier and UEFI are CI's (the job runs the plan's legs).
- No row exercises the stale-buffer line by a real fault: no ext2 path writes through an old address after another
  `get` now. `stray` is reached only from `landed`'s -ESTALE.
