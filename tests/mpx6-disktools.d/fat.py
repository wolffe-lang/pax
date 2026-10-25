#!/usr/bin/env python3
"""FAT32 differential: pinned dosfstools/mtools, no implementation source."""
import hashlib
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

BIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
ORACLE = Path(sys.argv[3]) if len(sys.argv) > 3 else None
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", TZ="UTC", LC_ALL="C.UTF-8", PAX_DISKTOOLS_LOCALE="C.UTF-8")
rows = 0


def run(args, ok=True):
    p = subprocess.run([str(x) for x in args], capture_output=True)
    if ok:
        assert p.returncode == 0, (args, p.returncode, p.stdout, p.stderr)
    else:
        assert p.returncode == 1, (args, p.returncode, p.stdout, p.stderr)
        assert b"wolf-trap" not in p.stderr
    return p


def oracle(name, *args):
    return run([ORACLE / name if ORACLE else name, *args])


def passed(name):
    global rows
    rows += 1
    print("PASS F%d %s" % (rows, name), flush=True)


def fsck(image):
    p = oracle("fsck.fat", "-n", image)
    lines = (p.stdout + p.stderr).decode().splitlines()
    assert len(lines) == 2, ("F-fsck-fat", lines)
    assert lines[0].startswith("fsck.fat "), lines
    assert re.fullmatch(re.escape(str(image)) + r": \d+ files, \d+/\d+ clusters", lines[1]), lines


def listing(image):
    p = oracle("mdir", "-/", "-i", image, "::/")
    return p.stdout


def serial(seed):
    return hashlib.sha256(("pax-esp:%s:1700000000" % seed).encode()).hexdigest()[:8]


ref, own = OUT / "oracle.img", OUT / "wolf.img"
for size in [33, 64, 192]:
    run([BIN, "--seed", "px69", "mkfs", own, str(size) + "M"])
    with ref.open("wb") as f:
        f.truncate(size << 20)
    oracle("mkfs.fat", "-F", "32", "-s", "1", "--invariant", "-i", serial("px69"), "-n", "PAX-ESP", ref)
    # The boot code/OEM id is deliberately independent. Hold the layout.
    a, b = own.read_bytes()[:90], ref.read_bytes()[:90]
    for off, width in [(11, 6), (17, 7), (28, 40), (71, 19)]:
        assert a[off:off + width] == b[off:off + width], (size, off, a.hex(), b.hex())
    fsck(own)
    assert listing(own) == listing(ref)
    passed("%d MiB geometry, empty listing, FSInfo, fsck" % size)

# The 64 MiB ESP, the same insertion order as tools/mkdisk.
run([BIN, "--seed", "px69", "mkfs", own, "64M"])
with ref.open("wb") as f:
    f.truncate(64 << 20)
oracle("mkfs.fat", "-F", "32", "--invariant", "-i", serial("px69"), "-n", "PAX-ESP", ref)
for directory in ["/EFI", "/EFI/BOOT", "/boot", "/boot/limine"]:
    run([BIN, "mkdir", own, directory])
    oracle("mmd", "-i", ref, "::" + directory)
files = [
    ("/EFI/BOOT/BOOTX64.EFI", b"EFI fixture\0\xff" * 1031),
    ("/boot/limine/limine.conf", b"timeout: 0\n/PAX\n protocol: limine\n"),
    ("/boot/limine/limine-bios.sys", bytes(range(256)) * 90),
    ("/boot/pax", bytes(range(256)) * 17001),
    ("/boot/initramfs.cpio", b"070701" + b"archive fixture" * 1111),
]
for n, (name, data) in enumerate(files):
    src = OUT / ("f%d" % n)
    src.write_bytes(data)
    os.utime(src, (1700000000, 1700000000))
    run([BIN, "copy", own, src, name])
    oracle("mcopy", "-m", "-i", ref, src, "::" + name)
    fsck(own)
    assert oracle("mtype", "-i", own, "::" + name).stdout == data
    assert run([BIN, "cat", ref, name]).stdout == data
    assert run([BIN, "cat", own, name]).stdout == data
assert listing(own) == listing(ref), (listing(own), listing(ref))
fsck(own)
passed("ESP tree: exact mdir recursive listing and all file bytes both directions")

# Exercise directory expansion, alias collision, empty files and LFN boundaries.
source = OUT / "small"
source.write_bytes(b"\0\xfftest\n")
os.utime(source, (1700000000, 1700000000))
for i, name in enumerate(["Long File Name.txt", "Long File Names.txt", "Mixed.TXT", "snake_case.long", "a" * 13, "b" * 26, "root-π-狼.txt", "é.txt"] + ["collision long name %02d.txt" % i for i in range(23)]):
    dest = "/boot/limine/" + name
    run([BIN, "copy", own, source, dest])
    oracle("mcopy", "-m", "-i", ref, source, "::" + dest)
    assert oracle("mtype", "-i", own, "::" + dest).stdout == source.read_bytes()
assert listing(own) == listing(ref), (listing(own), listing(ref))
fsck(own)
assert run([BIN, "ls", own, "/boot/limine"]).stdout == run([BIN, "ls", ref, "/boot/limine"]).stdout
passed("LFN boundaries, BMP Unicode, aliases through ~23, directory-chain growth")

