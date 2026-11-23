#!/usr/bin/env python3
"""paxext2 --extents (X3's ext4: ext3's features and `extent`) against mke2fs -t ext4.

  ext4.py PAXEXT2 OUT [RUNNER]

Each row prints `PASS E4-<name> …` or `FAIL E4-<name> …`; the exit is 1 when
any row failed. The oracles are e2fsprogs' own programs, run as black boxes
through tools/e2fs (its pinned container), or directly when PAX_E2FS_NATIVE=1,
and Linux's own ext4 driver in a QEMU guest (tools/linux-blk --type ext4), or
its record (ext4-linux.record) where no Linux kernel is readable, said loudly,
as tests/mpx6-ext2 does. The extent trees are read here from the documented
layout (Documentation/filesystems/ext4/ifork.rst), never from a tool's source.

The oracle image is `mke2fs -t ext4` with every default feature outside the
profile turned off: the -O string is derived at run time from mke2fs's own
defaults (dumpe2fs -h), so a different default set cannot pass unseen.
"""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
BIN = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
RUNNER = [sys.argv[3]] if len(sys.argv) > 3 else []
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", E2FSPROGS_FAKE_TIME="1700000000", TZ="UTC")
JOURNAL = 4096
PROFILE = {"extent", "filetype", "has_journal", "large_file", "sparse_super"}
EXTENTS_FL = 0x80000
failed = 0


def row(name, ok, why):
    global failed
    print(("PASS " if ok else "FAIL ") + "E4-" + name + " " + why, flush=True)
    if not ok:
        failed += 1


def run(args, **kw):
    return subprocess.run([str(x) for x in args], capture_output=True, **kw)


def paxext2(*args):
    return run([*RUNNER, BIN, *args])


def oracle(name, *args):
    if os.environ.get("PAX_E2FS_NATIVE") == "1":
        return run([name, *args])
    return run([ROOT / "tools/e2fs", OUT, name, *args])


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fresh(path, mib):
    if path.exists():
        path.unlink()
    with path.open("wb") as f:
        f.truncate(mib << 20)


class Image:
    """An ext2-family image read from the documented layout (super.rst, inodes.rst, ifork.rst)."""

    def __init__(self, path):
        self.f = Path(path).open("rb")
        self.sb = self.at(1024, 1024)
        self.ipg = struct.unpack_from("<I", self.sb, 40)[0]
        self.isize = struct.unpack_from("<H", self.sb, 88)[0]
        self.blocks = struct.unpack_from("<I", self.sb, 4)[0]

    def at(self, off, n):
        self.f.seek(off)
        b = self.f.read(n)
        assert len(b) == n, "short read"
        return b

    def block(self, n):
        return self.at(n * 4096, 4096)

    def words(self, at, fmt):
        return struct.unpack_from(fmt, self.sb, at)

    def inode(self, number):
        group, index = divmod(number - 1, self.ipg)
        table = struct.unpack_from("<I", self.at(4096 + group * 32, 32), 8)[0]
        return self.at(table * 4096 + index * self.isize, self.isize)

    def tree(self, raw):
        """(depth, [(logical, length, physical, uninit)], tree blocks) of an extent root, or None if not one."""
        out, nodes = [], []

        def node(b, want):
            magic, entries, mx, depth = struct.unpack_from("<HHHH", b, 0)
            if magic != 0xF30A or entries > mx or depth > 5 or (want is not None and depth != want):
                raise ValueError("bad extent node")
            for e in range(entries):
                o = 12 + 12 * e
                if depth == 0:
                    lblk, ln, hi, lo = struct.unpack_from("<IHHI", b, o)
                    out.append((lblk, ln - 32768 if ln > 32768 else ln, (hi << 32) | lo, ln > 32768))
                else:
                    _l, lo, hi = struct.unpack_from("<IIH", b, o)
                    child = (hi << 32) | lo
                    if child in nodes:
                        raise ValueError("extent node named twice")
                    nodes.append(child)
                    node(self.block(child), depth - 1)
            return depth
        depth = node(raw[40:100], None)
        return depth, out, nodes


