#!/usr/bin/env python3
"""Move a known fixture's inode and direct block beyond the 2 TiB boundary.
Own ext2 layout writer; independent e2fsck must accept its result before boot.
"""
import argparse
from pathlib import Path
import struct
import subprocess

p = argparse.ArgumentParser()
p.add_argument('formatter', type=Path)
p.add_argument('image', type=Path)
a = p.parse_args()
tree = a.image.parent / 'high-tree'
tree.mkdir(exist_ok=True)
(tree / 'high').write_bytes(bytes((i * 17 + 11) & 255 for i in range(4096)))
subprocess.run([str(a.formatter), '--from', str(tree), '--inodes', '16', str(3 << 40), str(a.image)], check=True)


def u(b, at, fmt='<I'):
    return struct.unpack_from(fmt, b, at)[0]


def put(b, at, n, fmt='<I'):
    struct.pack_into(fmt, b, at, n)


def supers(g):
    if g in (0, 1):
        return True
    for prime in (3, 5, 7):
        n = g
        while n % prime == 0:
            n //= prime
        if n == 1:
            return True
    return False


with a.image.open('r+b') as f:
    def read(at, n):
        f.seek(at)
        b = bytearray(f.read(n))
        assert len(b) == n
        return b

    def write(at, b):
        f.seek(at)
        f.write(b)

    sb = read(1024, 1024)
    blocks, bpg, ipg = u(sb, 4), u(sb, 32), u(sb, 40)
    groups = (blocks + bpg - 1) // bpg
    gd = read(4096, groups * 32)
    root = read(u(gd, 8) * 4096 + 256, 256)
    rootblock = u(root, 40)
    directory = read(rootblock * 4096, 4096)
    at = 0
    while directory[at + 8:at + 8 + directory[at + 6]] != b'high':
        at += u(directory, at + 4, '<H')
        assert at < 4096
    oldino = u(directory, at)
    oldgroup = (oldino - 1) // ipg
    oldat = u(gd, oldgroup * 32 + 8) * 4096 + (oldino - 1) % ipg * 256
    inode = read(oldat, 256)
    oldblock = u(inode, 40)
    group = (1 << 29) // bpg + 1
    ino = group * ipg + 1
    block = u(gd, group * 32 + 8) + ipg // 16
    assert block * 4096 > 1 << 41
    assert block < blocks
    data = read(oldblock * 4096, 4096)
    write(block * 4096, data)
    put(inode, 40, block)
    write(u(gd, group * 32 + 8) * 4096, inode)
    write(oldat, bytes(256))
    put(directory, at, ino)
    write(rootblock * 4096, directory)
    for g, bit, field, used in [(oldgroup, (oldino - 1) % ipg, 4, False), (group, 0, 4, True),
                                (oldblock // bpg, oldblock % bpg, 0, False), (group, block % bpg, 0, True)]:
        bm_at = u(gd, g * 32 + field) * 4096
        bm = read(bm_at, 4096)
        assert bool(bm[bit // 8] & (1 << (bit % 8))) != used
        if used:
            bm[bit // 8] |= 1 << (bit % 8)
        else:
            bm[bit // 8] &= 255 ^ (1 << (bit % 8))
        write(bm_at, bm)
        count = g * 32 + (14 if field == 4 else 12)
        put(gd, count, u(gd, count, '<H') + (-1 if used else 1), '<H')
    for g in range(groups):
        if supers(g):
            write((g * bpg + 1) * 4096, gd)
    print('HIGH FIXTURE inode=%d block=%d byte_offset=%d sector=%d' % (ino, block, block * 4096, block * 8), flush=True)
subprocess.run(['e2fsck', '-fn', str(a.image)], check=True)
print('PASS B-high-fixture: independent checker clean', flush=True)