source.write_bytes(b"")
os.utime(source, (1700000000, 1700000000))
run([BIN, "copy", own, source, "/empty"])
oracle("mcopy", "-m", "-i", ref, source, "::/empty")
assert run([BIN, "cat", own, "/empty"]).stdout == b""
assert listing(own) == listing(ref)
fsck(own)
passed("empty file has zero clusters and readable zero bytes")

before = hashlib.sha256(own.read_bytes()).digest()
for args in [["mkdir", own, "/boot"], ["mkdir", own, "/missing/sub"], ["mkdir", own, "/../bad"], ["copy", own, source, "/bad?name"], ["copy", own, source, "/boot/PAX"], ["mkfs", own, "32M"], ["mkfs", own, "64M", "bad/name"]]:
    run([BIN, *args], ok=False)
    assert hashlib.sha256(own.read_bytes()).digest() == before
passed("invalid names, duplicate names, absent parent and geometry refuse without changes")

# Offset into a larger disk: only the designated partition may change.
disk = OUT / "offset.img"
with disk.open("wb") as f:
    f.truncate(68 << 20)
    f.write(b"PREFIX")
    f.seek((67 << 20)); f.write(b"SUFFIX")
run([BIN, "--offset", "2M", "mkfs", disk, "64M"])
run([BIN, "--offset", "2M", "mkdir", disk, "/EFI"])
with disk.open("rb") as f:
    assert f.read(6) == b"PREFIX"
    f.seek(67 << 20); assert f.read(6) == b"SUFFIX"
    f.seek(2 << 20); image = f.read(64 << 20)
(OUT / "partition.img").write_bytes(image)
fsck(OUT / "partition.img")
passed("offset partition formatting and directory write preserve bytes outside window")

# R-px69-4: Microsoft FAT §7 stores UTF-16, including surrogate pairs.
# mtools 4.0.49 instead truncates U+1F600 to U+F600: preserve the defect
# as a named oracle observation, never as the formatter's expected answer.
nonbmp = OUT / "nonbmp.img"
run([BIN, "mkfs", nonbmp, "64M"])
source.write_bytes(b"non-BMP witness")
os.utime(source, (1700000000, 1700000000))
run([BIN, "copy", nonbmp, source, "/emoji-😀.txt"])
assert "emoji-😀.txt".encode() in run([BIN, "ls", nonbmp]).stdout
assert run([BIN, "cat", nonbmp, "/emoji-😀.txt"]).stdout == source.read_bytes()
b = nonbmp.read_bytes()
start = (32 + 2 * struct.unpack_from("<I", b, 36)[0]) * 512
assert "😀".encode("utf-16le") in b[start:start + 512]
fsck(nonbmp)
other = OUT / "mtools-nonbmp.img"
with other.open("wb") as f:
    f.truncate(64 << 20)
oracle("mkfs.fat", "-F32", "--invariant", other)
oracle("mcopy", "-m", "-i", other, source, "::/emoji-😀.txt")
listing_bad = run([BIN, "ls", other]).stdout
assert "emoji-\uf600.txt".encode() in listing_bad, listing_bad
(OUT / "nonbmp-oracle-defect.txt").write_bytes(listing_bad)
passed("R-px69-4: correct surrogate pair; pinned mtools truncation named independently")

# Both long and short spellings address the same content.
assert run([BIN, "cat", own, "/boot/limine/LIMINE~1.SYS"]).stdout == files[2][1]
run([BIN, "copy", own, own, "/self.img"], ok=False)
passed("8.3 alias lookup; self-copy refused before writes")

# More file clusters than are free: leave all metadata and payload untouched.
small = OUT / "full.img"
run([BIN, "mkfs", small, "33M"])
large = OUT / "too-large"
with large.open("wb") as f:
    f.truncate(33 << 20)
before = hashlib.sha256(small.read_bytes()).digest()
p = run([BIN, "copy", small, large, "/too-large"], ok=False)
assert b"full" in p.stderr
assert hashlib.sha256(small.read_bytes()).digest() == before
fsck(small)
passed("ENOSPC preflight leaves the image byte-identical")

# The LFN checksum plant: discover a real LFN via an independent sector walk.
b = bytearray(own.read_bytes())
fats = struct.unpack_from("<I", b, 36)[0]
start = (32 + 2 * fats) * 512
planted = False
for off in range(start, len(b), 32):
    if b[off] & 0x40 and b[off + 11] == 15 and b[off + 12] == 0:
        b[off + 13] = (b[off + 13] + 1) & 255
        planted = True
        break
assert planted
bad = OUT / "lfn-bad.img"
bad.write_bytes(b)
p = subprocess.run([str(ORACLE / "fsck.fat") if ORACLE else "fsck.fat", "-n", str(bad)], capture_output=True)
assert b"wrong" in (p.stdout + p.stderr).lower(), (p.stdout, p.stderr)
assert b"Not auto-correcting" in p.stdout + p.stderr, (p.stdout, p.stderr)
assert b"checksum" in (p.stdout + p.stderr).lower(), (p.stdout, p.stderr)
(OUT / "lfn-checksum.red").write_bytes(p.stdout + p.stderr)
passed("fsck.fat detects off-by-one LFN checksum (red control)")
print("FAT: %d PASS, 0 SKIP" % rows)