def features(path):
    d = oracle("dumpe2fs", "-h", path)
    for line in d.stdout.decode(errors="replace").splitlines():
        if line.startswith("Filesystem features:"):
            return set(line.split(":", 1)[1].split())
    return set()


def journal_lines(path):
    d = oracle("dumpe2fs", "-h", path)
    keep = ("Journal ", "Total journal", "Max transaction", "Fast commit")
    return [l for l in d.stdout.decode(errors="replace").splitlines() if l.startswith(keep) and not l.startswith("Journal UUID")]


def profile_o(mib):
    """mke2fs -t ext4's -O string for the profile at this size: its defaults outside PROFILE turned off."""
    probe = OUT / f"defaults-{mib}.img"
    fresh(probe, mib)
    o = oracle("mke2fs", "-q", "-F", "-t", "ext4", "-b", "4096", probe)
    assert o.returncode == 0, o
    have = features(probe)
    probe.unlink()
    return ",".join(sorted("^" + f for f in have - PROFILE) + sorted(PROFILE - have))


def fsck_clean(path):
    c = oracle("e2fsck", "-fn", path)
    return c.returncode == 0 and b"WARNING" not in c.stdout + c.stderr, c.returncode


def shape(t):
    depth, ext, nodes = t
    return depth, [(l, n) for (l, n, _p, _u) in ext], len(nodes)


# --- the format rows: paxext2's empty ext4 against mke2fs's, at three sizes and without a journal
for mib, journalled in ((64, True), (448, True), (1024, True), (64, False)):
    name = f"format-{mib}" if journalled else f"plain-{mib}"
    own, ref = OUT / f"own-{name}.img", OUT / f"ref-{name}.img"
    if own.exists():
        own.unlink()
    args = (["--journal", str(JOURNAL)] if journalled else []) + ["--extents", "--label", "pax-root", f"{mib}M", own]
    made = paxext2(*args)
    if made.returncode != 0:
        row(name, False, f"{mib} MiB: paxext2 {' '.join(map(str, args[:-1]))} exit {made.returncode}: {made.stderr.decode(errors='replace').strip()}")
        continue
    opts = profile_o(mib) if journalled else profile_o(mib) + ",^has_journal"
    fresh(ref, mib)
    o = oracle("mke2fs", "-q", "-F", "-t", "ext4", "-O", opts, "-b", "4096", "-I", "256", *(["-J", "size=16"] if journalled else []), ref)
    assert o.returncode == 0, o
    clean, rc = fsck_clean(own)
    want = PROFILE if journalled else PROFILE - {"has_journal"}
    fa, fb = features(own), features(ref)
    a, b = Image(own), Image(ref)
    words = a.words(92, "<III") == b.words(92, "<III")
    why = [f"e2fsck -fn exit {rc}"] if not clean else []
    if fa != want or fb != want:
        why.append(f"features {sorted(fa)} (mke2fs's {sorted(fb)}, want {sorted(want)})")
    if not words:
        why.append(f"feature words {a.words(92, '<III')} against mke2fs's {b.words(92, '<III')}")
    if journalled:
        ia, ib = a.inode(8), b.inode(8)
        try:
            sa, sb = shape(a.tree(ia)), shape(b.tree(ib))
        except ValueError as e:
            sa, sb = str(e), "-"
        flags = struct.unpack_from("<I", ia, 32)[0] & EXTENTS_FL
        jnl = list(a.words(0x10C, "<17I"))
        mapped = jnl[:15] == list(struct.unpack_from("<15I", ia, 40)) and a.sb[0xFD] == b.sb[0xFD] == 1
        if not flags or sa != sb:
            why.append(f"inode 8: EXTENTS_FL {bool(flags)}, tree {sa} against mke2fs's {sb}")
        if not mapped:
            why.append("s_jnl_blocks is not inode 8's i_block and size")
        la, lb = journal_lines(own), journal_lines(ref)
        if la != lb or not la:
            why.append(f"dumpe2fs journal lines differ ({len(la)} against {len(lb)})")
    row(name, not why, f"{mib} MiB{'' if journalled else ', no journal'}: against mke2fs -t ext4 -O {opts}" + (": " + "; ".join(why) if why else ": e2fsck clean, features, words" + (", inode 8's tree, s_jnl_blocks and the journal lines equal" if journalled else " equal")))

