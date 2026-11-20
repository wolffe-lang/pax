#!/usr/bin/env python3
"""paxext2 --journal (the installer's ext3 root) against mke2fs -t ext3.

  ext3.py PAXEXT2 OUT [RUNNER]

Each row prints `PASS X-<name> …` or `FAIL X-<name> …`; the exit is 1 when
any row failed. The oracles are e2fsprogs' own programs, run as black boxes
through tools/e2fs (its pinned container), or directly when PAX_E2FS_NATIVE=1
(a runner already inside a pinned toolchain image, whose record names it).
"""
import hashlib
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

sys.dont_write_bytecode = True  # no tools/__pycache__ beside the tool it loads (-I ignores the variable)
BIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
RUNNER = [sys.argv[3]] if len(sys.argv) > 3 else []
ROOT = Path(__file__).resolve().parents[2]
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", E2FSPROGS_FAKE_TIME="1700000000", TZ="UTC")
JOURNAL = 4096  # the installer's journal: 16 MiB of 4 KiB blocks
failed = 0


def row(name, ok, why):
    global failed
    print(("PASS " if ok else "FAIL ") + "X-" + name + " " + why, flush=True)
    if not ok:
        failed += 1


def run(args):
    return subprocess.run([str(x) for x in args], capture_output=True)


def paxext2(*args):
    return run([*RUNNER, BIN, *args])


def oracle(name, *args):
    if os.environ.get("PAX_E2FS_NATIVE") == "1":
        return run([name, *args])
    return run([ROOT / "tools/e2fs", OUT, name, *args])


def at(path, off, n):
    with path.open("rb") as f:
        f.seek(off)
        b = f.read(n)
    assert len(b) == n, "short read"
    return b


def inode(path, number):
    sb = at(path, 1024, 1024)
    per_group = struct.unpack_from("<I", sb, 40)[0]
    isize = struct.unpack_from("<H", sb, 88)[0]
    group, index = divmod(number - 1, per_group)
    table = struct.unpack_from("<I", at(path, 4096 + group * 32, 32), 8)[0]
    return at(path, table * 4096 + index * isize, isize)


def journal_super(path):
    first = struct.unpack_from("<I", inode(path, 8), 40)[0]
    return at(path, first * 4096, 1024)


def journal_lines(text):
    keep = ("Journal ", "Total journal", "Max transaction", "Fast commit")
    return [l for l in text.splitlines() if l.startswith(keep) and not l.startswith("Journal UUID")]


def fresh(path, size):
    if path.exists():
        path.unlink()
    with path.open("wb") as f:
        f.truncate(size << 20)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for size in (64, 448, 1024):
    own, ref = OUT / f"own-{size}.img", OUT / f"ref-{size}.img"
    if own.exists():
        own.unlink()
    made = paxext2("--journal", str(JOURNAL), "--label", "pax-root", str(size) + "M", own)
    fresh(ref, size)
    o = oracle("mke2fs", "-q", "-F", "-t", "ext3", "-b", "4096", "-J", "size=16", ref)
    assert o.returncode == 0, o
    if made.returncode != 0:
        row(f"format-{size}", False, f"{size} MiB: paxext2 --journal {JOURNAL} exit {made.returncode}: {made.stderr.decode(errors='replace').strip()}")
        continue
    check = oracle("e2fsck", "-fn", own)
    (OUT / f"own-{size}.fsck").write_bytes(check.stdout + check.stderr)
    sb = at(own, 1024, 1024)
    j = inode(own, 8)
    words = list(struct.unpack_from("<17I", sb, 0x10C))
    size_bytes = JOURNAL * 4096
    want = list(struct.unpack_from("<15I", j, 40)) + [size_bytes >> 32, size_bytes & 0xFFFFFFFF]
    ok = (check.returncode == 0 and b"WARNING" not in check.stdout + check.stderr
          and struct.unpack_from("<I", sb, 92)[0] & 4 and struct.unpack_from("<I", sb, 0xE0)[0] == 8
          and sb[0xFD] == 1 and words == want
          and struct.unpack_from("<H", j, 0)[0] == 0o100600 and struct.unpack_from("<H", j, 26)[0] == 1
          and struct.unpack_from("<I", j, 4)[0] == size_bytes)
    row(f"format-{size}", bool(ok), f"{size} MiB: e2fsck -fn exit {check.returncode}, has_journal, inode 8 a 0600 file of {JOURNAL} blocks, s_jnl_blocks its map")
    a, b = journal_super(own), journal_super(ref)
    fields = [(0, ">III"), (12, ">IIIII"), (32, ">IIII"), (64, ">I")]
    same = all(struct.unpack_from(f, a, o) == struct.unpack_from(f, b, o) for o, f in fields)
    uuid = a[48:64] == sb[104:120]
    ref_uuid = b[48:64] == at(ref, 1024 + 104, 16)
    row(f"journal-super-{size}", same and uuid and ref_uuid,
        f"{size} MiB: the journal superblock's header, geometry, sequence, start, errno, feature words and users are mke2fs -t ext3's; its UUID the volume's (as mke2fs's)")
    da = oracle("dumpe2fs", "-h", own)
    db = oracle("dumpe2fs", "-h", ref)
    (OUT / f"own-{size}.dumpe2fs").write_bytes(da.stdout + da.stderr)
    (OUT / f"ref-{size}.dumpe2fs").write_bytes(db.stdout + db.stderr)
    la, lb = journal_lines(da.stdout.decode()), journal_lines(db.stdout.decode())
    row(f"dumpe2fs-{size}", da.returncode == 0 and la == lb and len(la) > 0,
        f"{size} MiB: dumpe2fs -h's journal lines equal mke2fs -t ext3's ({len(la)} lines)")

