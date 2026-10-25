#!/usr/bin/env python3
"""paxext2 vs tools/mkdisk --from and tools/e2tree, using real e2fsprogs.
Runs on the Linux container-engine host. Optional argv[3] is an executable
runner which receives BINARY ARG... (the lane uses its Ubuntu container).
"""
import hashlib
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

BIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
RUNNER = [sys.argv[3]] if len(sys.argv) > 3 else []
ROOT = Path(__file__).resolve().parents[2]
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", E2FSPROGS_FAKE_TIME="1700000000", TZ="UTC")
rows = 0


def run(args, ok=True):
    p = subprocess.run([str(x) for x in args], capture_output=True)
    if ok:
        assert p.returncode == 0, (args, p.returncode, p.stdout, p.stderr)
    else:
        assert p.returncode == 1, (args, p.returncode, p.stdout, p.stderr)
        assert b"wolf-trap" not in p.stderr
    return p


def wolf(*args, ok=True):
    return run([*RUNNER, BIN, *args], ok)


def oracle(name, *args, ok=True):
    return run([ROOT / "tools/e2fs", OUT, name, *args], ok)


def passed(name):
    global rows
    rows += 1
    print("PASS E%d %s" % (rows, name), flush=True)


def fsck(image):
    try:
        p = oracle("e2fsck", "-fn", image)
    except AssertionError as e:
        raise AssertionError("E-e2fsck: " + str(e)) from e
    assert b"WARNING" not in p.stdout + p.stderr, p.stdout + p.stderr
    return p


def superblock(image):
    with image.open("rb") as f:
        f.seek(1024)
        return f.read(1024)


own, ref = OUT / "wolf.img", OUT / "oracle.img"
for size in [8, 16, 32, 64, 128, 448, 512, 1024]:
    for f in [own, ref]:
        if f.exists(): f.unlink()
    wolf("--label", "px69", str(size) + "M", own)
    with ref.open("wb") as f:
        f.truncate(size << 20)
    oracle("mkfs.ext2", "-q", "-F", "-b", "4096", ref)
    fsck(own)
    a, b = superblock(own), superblock(ref)
    for at, width in [(0, 4), (4, 4), (8, 4), (24, 4), (32, 4), (40, 4), (88, 2)]:
        assert a[at:at + width] == b[at:at + width], (size, at, a.hex(), b.hex())
    assert struct.unpack_from("<I", a, 92)[0] & 4 == 0
    passed("%d MiB: default inode count/reserved blocks/group geometry, fsck, no journal" % size)

# A source tree with every requested metadata class and both indirect levels.
tree = OUT / "tree"
tree.mkdir(exist_ok=True)
(tree / "dir").mkdir(exist_ok=True)
(tree / "empty-dir").mkdir(exist_ok=True)
(tree / "dir" / "child").mkdir(exist_ok=True)
(tree / "a").write_bytes(b"linked content\0\xff")
if not (tree / "z-hard").exists(): os.link(tree / "a", tree / "z-hard")
(tree / "empty").write_bytes(b"")
(tree / "block-boundary").write_bytes(bytes(range(256)) * 16)
(tree / "double-indirect").write_bytes(bytes(range(256)) * 20001)
with (tree / "sparse").open("wb") as f:
    f.write(b"first")
    f.seek(5 << 20)
    f.write(b"last")
for length in [1, 59, 60, 61, 255]:
    link = tree / ("symlink%d" % length)
    if link.is_symlink(): link.unlink()
    os.symlink("x" * length, link)
for i in range(400):
    (tree / "dir" / ("entry-%03d-name" % i)).write_bytes(b"row" + str(i).encode())
(tree / "space name").write_text("space-name metadata\n")
attrs = OUT / "attrs"
attrs.write_text('/ 755 0 0 0\n/a 6751 70000 80000 2200000000 2200000001 2200000002\n/dir 2770 1000 1001 1700000100\n"/space name" 640 1000 1000 0\n/symlink61 777 70000 80000 2200000000\n')
for f in [own, ref]: f.unlink()
wolf("--from", tree, "--attrs", attrs, "--label", "px69", "64M", own)
run([ROOT / "tools/mkdisk", "--from", tree, "--attrs", attrs, "--label", "px69", "64M", ref])
fsck(own)
a = run([ROOT / "tools/e2tree", own]).stdout
b = run([ROOT / "tools/e2tree", ref]).stdout
(OUT / "wolf.tree").write_bytes(a)
(OUT / "oracle.tree").write_bytes(b)
if a != b:
    import difflib
    raise AssertionError("".join(difflib.unified_diff(b.decode().splitlines(True), a.decode().splitlines(True))))
passed("exact e2tree vs mkdisk --from: 400-entry directory, metadata, high ids/future times, links, sparse/direct/single/double maps")

# Seed UUID and directory hash seed match the reference builder.
a, b = superblock(own), superblock(ref)
assert a[104:120] == b[104:120]
assert a[236:252] == b[236:252]
passed("seeded UUID and directory hash seed agree with mkdisk")

# Identical inputs reproduce every byte, not just the visible tree.
second = OUT / "second.img"
if second.exists(): second.unlink()
wolf("--from", tree, "--attrs", attrs, "--label", "px69", "64M", second)
assert hashlib.sha256(second.read_bytes()).digest() == hashlib.sha256(own.read_bytes()).digest()
second.unlink()
passed("repeated format/population is byte-identical")

before = hashlib.sha256(own.read_bytes()).digest()
for args in [["1M", own], ["--inodes", "1", "64M", own], ["--label", "x" * 17, "64M", own], ["--from", tree, "--inodes", "16", "64M", own]]:
    wolf(*args, ok=False)
    assert hashlib.sha256(own.read_bytes()).digest() == before
passed("invalid geometry and insufficient inode budget leave an existing image unchanged")

# Last directory record must reach the block boundary: independent plant.
bad = OUT / "directory-bad.img"
blob = bytearray(own.read_bytes())
ipg = struct.unpack_from("<I", blob, 1024 + 40)[0]
it = struct.unpack_from("<I", blob, 4096 + 8)[0]
root = it * 4096 + 256  # inode 2
block = struct.unpack_from("<I", blob, root + 40)[0]
o = block * 4096
end = o + 4096
while True:
    n = struct.unpack_from("<H", blob, o + 4)[0]
    assert n >= 8 and o + n <= end
    if o + n == end:
        struct.pack_into("<H", blob, o + 4, n - 4)
        break
    o += n
bad.write_bytes(blob)
p = subprocess.run([str(ROOT / "tools/e2fs"), str(OUT), "e2fsck", "-fn", str(bad)], capture_output=True)
assert p.returncode != 0, (p.stdout, p.stderr)
assert b"directory" in (p.stdout + p.stderr).lower(), (p.stdout, p.stderr)
(OUT / "directory-short.red").write_bytes(p.stdout + p.stderr)
passed("e2fsck rejects a short final directory record (red control)")
print("EXT2: %d PASS, 0 SKIP" % rows)