# --- a populated root
tree = OUT / "tree"
if tree.exists():
    shutil.rmtree(tree)
(tree / "dir").mkdir(parents=True)
(tree / "wide").mkdir()
(tree / "a").write_bytes(b"extent content\n")
(tree / "empty").write_bytes(b"")
(tree / "dir" / "big").write_bytes(bytes(range(256)) * 16 * 1280)  # 5 MiB, one run
(tree / "cross").write_bytes(bytes(range(256)) * 16 * 33280)  # past one extent's 32768 blocks, across a group
block = bytes(range(1, 256)) * 16 + b"\x01" * 16


def sparse(path, runs):
    with path.open("wb") as f:
        for k in range(runs):
            f.write(block)
            if k + 1 < runs:
                f.write(bytes(4096))


sparse(tree / "six", 6)  # six runs: more than i_block's four, depth 1
sparse(tree / "many", 1500)  # 1500 runs: more than 4 x 340, depth 2
for k in range(1200):
    (tree / "wide" / f"entry-{k:04d}-padding-name").write_bytes(b"")
os.symlink("a", tree / "fast")
os.symlink("dir/" + "x" * 100, tree / "slow")
for p in sorted(tree.rglob("*"), reverse=True):
    os.utime(p, (1700000000, 1700000000), follow_symlinks=False)
os.utime(tree, (1700000000, 1700000000))
MINDEPTH = {"a": 0, "dir/big": 0, "cross": 0, "six": 1, "many": 2}
imgs = {}
for name, args in (("plain", []), ("extents", ["--extents"])):
    img = OUT / f"tree-{name}.img"
    if img.exists():
        img.unlink()
    p = paxext2("--from", tree, "--label", "pax-root", "--journal", str(JOURNAL), *args, "256M", img)
    imgs[name] = img if p.returncode == 0 else None
    if p.returncode != 0:
        print(f"ext4.py: tree {name}: paxext2 exit {p.returncode}: {p.stderr.decode(errors='replace').strip()}", flush=True)


def tree_of(img):
    if os.environ.get("PAX_E2FS_NATIVE") == "1":
        from importlib.machinery import SourceFileLoader
        import contextlib
        import io
        wrapper = OUT / "e2fs-local"
        wrapper.write_text('#!/bin/sh\nshift\nexec "$@"\n')
        wrapper.chmod(0o755)
        mod = SourceFileLoader("x3_e2tree", str(ROOT / "tools/e2tree")).load_module()
        mod.E2FS = str(wrapper)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = mod.main(["e2tree", str(img)])
        return code, out.getvalue()
    r = run([ROOT / "tools/e2tree", img])
    return r.returncode, r.stdout.decode(errors="replace")


def without_blocks(text):
    # e2tree's eighth field is i_blocks, which an extent tree and an indirect map count differently.
    return [l.split("\t")[:7] + l.split("\t")[8:] for l in text.splitlines()]


