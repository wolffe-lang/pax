#!/usr/bin/env python3
"""Make a full sparse ext3 fixture with /old's only block in the last group.

Only unmounted image files are written. e2fsprogs is a black-box builder and
checker; direct field edits follow the published legacy on-disk layout. File
data allocated for filler remains a host-file hole; only pointer blocks and
bitmaps are written. An independent e2fsck checks the completed allocation.
"""
import argparse
from array import array
from pathlib import Path
import os
import re
import struct
import subprocess

BS = 4096


def command(argv):
    args = list(map(str, argv))
    if os.environ.get("PAX_E2FS_NATIVE") != "1":
        root = Path(__file__).resolve().parents[2]
        args = [str(root / "tools/e2fs"), str(Path(args[-1]).resolve().parent), *args]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"{argv}: {r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def read(f, off, n):
    f.seek(off)
    b = f.read(n)
    if len(b) != n:
        raise RuntimeError("short fixture read")
    return b


def write(f, off, b):
    f.seek(off)
    f.write(b)


def map_blocks(n):
    total = n
    if n > 12:
        total += 1
    if n > 12 + 1024:
        double = min(n - 12 - 1024, 1024**2)
        total += 1 + (double + 1023) // 1024
    if n > 12 + 1024 + 1024**2:
        triple = n - 12 - 1024 - 1024**2
        total += 1 + (triple + 1024**2 - 1) // 1024**2 + (triple + 1023) // 1024
    return total


def make(out, gib):
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = out / "source"
    source.mkdir()
    (source / "old").write_bytes(b"A" * BS)
    (source / "filler").write_bytes(b"")
    (source / "tail").write_bytes(b"")
    image = out / "full.img"
    with image.open("wb") as f:
        f.truncate(gib * 1024**3)
    command(["mke2fs", "-q", "-F", "-t", "ext3", "-b", str(BS), "-N", "4096",
             "-J", "size=16", "-O", "^resize_inode,^dir_index", "-E", "lazy_itable_init=0",
             "-d", source, image])

    def inode(name):
        text = command(["debugfs", "-R", "stat /" + name, image])
        (out / (name + ".stat.txt")).write_text(text)
        return int(re.search(r"Inode:\s+(\d+)", text)[1])

    old, filler, tail = inode("old"), inode("filler"), inode("tail")
    with image.open("r+b") as f:
        sb = read(f, 1024, 1024)
        blocks = struct.unpack_from("<I", sb, 4)[0]
        bpg = struct.unpack_from("<I", sb, 32)[0]
        ipg = struct.unpack_from("<I", sb, 40)[0]
        isize = struct.unpack_from("<H", sb, 88)[0]
        groups = (blocks + bpg - 1) // bpg

        def ino_offset(number):
            group, index = divmod(number - 1, ipg)
            table = struct.unpack("<I", read(f, BS + group * 32 + 8, 4))[0]
            return table * BS + index * isize

        oldoff, filloff, tailoff = ino_offset(old), ino_offset(filler), ino_offset(tail)
        low = struct.unpack("<I", read(f, oldoff + 40, 4))[0]
        group = groups - 1
        bitmap_block = struct.unpack("<I", read(f, BS + group * 32, 4))[0]
        bitmap = read(f, bitmap_block * BS, BS)
        high = next(group * bpg + bit for bit in range(blocks - group * bpg - 1, -1, -1)
                    if not bitmap[bit // 8] & (1 << (bit % 8)))

        def allocate(block, used):
            g, bit = divmod(block, bpg)
            gd = BS + g * 32
            bm = struct.unpack("<I", read(f, gd, 4))[0]
            value = read(f, bm * BS + bit // 8, 1)[0]
            mask = 1 << (bit % 8)
            if bool(value & mask) == used:
                raise RuntimeError("unexpected block allocation state")
            write(f, bm * BS + bit // 8, bytes([value | mask if used else value & ~mask]))
            count = struct.unpack("<H", read(f, gd + 12, 2))[0]
            write(f, gd + 12, struct.pack("<H", count - 1 if used else count + 1))

        write(f, high * BS, read(f, low * BS, BS))
        allocate(high, True)
        allocate(low, False)
        # The old location becomes sparse filler data: do not leak its A bytes
        # into the filler read used to exert cache pressure.
        write(f, low * BS, bytes(BS))
        write(f, oldoff + 40, struct.pack("<I", high))
        free = array("I")
        for g in range(groups):
            gd = BS + g * 32
            bm = struct.unpack("<I", read(f, gd, 4))[0]
            bits = read(f, bm * BS, BS)
            limit = min(bpg, blocks - g * bpg)
            free.extend(g * bpg + bit for bit in range(limit)
                        if not bits[bit // 8] & (1 << (bit % 8)))
            write(f, bm * BS, b"\xff" * BS)
            write(f, gd + 12, bytes(2))
        available = struct.unpack("<I", read(f, 1024 + 12, 4))[0]
        if len(free) != available:
            raise RuntimeError("free bitmap/count disagreement")
        lo, hi = 0, available
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if map_blocks(mid) <= available:
                lo = mid
            else:
                hi = mid - 1
        remaining = available - map_blocks(lo)
        if not lo or remaining > 12:
            raise RuntimeError("unexpected legacy allocation boundary")
        cursor = 0

        def take():
            nonlocal cursor
            b = free[cursor]
            cursor += 1
            return b

        def tree(level, count):
            if level == 0:
                if count != 1:
                    raise RuntimeError("invalid leaf span")
                return take()
            block = take()
            stride = 1024**(level - 1)
            pointers = []
            while count:
                child = min(stride, count)
                pointers.append(tree(level - 1, child))
                count -= child
            if len(pointers) > 1024:
                raise RuntimeError("pointer block overflow")
            pointers.extend([0] * (1024 - len(pointers)))
            write(f, block * BS, struct.pack("<1024I", *pointers))
            return block

        pointers = [take() for _ in range(min(12, lo))]
        count = lo - len(pointers)
        pointers.extend([0] * (12 - len(pointers)))
        for level in range(1, 4):
            span = min(count, 1024**level)
            pointers.append(tree(level, span) if span else 0)
            count -= span
        if count or cursor != map_blocks(lo):
            raise RuntimeError("legacy map allocation disagreement")
        size = lo * BS
        write(f, filloff + 4, struct.pack("<I", size & 0xffffffff))
        write(f, filloff + 108, struct.pack("<I", size >> 32))
        write(f, filloff + 28, struct.pack("<I", cursor * 8))
        write(f, filloff + 40, struct.pack("<15I", *pointers))
        tail_blocks = [take() for _ in range(remaining)]
        write(f, tailoff + 4, struct.pack("<I", remaining * BS))
        write(f, tailoff + 28, struct.pack("<I", remaining * 8))
        write(f, tailoff + 40, struct.pack("<15I", *(tail_blocks + [0] * (15 - remaining))))
        if cursor != available:
            raise RuntimeError("fixture has unassigned allocated blocks")
        write(f, 1024 + 12, bytes(4))
    check = command(["e2fsck", "-fn", image])
    (out / "initial.fsck.txt").write_text(check)
    facts = f"blocks={blocks} groups={groups} old_block={high} old_group={group} filler_bytes={size}\n"
    (out / "facts.txt").write_text(facts)
    print(facts, end="", flush=True)
    print(f"allocated_host_bytes={image.stat().st_blocks * 512}", flush=True)
    return image


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--gib", type=int, default=65)
    p.add_argument("out")
    args = p.parse_args()
    make(args.out, args.gib)