# A populated root: the journal changes nothing a tree walk sees.
tree = OUT / "tree"
(tree / "dir").mkdir(parents=True, exist_ok=True)
(tree / "a").write_bytes(b"journalled content\n")
(tree / "dir" / "big").write_bytes(bytes(range(256)) * 20001)
for name, args in (("plain", []), ("journalled", ["--journal", str(JOURNAL)])):
    img = OUT / f"tree-{name}.img"
    if img.exists():
        img.unlink()
    p = paxext2("--from", tree, "--label", "pax-root", *args, "64M", img)
    if p.returncode != 0:
        row("tree", False, f"--from with {args}: exit {p.returncode}")
        break
else:
    if os.environ.get("PAX_E2FS_NATIVE") == "1":
        # tools/e2tree runs debugfs through tools/e2fs; inside a pinned image, directly (verify.py's way).
        from importlib.machinery import SourceFileLoader
        import contextlib
        import io
        wrapper = OUT / "e2fs-local"
        wrapper.write_text('#!/bin/sh\nshift\nexec "$@"\n')
        wrapper.chmod(0o755)
        mod = SourceFileLoader("px162_e2tree", str(ROOT / "tools/e2tree")).load_module()
        mod.E2FS = str(wrapper)

        def tree_of(img):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = mod.main(["e2tree", str(img)])
            return code, out.getvalue().encode()
    else:
        def tree_of(img):
            r = run([ROOT / "tools/e2tree", img])
            return r.returncode, r.stdout
    (ca, ta), (cb, tb) = tree_of(OUT / "tree-plain.img"), tree_of(OUT / "tree-journalled.img")
    (OUT / "tree-plain.txt").write_bytes(ta)
    (OUT / "tree-journalled.txt").write_bytes(tb)
    check = oracle("e2fsck", "-fn", OUT / "tree-journalled.img")
    row("tree", ca == 0 and cb == 0 and ta == tb and len(ta) > 0 and check.returncode == 0,
        "a populated journalled root: e2tree equal to the plain build's, e2fsck -fn clean")
    again = OUT / "tree-again.img"
    if again.exists():
        again.unlink()
    p = paxext2("--from", tree, "--label", "pax-root", "--journal", str(JOURNAL), "64M", again)
    row("reproducible", p.returncode == 0 and sha(again) == sha(OUT / "tree-journalled.img"),
        "the same inputs give the same bytes, journal included")

# Refusals: a journal below 1024 blocks, of no blocks, or over a quarter of
# the volume leaves an existing image unchanged.
victim = OUT / "tree-journalled.img"
if victim.exists():
    before = sha(victim)
    bad = []
    for args in (["--journal", "1000", "64M"], ["--journal", "0", "64M"], ["--journal", "8192", "64M"]):
        p = paxext2(*args, victim)
        if p.returncode != 1 or b"wolf-trap" in p.stderr or sha(victim) != before:
            bad.append(" ".join(args))
    row("refusals", not bad, "too small, empty and over-a-quarter journals refused, the image unchanged" + (": " + ", ".join(bad) if bad else ""))
else:
    row("refusals", False, "no journalled image to guard")
print(f"EXT3: {'FAIL' if failed else 'PASS'} ({failed} failed)", flush=True)
sys.exit(1 if failed else 0)