def lookup(img, path):
    """The inode number of PATH in IMG, by the image's own directories (filetype entries)."""
    ino = 2
    for part in path.split("/"):
        found = None
        raw = img.inode(ino)
        t = img.tree(raw) if struct.unpack_from("<I", raw, 32)[0] & EXTENTS_FL else None
        blocks = [p + k for (_l, n, p, _u) in t[1] for k in range(n)] if t else list(struct.unpack_from("<12I", raw, 40))
        for b in blocks:
            if not b or found:
                continue
            d, at = img.block(b), 0
            while at < 4096 and not found:
                child, rec, nl = struct.unpack_from("<IHB", d, at)
                if child and d[at + 8:at + 8 + nl].decode() == part:
                    found = child
                at += rec if rec else 4096
        if not found:
            return None
        ino = found
    return ino


if imgs["plain"] and imgs["extents"]:
    (ca, ta), (cb, tb) = tree_of(imgs["plain"]), tree_of(imgs["extents"])
    (OUT / "tree-plain.txt").write_text(ta)
    (OUT / "tree-extents.txt").write_text(tb)
    clean, rc = fsck_clean(imgs["extents"])
    img = Image(imgs["extents"])
    flagged = []
    for path in ("a", "empty", "dir", "dir/big", "cross", "six", "many", "wide", "slow", "fast"):
        ino = lookup(img, path)
        fl = bool(struct.unpack_from("<I", img.inode(ino), 32)[0] & EXTENTS_FL) if ino else None
        if fl != (path != "fast"):
            flagged.append(f"{path} EXTENTS_FL {fl}")
    ok = ca == 0 and cb == 0 and without_blocks(ta) == without_blocks(tb) and len(ta) > 0 and clean and not flagged
    row("tree", ok, f"a populated root: e2tree (but i_blocks) equal to the indirect build's, e2fsck -fn exit {rc}, the flag on every file, directory and slow link and not the fast link" + ("; " + ", ".join(flagged) if flagged else ""))
    bad = []
    for path, want_depth in MINDEPTH.items():
        ino = lookup(img, path)
        raw = img.inode(ino)
        depth, ext, nodes = img.tree(raw)
        data = (tree / path).read_bytes()
        runs, k, n = [], 0, (len(data) + 4095) // 4096
        while k < n:
            if any(data[k * 4096:(k + 1) * 4096]):
                start = k
                while k < n and any(data[k * 4096:(k + 1) * 4096]) and k - start < 32768:
                    k += 1
                runs.append((start, k - start))
            else:
                k += 1
        logical = [(l, ln) for (l, ln, _p, _u) in ext]
        covers = sorted(set(x for (l, ln) in runs for x in range(l, l + ln))) == sorted(set(x for (l, ln) in logical for x in range(l, l + ln)))
        sectors = struct.unpack_from("<I", raw, 28)[0]
        want_sectors = 8 * (sum(ln for (_l, ln) in logical) + len(nodes))
        if depth != want_depth or not covers or any(u for (*_x, u) in ext) or any(ln > 32768 for (_l, ln) in logical) or sectors != want_sectors:
            bad.append(f"{path}: depth {depth} (want {want_depth}), {len(ext)} extents for {len(runs)} runs, covers {covers}, i_blocks {sectors} (want {want_sectors})")
    row("shape", not bad, "each file's tree has the fewest levels its runs need, its extents exactly its data, no uninitialized extent, i_blocks data and tree" + ("; " + "; ".join(bad) if bad else ""))
else:
    row("tree", False, "the populated root was not built (lines above)")
    row("shape", False, "no extent image to read")

# --- past the indirect reach: 5 GiB, data at both ends
src = OUT / "big-src.bin"
with src.open("wb") as f:
    f.write(block)
    f.truncate(5 << 30)
    f.seek((5 << 30) - 4096)
    f.write(block)
bigdir = OUT / "big-tree"
if bigdir.exists():
    shutil.rmtree(bigdir)
bigdir.mkdir()
shutil.move(str(src), bigdir / "big")
bimg = OUT / "big.img"
if bimg.exists():
    bimg.unlink()
