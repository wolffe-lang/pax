#!/usr/bin/env python3
"""Black-box GPT rows: independent tools plus malformed-input refusal.
Run inside a Linux container: gpt.py PAXGPT OUTDIR [ORACLE_BIN_DIR].
The malformed fixtures are generated, not edited golden recordings.
"""
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import zlib

BIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
ORACLE = Path(sys.argv[3]) if len(sys.argv) > 3 else None
ROOT = Path(__file__).resolve().parents[2]
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", LC_ALL="C.UTF-8")
rows = 0


def run(argv, ok=True):
    p = subprocess.run([str(x) for x in argv], capture_output=True)
    if ok:
        assert p.returncode == 0, (argv, p.returncode, p.stdout, p.stderr)
    else:
        assert p.returncode == 1, (argv, p.returncode, p.stdout, p.stderr)
        assert b"wolf-trap" not in p.stderr, p.stderr
    return p


def oracle(name, *args):
    return run([ORACLE / name if ORACLE else name, *args])


def passed(name):
    global rows
    rows += 1
    print("PASS G%d %s" % (rows, name), flush=True)


def layout(size, esp, home=0, root=True):
    end = size * 2048 - 34
    lo = (esp + 2) * 2048
    hi = ((end + 1) // 8) * 8 - 1
    parts = [(1, "esp", 4096, lo - 1, "esp"),
             (2, "linux", lo, hi, "root" if root else "home"),
             (3, "bios", 2048, 4095, "bios")]
    if home:
        start = ((end + 1 - home * 2048) // 2048) * 2048
        parts[1] = (2, "linux", lo, start - 1, "root")
        parts.append((4, "linux", start, start + home * 2048 - 1, "home"))
    return [":".join(map(str, p)) for p in parts]


def metadata(path):
    with path.open("rb") as f:
        front = f.read(34 * 512)
        f.seek(-33 * 512, 2)
        return front + f.read()


def verify(path):
    own = run([BIN, "--dump", path]).stdout
    ref = oracle("sfdisk", "--dump", path).stdout
    assert own == ref, (own, ref)
    v = oracle("sgdisk", "-v", path)
    assert b"No problems found" in v.stdout + v.stderr, v.stdout + v.stderr
    assert b"Warning!" not in v.stdout + v.stderr, v.stdout + v.stderr


for n, (size, esp, home, root) in enumerate([
        (64, 33, 0, False), (128, 64, 0, False), (128, 64, 16, True),
        (512, 64, 0, True), (512, 192, 0, False), (512, 192, 32, True)]):
    image, ref = OUT / ("layout%d.img" % n), OUT / "reference.img"
    parts = layout(size, esp, home, root)
    run([BIN, "--seed", "px69", "--size", str(size) + "M", image, *parts])
    run([ROOT / "tools/mkgpt", "--label", "px69", "--size", str(size) + "M", ref, *parts])
    assert metadata(image) == metadata(ref)
    verify(image)
    before = metadata(image)
    # No --size: write into the existing image, preserving all payload bytes.
    with image.open("r+b") as f:
        f.seek(16 * 1024 * 1024)
        f.write(b"px69 payload, not GPT")
    run([BIN, "--seed", "px69", image, *parts])
    assert metadata(image) == before
    with image.open("rb") as f:
        f.seek(16 * 1024 * 1024)
        assert f.read(21) == b"px69 payload, not GPT"
    passed("mkdisk layout size=%dM esp=%dM home=%dM root=%s, exact bytes/dump/payload" % (size, esp, home, root))
    if n != 0:
        image.unlink()
    ref.unlink()

image = OUT / "external9"
with image.open("wb") as f:
    f.truncate(64 << 20)
# sgdisk's own writer, not PAX's encoder. Non-ASCII uses a surrogate pair.
oracle("sgdisk", "--clear", "--new=1:2048:65535", "--typecode=1:EF00", "--change-name=1:root-π-狼-😀", image)
verify(image)
passed("read sgdisk's GPT, Unicode including UTF-16 pair, digit-ending device name")
image.unlink()

image = OUT / "names.img"
for name in ["", "a" * 36, 'with space:colon', 'quote"slash\\tab\t', 'π狼😀']:
    run([BIN, "--size", "64M", image, "1:linux:2048:65535:" + name])
    verify(image)
passed("empty, full-width, punctuation and Unicode partition names")

original = metadata(image)
for extra in [
    ["1:linux:2048:65535:a", "1:esp:67584:100000:b"],
    ["1:linux:2048:65535:a", "2:esp:4096:100000:b"],
    ["129:linux:2048:65535:a"], ["0:linux:2048:65535:a"],
    ["1:linux:2049:65535:a"], ["1:linux:2048:131071:a"],
    ["1:linux:65536:2048:a"], ["1:no-guid:2048:65535:a"],
    ["1:00000000-0000-0000-0000-000000000000:2048:65535:a"],
    ["1:linux:2048:65535:" + "a" * 37], ["1:linux:2048:65535:" + "😀" * 19],
]:
    run([BIN, "--size", "64M", image, *extra], ok=False)
    assert metadata(image) == original
passed("invalid/overlapping/duplicate/out-of-range input rejected before writing")

for size in ["-1", "513", "1024", "9223372036854775807G", "bad", "0"]:
    run([BIN, "--size", size, image], ok=False)
    assert metadata(image) == original
passed("invalid sizes leave an existing image untouched")

# Independent mutations of both headers/arrays. With refreshed CRCs where
# needed, the row proves range/format validation, not only a CRC rejection.
base = image.read_bytes()
for name, off, value, fix in [
    ("primary-crc", 512 + 56, 1, False),
    ("backup-crc", len(base) - 512 + 56, 1, False),
    ("primary-array-crc", 1024 + 56, 1, False),
    ("backup-array-crc", len(base) - 33 * 512 + 56, 1, False),
    ("header-short", 512 + 12, 91, True),
    ("header-long", 512 + 13, 3, True),
    ("self-lba", 512 + 24, 2, True),
    ("alt-lba", 512 + 32, 2, True),
    ("reserved", 512 + 20, 1, True),
    ("array-overflow", 512 + 79, 255, True),
    ("last-overflow", 512 + 55, 255, True),
    ("entry-count", 512 + 80, 127, True),
    ("entry-width", 512 + 84, 64, True),
    ("mbr-signature", 510, 0, False),
]:
    b = bytearray(base)
    b[off] = value if fix or name == "mbr-signature" else b[off] ^ value
    if fix:
        struct.pack_into("<I", b, 512 + 16, 0)
        n = struct.unpack_from("<I", b, 512 + 12)[0]
        struct.pack_into("<I", b, 512 + 16, zlib.crc32(b[512:512 + n]))
    image.write_bytes(b)
    p = run([BIN, "--dump", image], ok=False)
    assert not p.stdout, p.stdout
    if name == "backup-crc":
        verdict = oracle("sgdisk", "-v", image)
        assert b"Warning!" in verdict.stdout + verdict.stderr
        assert b"Backup header: ERROR" in verdict.stdout + verdict.stderr
        assert b"CRC" in verdict.stdout + verdict.stderr
        (OUT / "backup-crc.red").write_bytes(verdict.stdout + verdict.stderr)
    passed("reject " + name + " without a partial dump")
image.unlink()
(OUT / "result").write_text("GPT: %d PASS, 0 SKIP\n" % rows)
print("GPT: %d PASS, 0 SKIP" % rows)
