#!/usr/bin/env python3
"""Large ext2 geometry, real e2fsck, bounded sparse files; no oracle source.
Default CI rows use an explicit small inode budget; --density measures defaults.
Images are processed one at a time and removed even on a failed assertion.
"""
import argparse
import os
from pathlib import Path
import shutil
import struct
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('binary', type=Path)
p.add_argument('out', type=Path)
p.add_argument('--density', action='store_true')
p.add_argument('--sizes', nargs='+', type=int, default=[8 << 30, 64 << 30, 500000000000, 4000000000000, (1 << 44) - 4096])
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
os.environ['SOURCE_DATE_EPOCH'] = '1700000000'
LIMIT = (1 << 44) - 4096


def run(row, argv):
    start = time.monotonic()
    result = subprocess.run([str(x) for x in argv], capture_output=True)
    elapsed = time.monotonic() - start
    (a.out / (row + '.log')).write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, (row, result.returncode, result.stdout, result.stderr)
    print('PASS', row, 'seconds=%.6f' % elapsed, flush=True)
    return result


def read(f, at, n):
    f.seek(at)
    b = f.read(n)
    assert len(b) == n
    return b


def u32(b, at):
    return struct.unpack_from('<I', b, at)[0]


def backup(g):
    if g in (0, 1):
        return True
    for prime in (3, 5, 7):
        n = g
        while n % prime == 0:
            n //= prime
        if n == 1:
            return True
    return False


# Refusal must precede opening/truncating even when the backing filesystem
# cannot represent a >=16 TiB regular file. Only a tiny existing sentinel.
sentinel = a.out / 'refusal.img'
sentinel.write_bytes(b'px84-preserve-existing-target')
for size in (LIMIT + 4096, 17 << 40, 9223372036854771712):
    r = subprocess.run([str(a.binary), str(size), str(sentinel)], capture_output=True)
    assert r.returncode == 1 and b'too_large' in r.stderr, ('B-limit', size, r.stderr)
    assert sentinel.read_bytes() == b'px84-preserve-existing-target'
print('PASS B-limit: named refusals leave target unchanged', flush=True)
sentinel.unlink()

for requested in a.sizes:
    size = requested // 4096 * 4096
    name = 'B-%d' % requested
    image = a.out / (name + '.img')
    # A density row may consume size/64 in inode tables; refuse before
    # formatting if the host cannot hold it plus a 2 GiB safety margin.
    ratio = 32768 if size >= 4 << 40 else 16384
    needed = size // ratio * 256 + (size // (128 << 20) + 1) * 12288
    if not a.density:
        needed = (size // (128 << 20) + 1) * 12288
    assert shutil.disk_usage(a.out).free > needed + (2 << 30), ('B-space', needed)
    extra = [] if a.density else ['--inodes', '16']
    try:
        run(name + '-format', [a.binary, *extra, str(size), image])
        with image.open('rb') as f:
            sb = read(f, 1024, 1024)
            blocks, bpg, ipg = u32(sb, 4), u32(sb, 32), u32(sb, 40)
            assert blocks == size // 4096, ('B-block-count', blocks, size)
            groups = (blocks + bpg - 1) // bpg
            assert u32(sb, 0) == groups * ipg
            assert u32(sb, 92) & 4 == 0, 'B-no-journal'
            gd = read(f, 4096, groups * 32)
            tables = ipg // 16
            if a.density:
                want = size // ratio
                expected = ((want + groups - 1) // groups + 15) // 16 * 16
                assert ipg == expected, ('B-density', ipg, expected)
            # Check every group's locations, including descriptors beyond
            # the first GDT block and blocks beyond both 32-bit boundaries.
            for g in range(groups):
                bb, ib, it = struct.unpack_from('<III', gd, g * 32)
                end = min((g + 1) * bpg, blocks)
                assert g * bpg <= bb < ib < it < end and it + tables <= end, ('B-group', g)
                if backup(g):
                    copy = read(f, g * bpg * 4096 + (1024 if g == 0 else 0), 1024)
                    assert copy[:90] == sb[:90] and copy[92:] == sb[92:], ('B-backup', g)
                    assert struct.unpack_from('<H', copy, 90)[0] == g & 65535
                    assert read(f, (g * bpg + 1) * 4096, len(gd)) == gd, ('B-backup-gdt', g)
            # The final partial group's padding must be unavailable.
            bm = read(f, u32(gd, (groups - 1) * 32) * 4096, 4096)
            for bit in range(blocks - (groups - 1) * bpg, 32768):
                assert bm[bit // 8] & (1 << (bit % 8)), ('B-partial-padding', bit)
        run(name + '-e2fsck', ['e2fsck', '-fn', image])
        run(name + '-dumpe2fs', ['dumpe2fs', '-h', image])
        print('PASS', name, 'geometry', blocks, groups, ipg, 'allocated_bytes', image.stat().st_blocks * 512, flush=True)
    finally:
        image.unlink(missing_ok=True)
print('BIG DISK: PASS; 0 SKIP', flush=True)
