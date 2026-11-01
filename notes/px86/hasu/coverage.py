#!/usr/bin/env python3
"""px86, R-px86-1's measurement: which bytes of a used disk each PAX formatter leaves as it found them.

    coverage.py DISKTOOLS_BIN WORK

A sparse 64 GiB image (the regions' places do not depend on the size: the root's last MiB is data blocks at any) is filled with a pattern in the ranges that matter (the first 72 MiB and the
last 4 MiB), then PAX's own formatters run on it alone, as the executor runs them (paxgpt with the executor's
partitions, paxfat mkfs at the ESP, paxext2 of an empty tree at the root; no zero phase): every 512-byte sector of
those ranges still holding its pattern is counted, by region. Prints one line a region.
"""
from pathlib import Path
import hashlib
import os
import subprocess
import sys

bin_, work = Path(sys.argv[1]), Path(sys.argv[2])
work.mkdir(parents=True, exist_ok=True)
MIB = 1 << 20
N = 68719476736
img = work/'coverage.img'
end = (N - 33 * 512) // 4096 * 4096
root_start, root_bytes = 69206016, min(end - 69206016, 17592186040320)
root_end = root_start + root_bytes
regions = {
    'gpt primary [0,17408)': (0, 17408),
    'gap [17408,65536)': (17408, 65536),
    'log [65536,131072)': (65536, 131072),
    'gap [131072,1048576)': (131072, MIB),
    'partition 3 [1 MiB,2 MiB)': (MIB, 2 * MIB),
    'esp first MiB': (2 * MIB, 3 * MIB),
    'esp last MiB': (65 * MIB, 66 * MIB),
    'root first MiB': (root_start, root_start + MIB),
    'root last MiB': (root_end - MIB, root_end),
    'tail slack before the backup': (end, N - 33 * 512),
    'backup table': (N - 33 * 512, N),
}
pat = lambda at, n: hashlib.shake_256(b'used %d' % at).digest(n)
CACHE = {}
def chunk(blk):
    if blk not in CACHE:
        CACHE[blk] = pat(blk, MIB)
    return CACHE[blk]
with open(img, 'wb') as f:
    f.truncate(N)
    for a, b in [(0, 72 * MIB), (N - 4 * MIB, N)]:
        for at in range(a, b, MIB):
            f.seek(at)
            f.write(pat(at, min(MIB, b - at)))
env = dict(os.environ, SOURCE_DATE_EPOCH='1700000000')
last = root_end // 512 - 1
tree = work/'tree'
tree.mkdir(exist_ok=True)
cmds = [[bin_/'paxgpt', '--seed', 'cov', img, '1:esp:4096:135167:esp', f'2:linux:135168:{last}:root', '3:bios:2048:4095:bios'],
        [bin_/'paxfat', '--offset', '2097152', '--seed', 'cov', 'mkfs', img, '67108864']]
for c in cmds:
    p = subprocess.run([str(x) for x in c], capture_output=True, env=env)
    print(f'{c[0].name} exit {p.returncode} {p.stderr.decode()[-300:].strip()}', flush=True)
    if p.returncode != 0:
        sys.exit(1)
# paxext2 of an empty tree (no --attrs: its defaults), as the executor's root phase runs it otherwise.
ext = [str(bin_/'paxext2'), '--from', str(tree), '--label', 'pax-root', '--seed', 'cov', '--offset', str(root_start), str(root_bytes), str(img)]
p = subprocess.run(ext, capture_output=True, env=env)
print(f'paxext2 exit {p.returncode} {p.stderr.decode()[-300:].strip()}', flush=True)
with open(img, 'rb') as f:
    for name, (a, b) in regions.items():
        kept = 0
        for s in range(a, b, 512):
            n = min(512, b - s)
            blk = (s // MIB) * MIB
            f.seek(s)
            got = f.read(n)
            if got == chunk(blk)[s - blk:s - blk + n]:
                kept += n
        print(f'{name}: {kept} of {b - a} bytes still the old disk\'s', flush=True)
img.unlink()