p = paxext2("--from", bigdir, "--extents", "64M", bimg)
if p.returncode == 0:
    clean, rc = fsck_clean(bimg)
    # debugfs `cat` streamed into the hash: 5 GiB never lands on the runner's disk.
    argv = ["debugfs", "-R", "cat /big", bimg] if os.environ.get("PAX_E2FS_NATIVE") == "1" else [ROOT / "tools/e2fs", OUT, "debugfs", "-R", "cat /big", bimg]
    h = hashlib.sha256()
    with subprocess.Popen([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as c:
        for chunk in iter(lambda: c.stdout.read(1 << 20), b""):
            h.update(chunk)
    same = c.returncode == 0 and h.hexdigest() == sha(bigdir / "big")
    row("big", clean and same, f"a 5 GiB sparse file (past the indirect map's 1049612 blocks) as extents: e2fsck -fn exit {rc}, its bytes through debugfs cat {'equal' if same else 'not equal'}")
else:
    row("big", False, f"paxext2 --extents on a 5 GiB sparse file: exit {p.returncode}: {p.stderr.decode(errors='replace').strip()}")
(bigdir / "big").unlink()

# --- Linux's own driver reads the populated root (live, or the record for these exact bytes)
# The walk against e2tree's listing: ext4_walk.py's functions, which the rig's dry runs too.
from importlib.machinery import SourceFileLoader as _Loader
WALK = _Loader("x3_ext4_walk", str(HERE / "ext4_walk.py")).load_module()
walked = WALK.walked


def expected():
    # e2tree's listing of the extent image (debugfs, the oracle): path, type, mode, size, contents.
    if not imgs.get("extents") or not (OUT / "tree-extents.txt").exists():
        return []
    return WALK.expected((OUT / "tree-extents.txt").read_text())


expect = expected()
record = HERE / "ext4-linux.record"
# PAX_E4_LINUX_RECORD=PATH: this host makes the record (written to PATH, never into the checkout); a host that
# makes it must boot Linux live, so a missing kernel is a failure there, not a reason to read the old record.
making = os.environ.get("PAX_E4_LINUX_RECORD", "")
kernel = os.environ.get("PAX_LINUX_KERNEL", f"/usr/lib/modules/{os.uname().release}/vmlinuz")
skipped = False
if imgs.get("extents"):
    image_sha = sha(imgs["extents"])
    live = os.environ.get("PAX_LINUX") != "recorded" and os.access(kernel, os.R_OK)
    if live:
        bb = OUT / "bb"
        run([ROOT / "tools/fetch-busybox", bb])
        mods = os.environ.get("PAX_LINUX_MODULES", f"/usr/lib/modules/{os.uname().release}")

        def guest(name, image, script):
            # tools/linux-blk runs each command through the guest's /bin/sh: busybox, given that name.
            out = OUT / name
            copy = OUT / f"{name}.img"
            shutil.copyfile(image, copy)
            g = run([ROOT / "tools/linux-blk", "--kernel", kernel, "--modules", mods, "--busybox", bb / "busybox", "--ro", "--type", "ext4",
                     "--file", f"{bb / 'busybox'}=/bin/sh", "--file", f"{HERE / script}=/etc/disk/{script}",
                     out, copy, "--", f"/bin/sh /etc/disk/{script}"])
            log = (out / "serial.log").read_text(errors="replace") if (out / "serial.log").exists() else ""
            status = next((l.split()[-1] for l in log.splitlines() if "linux-blk: run 1 status" in l), "?")
            uname = next((l.split()[-1] for l in log.splitlines() if "linux-blk: uname" in l), "?")
            mount = next((l.split()[-1] for l in log.splitlines() if "linux-blk: mount " in l), "?")
            return g.returncode, log, status, uname, mount

        rc, log, status, uname, mount = guest("linux", imgs["extents"], "ext4-walk.sh")
        got = WALK.walk_lines(log)
        errors = [l for l in log.splitlines() if "walk-errors: " in l]
        ok = rc == 0 and status == "0" and bool(expect) and walked(got) == expect and bool(errors) and errors[-1].split()[-1] == "0"
        why = (f"the walk exited {status} in the guest (mount {mount})" if status != "0" else
               f"{len(got)} names against e2tree's {len(expect)}, types, modes, sizes and contents {'equal' if walked(got) == expect else 'not equal'}, EXT4-fs errors {errors[-1].split()[-1] if errors else '?'}")
        row("linux-reads", ok, f"Linux {uname} (live) mounts the root -t ext4 read-only: {why}")
        # The leaf's own depth field set to disagree with its parent's: e2fsck -fn says nothing (the rows takes of
        # 2026-11-23); fsck.ext2 refuses it. This row asks Linux, which decides whether that refusal stands.
        depth_img = OUT / "depth.img"
        shutil.copyfile(imgs["extents"], depth_img)
        di = Image(depth_img)
        six_ino = lookup(di, "six")
        raw6 = di.inode(six_ino)
        leaf = (struct.unpack_from("<H", raw6, 40 + 12 + 8)[0] << 32) | struct.unpack_from("<I", raw6, 40 + 12 + 4)[0]
        with depth_img.open("r+b") as f:
            f.seek(leaf * 4096 + 6)
            f.write(struct.pack("<H", 1))
        depth_sha = sha(depth_img)
        e2 = oracle("e2fsck", "-fn", depth_img).returncode
        rc2, log2, status2, _u, _m = guest("linux-depth", depth_img, "ext4-depth.sh")
        read_rc = next((l.split()[-1] for l in log2.splitlines() if "depth-read: " in l), "?")
        derr = next((l.split()[-1] for l in log2.splitlines() if "depth-errors: " in l), "?")
        refused = status2 == "0" and read_rc not in ("0", "?") and derr not in ("0", "?")
        row("linux-depth", refused, f"Linux {uname} reads six through a leaf whose depth disagrees with its parent's: "
            + (f"refused (cat exit {read_rc}, {derr} EXT4-fs errors), as fsck.ext2 refuses it; e2fsck -fn exit {e2}" if refused else
               f"the guest's run exited {status2}, cat exit {read_rc}, EXT4-fs errors {derr}; e2fsck -fn exit {e2}"))
        if ok and status2 == "0" and making:
            Path(making).write_text(f"# E4-linux-reads' record: Linux {uname} walked the paxext2 --extents root of {len(got)} entries, each equal to\n"
                                    "# e2tree's listing (type, mode, size, contents; a link's target as -> TARGET), and refused six read through\n"
                                    "# a leaf whose depth disagrees with its parent's. Lines: image, uname, the walk, depth.\n"
                                    + f"image {image_sha}\nuname {uname}\n" + "\n".join(got) + "\n"
                                    + f"depth {depth_sha} read {read_rc} errors {derr}\n")
            print(f"ext4.py: the record written to {making}", flush=True)
    elif making:
        row("linux-reads", False, f"this host makes the record (PAX_E4_LINUX_RECORD) but no Linux kernel is readable at {kernel}")
        row("linux-depth", False, "this host makes the record but no Linux kernel is readable")
    elif not record.exists():
        skipped = True
        print(f"SKIP E4-linux-reads no readable Linux kernel ({kernel}) and no record ({record.name})", flush=True)
        print(f"SKIP E4-linux-depth no readable Linux kernel ({kernel}) and no record ({record.name})", flush=True)
    else:
        rec = [l for l in record.read_text().splitlines() if not l.startswith("#")]
        made = rec[1].split()[-1] if len(rec) > 1 else "?"
        print(f"LOUD: E4-linux-reads, E4-linux-depth: no readable Linux kernel ({kernel}) or PAX_LINUX=recorded: the record, made on Linux {made}", flush=True)
        walk_lines = [l for l in rec[2:] if not l.startswith("depth ")]
        same = bool(rec) and rec[0] == f"image {image_sha}"
        ok = same and bool(expect) and walked(walk_lines) == expect
        row("linux-reads", ok, f"the record (Linux {made}) is {'of these bytes' if same else 'of other bytes: remake it'} ({image_sha[:16]}), its walk {'equal' if ok else 'not equal'} to the tree")
        dline = next((l.split() for l in rec if l.startswith("depth ")), None)
        row("linux-depth", bool(dline) and same and dline[3] not in ("0", "?") and dline[5] not in ("0", "?"),
            f"the record (Linux {made}): reading six through the disagreeing leaf " + (f"refused (cat exit {dline[3]}, {dline[5]} EXT4-fs errors)" if dline else "not in the record"))
else:
    row("linux-reads", False, "no extent image to read")
    row("linux-depth", False, "no extent image to damage")

# --- the same inputs, the same bytes
if imgs.get("extents"):
    again = OUT / "tree-again.img"
    if again.exists():
        again.unlink()
    p = paxext2("--from", tree, "--label", "pax-root", "--journal", str(JOURNAL), "--extents", "256M", again)
    row("reproducible", p.returncode == 0 and sha(again) == sha(imgs["extents"]), "the same inputs give the same bytes, the trees and journal included")
    again.unlink(missing_ok=True)
else:
    row("reproducible", False, "no extent image to repeat")

# --- without --extents nothing moved: digests the base binary made (ext4-goldens)
goldens = HERE / "ext4-goldens"
want = dict(l.split() for l in goldens.read_text().splitlines() if l and not l.startswith("#")) if goldens.exists() else {}
got = {}
for name, args in (("ext2-64", ["64M"]), ("ext3-64", ["--journal", str(JOURNAL), "64M"]), ("ext3-448", ["--journal", str(JOURNAL), "448M"])):
    img = OUT / f"same-{name}.img"
    if img.exists():
        img.unlink()
    p = paxext2("--label", "pax-root", *args, img)
    got[name] = sha(img) if p.returncode == 0 else f"exit-{p.returncode}"
    img.unlink(missing_ok=True)
small = OUT / "small-tree"
if small.exists():
    shutil.rmtree(small)
(small / "dir").mkdir(parents=True)
(small / "a").write_bytes(b"journalled content\n")
(small / "dir" / "big").write_bytes(bytes(range(256)) * 20001)
for p in sorted(small.rglob("*"), reverse=True):
    os.utime(p, (1700000000, 1700000000))
os.utime(small, (1700000000, 1700000000))
img = OUT / "same-tree.img"
if img.exists():
    img.unlink()
p = paxext2("--from", small, "--label", "pax-root", "--journal", str(JOURNAL), "64M", img)
got["tree-ext3-64"] = sha(img) if p.returncode == 0 else f"exit-{p.returncode}"
img.unlink(missing_ok=True)
# PAX_E4_GOLDENS_WRITE=PATH: the digests written to PATH (never into the checkout, where the file is tracked).
if os.environ.get("PAX_E4_GOLDENS_WRITE", "") not in ("", "1"):
    Path(os.environ["PAX_E4_GOLDENS_WRITE"]).write_text("# paxext2 without --extents: each image's sha256, made by the base binary (tests/mpx6-disktools.d/ext4.py)\n"
                       + "".join(f"{k} {v}\n" for k, v in sorted(got.items())))
moved = [k for k in got if want.get(k) != got[k]]
row("unchanged", bool(want) and not moved, "ext2 and ext3 images of fixed inputs without --extents hash to the base binary's digests" + (": " + ", ".join(f"{k} {got[k][:16]} (held {want.get(k, 'none')[:16]})" for k in moved) if moved else ""))

print(f"EXT4: {'FAIL' if failed else 'PASS'} ({failed} failed)", flush=True)
sys.exit(1 if failed else 0)
