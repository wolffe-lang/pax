#!/usr/bin/env python3
"""Fixtures for tests/mpx6-ext2's extent read rows (XR), with their manifest.

    xr-fixture.py --paxext2 BIN --e2fs TOOLS_E2FS --work DIR

Every image starts as paxext2's own --extents output (the formatter the
disk-tools suite holds to pinned e2fsck and debugfs) and is checked again
here by the pinned readers through tools/e2fs: e2fsck -fn clean, every
regular file's bytes through debugfs dump, each tree's depth from its
inode. Damaged, unwritten, feature and state variants are byte edits of
copies, at offsets taken from the published layout (Documentation/
filesystems/ext4: super.rst, group_descr.rst, inodes.rst, ifork.rst,
journal.rst); e2fsck's verdict on each copy is saved, not assumed. No
fixture is ever repaired. The damage set also makes K, an extent volume of
1 KiB blocks from pinned mke2fs (paxext2 makes only 4 KiB blocks) with
exactly the extent profile, held to e2fsck and debugfs alike.

Prints `PASS XR-fixture-<set>` or `FAIL XR-fixture-<set> <why>` and writes
DIR/manifest.json for xr-judge.py. Exit 0 when every set was made.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

EPOCH = "1700000000"
BS = 4096
MAGIC = 0xF30A


class Failure(Exception):
    pass


def need(ok, why):
    if not ok:
        raise Failure(why)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pattern(path, runs):
    """`runs` one-block runs, each a byte of its own, with a hole between."""
    with open(path, "wb") as f:
        f.truncate((runs * 2 - 1) * BS)
        for n in range(runs):
            f.seek(n * 2 * BS)
            f.write(bytes([n % 251 + 1]) * BS)


def sparse_copy(src, dst):
    """A copy that leaves all-zero blocks as holes (the images are mostly empty)."""
    with open(src, "rb") as a, open(dst, "wb") as b:
        size = os.fstat(a.fileno()).st_size
        while True:
            chunk = a.read(1 << 16)
            if not chunk:
                break
            if chunk.count(0) == len(chunk):
                b.seek(len(chunk), os.SEEK_CUR)
            else:
                b.write(chunk)
        b.truncate(size)


class Tools:
    def __init__(self, paxext2, e2fs, work):
        self.paxext2, self.e2fs, self.work = paxext2, e2fs, work
        self.env = dict(os.environ, SOURCE_DATE_EPOCH=EPOCH, E2FSPROGS_FAKE_TIME=EPOCH, SHELL="/bin/sh")

    def run(self, argv, tag, limit=600):
        r = subprocess.run([str(a) for a in argv], env=self.env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=limit)
        (self.work / "logs" / (tag + ".log")).write_bytes(r.stdout)
        return r

    def format(self, tree, size, image, journal, label):
        argv = [self.paxext2, "--from", tree, "--label", label, "--seed", label]
        if journal:
            argv += ["--journal", str(journal)]
        argv += ["--extents", size, image]
        r = self.run(argv, "paxext2-" + label)
        need(r.returncode == 0 and image.is_file(), f"paxext2 {label} exit {r.returncode}; see logs/paxext2-{label}.log")

    def fsck(self, image, tag):
        return self.run([self.e2fs, self.work, "e2fsck", "-fn", image], "e2fsck-" + tag).returncode

    def debugfs(self, image, command, tag):
        return self.run([self.e2fs, self.work, "debugfs", "-R", command, image], "debugfs-" + tag)


class Image:
    """Offsets in one image, read from its own superblock and descriptors."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            f.seek(1024)
            self.sb = f.read(1024)
        w = lambda o, n=4: int.from_bytes(self.sb[o:o + n], "little")
        need(w(0x38, 2) == 0xEF53, f"{path.name}: no ext2 superblock magic")
        need(w(0x18) in (0, 1, 2), f"{path.name}: block size is not 1, 2 or 4 KiB")
        self.bs = 1024 << w(0x18)
        self.blocks = w(0x4)
        self.first = w(0x14)
        self.ipg = w(0x28)
        self.isize = w(0x58, 2)
        self.words = (w(0x5C), w(0x60), w(0x64))

    def read(self, off, n):
        with open(self.path, "rb") as f:
            f.seek(off)
            return f.read(n)

    def write(self, off, data):
        with open(self.path, "r+b") as f:
            f.seek(off)
            f.write(data)

    def u(self, off, n):
        return int.from_bytes(self.read(off, n), "little")

    def put(self, off, n, value):
        self.write(off, value.to_bytes(n, "little"))

    def itable(self, group):
        return self.u((self.first + 1) * self.bs + group * 32 + 8, 4)

    def inode(self, ino):
        group, index = divmod(ino - 1, self.ipg)
        at = self.itable(group) * self.bs + index * self.isize
        need(0 < at < self.blocks * self.bs, f"inode {ino} outside the image")
        return at

    def header(self, at):
        return {"magic": self.u(at, 2), "entries": self.u(at + 2, 2), "max": self.u(at + 4, 2),
                "depth": self.u(at + 6, 2)}

    def child(self, at, k):
        """Index entry k of the node at `at`: its key and child block."""
        e = at + 12 + 12 * k
        return self.u(e, 4), self.u(e + 4, 4) | (self.u(e + 8, 2) << 32)

    def leaf(self, at, k):
        """Leaf entry k: (start block, length field, physical) and its offset."""
        e = at + 12 + 12 * k
        return (self.u(e, 4), self.u(e + 4, 2), self.u(e + 8, 4) | (self.u(e + 6, 2) << 32)), e


def build_tree(root, files):
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for rel, kind, value in files:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if kind == "bytes":
            p.write_bytes(value)
        elif kind == "pattern":
            pattern(p, value)
        elif kind == "blocks":
            p.write_bytes(b"".join(bytes([n % 251 + 1]) * BS for n in range(value)))
        elif kind == "dir":
            p.mkdir(exist_ok=True)
        elif kind == "link":
            os.symlink(value, p)
        elif kind == "big":
            block = bytes(range(256)) * 16
            with p.open("wb") as f:
                for at in value:
                    f.seek(at)
                    f.write(block)
                f.truncate(5 << 30)


def stat_ino(tools, image, path, tag):
    r = tools.debugfs(image, "stat " + path, tag)
    text = r.stdout.decode(errors="replace")
    ino = re.search(r"\bInode:\s*(\d+)", text)
    flags = re.search(r"\bFlags:\s*(0x[0-9a-fA-F]+)", text)
    need(r.returncode == 0 and ino and flags, f"debugfs stat {path}: no inode or flags")
    return int(ino[1]), int(flags[1], 16)


def dumped(tools, image, src, rel, tag):
    """Hold file `rel` of `image` to its source through pinned debugfs."""
    out = tools.work / "dump.tmp"
    if out.exists():
        out.unlink()
    r = tools.debugfs(image, f"dump /{rel} {out}", f"{tag}-dump-{rel.replace('/', '_')}")
    need(r.returncode == 0 and out.is_file() and sha(out) == sha(src),
         f"{tag}: debugfs dump of {rel} is not its source")
    out.unlink()


def checked_base(tools, tree, size, name, journal, files, undumped=()):
    """Format, then hold the image to e2fsck and debugfs: (image, its record).
    A file in `undumped` (the 5 GiB sparse one) is not dumped whole: its
    bytes are held at its data blocks and holes by the boot's own reads."""
    image = tools.work / (name + ".img")
    tools.format(tree, size, image, journal, "xr-" + name)
    need(tools.fsck(image, name) == 0, f"{name}: e2fsck -fn not clean on the formatter's own image")
    img = Image(image)
    want = (4 if journal else 0, 0x42, 3)
    need(img.words == want, f"{name}: feature words {img.words}, want {want}")
    record = {"image": image.name, "sha256": sha(image), "blocks": img.blocks, "files": {}}
    for rel in files:
        src = tree / rel
        ino, flags = stat_ino(tools, image, "/" + rel, f"{name}-stat-{rel.replace('/', '_')}")
        entry = {"ino": ino, "flags": flags}
        if src.is_symlink():
            entry["target"] = os.readlink(src)
        elif src.is_dir():
            entry["names"] = sorted(os.listdir(src))
        elif rel in undumped:
            entry["bytes"] = src.stat().st_size
        else:
            dumped(tools, image, src, rel, name)
            entry["bytes"] = src.stat().st_size
            entry["sha256"] = sha(src)
        if not src.is_symlink() or len(os.readlink(src)) >= 60:
            need(flags & 0x80000, f"{name}: {rel} has no EXTENTS_FL")
            entry["depth"] = img.header(img.inode(ino) + 40)["depth"]
        else:
            need(not flags & 0x80000, f"{name}: fast link {rel} has EXTENTS_FL")
        record["files"][rel] = entry
    return image, img, record


def damaged(tools, base, name, edit, record):
    """A copy of `base` with one edit; e2fsck's verdict on it saved."""
    image = tools.work / (name + ".img")
    sparse_copy(base, image)
    before = sha(image)
    what = edit(Image(image))
    need(sha(image) != before, f"{name}: the edit changed nothing")
    record[name] = {"image": image.name, "sha256": sha(image), "edit": what,
                    "e2fsck": tools.fsck(image, name)}
    return image


def make(args):
    work = args.work
    need(not work.exists(), f"{work} exists; fixtures are made fresh")
    (work / "logs").mkdir(parents=True)
    tools = Tools(args.paxext2, args.e2fs, work)
    manifest = {"paxext2_sha256": sha(args.paxext2)}
    ok = True

    def section(name, fn):
        nonlocal ok
        try:
            text = fn()
            print(f"PASS XR-fixture-{name} {text}", flush=True)
        except (Failure, OSError, subprocess.TimeoutExpired) as e:
            ok = False
            print(f"FAIL XR-fixture-{name} {e}", flush=True)

    # --- P: what a correct reader returns, and U: an unwritten range ---------------
    pfiles = [("empty", "bytes", b""), ("small", "bytes", b"an extent-mapped file, read back\n"),
              ("long", "blocks", 2049),
              ("six", "pattern", 6), ("many", "pattern", 1500),
              ("big", "big", [0, (4 << 30) + 8192, (5 << 30) - BS]),
              ("d/sub/deep.txt", "bytes", b"two directories down\n"),
              ("fl", "link", "small"), ("sl", "link", "d/sub/" + "a-long-link-target-" * 4)]
    pfiles += [(f"d/n{k:03d}", "bytes", f"n{k:03d}\n".encode()) for k in range(600)]

    def p_set():
        tree = work / "tree-p"
        build_tree(tree, pfiles)
        names = ["empty", "small", "long", "six", "many", "big", "d", "d/sub", "d/sub/deep.txt", "fl", "sl"]
        names += [f"d/n{k:03d}" for k in (0, 1, 299, 300, 598, 599)]
        image, img, rec = checked_base(tools, tree, "128M", "P", 4096, names, undumped=("big",))
        f = rec["files"]
        need((f["long"]["depth"], f["six"]["depth"], f["many"]["depth"]) == (0, 1, 2),
             f"depths long/six/many {f['long'].get('depth')}/{f['six'].get('depth')}/{f['many'].get('depth')}")
        # How every file was made, so the judge rebuilds any range's bytes.
        rec["sources"] = {rel: {"kind": kind, "value": value.hex() if kind == "bytes" else value}
                          for rel, kind, value in pfiles if kind != "dir"}
        manifest["P"] = rec
        # U: six's third run marked unwritten (ee_len + 32768); its disk bytes stay nonzero.
        u = {}

        def unwritten(i):
            root = i.inode(f["six"]["ino"]) + 40
            _key, blk = i.child(root, 0)
            (start, length, phys), e = i.leaf(blk * BS, 2)
            need(length == 1 and phys != 0, f"six's third run is {length} at {phys}")
            need(i.read(phys * BS, BS).count(0) == 0, "six's third run is not nonzero on disk")
            i.put(e + 4, 2, length + 32768)
            return {"file": "six", "logical": start, "blocks": length}

        damaged(tools, image, "U", unwritten, u)
        want = bytearray((tree / "six").read_bytes())
        lo = u["U"]["edit"]["logical"] * BS
        want[lo:lo + BS] = bytes(BS)
        u["U"]["six_sha256"] = hashlib.sha256(bytes(want)).hexdigest()
        u["U"]["six_bytes"] = len(want)
        manifest["U"] = u["U"]
        shutil.rmtree(tree / "d")
        (tree / "big").unlink()
        return f"P {rec['sha256'][:16]} (depths 0/1/2, 600 names, links, 5 GiB sparse), U e2fsck exit {u['U']['e2fsck']}"

    # --- Q: one damage case a file, controls on both sides --------------------------
    victims = ["v-magic", "v-max", "v-max2", "v-maxover", "v-max1", "v-entries", "v-depth-child", "v-depth-root", "v-unsorted",
               "v-overlap", "v-len0", "v-hiaddr", "v-pastend", "v-metadata", "v-journal"]
    qfiles = [("c-before", "pattern", 6), ("c-after", "pattern", 6), ("f-inline", "bytes", b"inline?\n"),
              ("f-encrypt", "bytes", b"encrypted?\n"), ("m-depth6", "pattern", 1500),
              ("m-idx-unsorted", "pattern", 1500), ("m-idx-max", "pattern", 1500),
              ("m-idx-338", "pattern", 1500), ("m-idx-337", "pattern", 1500),
              ("s-bad", "link", "c-before/" + "x" * 80)]
    qfiles += [(v, "pattern", 6) for v in victims]
    qfiles += [(f"d-out/n{k:03d}", "bytes", b"") for k in range(600)]
    qfiles += [(f"d-hole/n{k:03d}", "bytes", b"") for k in range(600)]

    def q_set():
        tree = work / "tree-q"
        build_tree(tree, qfiles)
        names = [rel for rel, *_ in qfiles if not rel.startswith("d-")] + ["d-out", "d-hole"]
        image, img, rec = checked_base(tools, tree, "64M", "Q-base", 1024, names)
        f = rec["files"]
        for v in victims + ["c-before", "c-after"]:
            need(f[v]["depth"] == 1, f"{v} depth {f[v]['depth']}")
        for m in ("m-depth6", "m-idx-unsorted", "m-idx-max", "m-idx-338", "m-idx-337"):
            need(f[m]["depth"] == 2, f"{m} depth {f[m]['depth']}")
        jroot = img.inode(8) + 40
        jh = img.header(jroot)
        need(jh["magic"] == MAGIC and jh["depth"] == 0 and jh["entries"] >= 1, f"journal tree {jh}")
        (_js, _jl, jphys), _ = img.leaf(jroot, 0)
        cases = {}

        def root(i, rel):
            return i.inode(f[rel]["ino"]) + 40

        def leafblock(i, rel):
            return i.child(root(i, rel), 0)[1] * BS

        def edit(i):
            out = {}
            r = root(i, "v-magic"); i.put(r, 2, 0x1234); out["v-magic"] = "root magic 0x1234"
            # Not damage: an eh_max one or two under its node's room, which pinned
            # e2fsck accepts at rooms 4, 84 and 340 and the Linux guest reads
            # whole. Three or more under, pinned e2fsck calls corrupt.
            r = root(i, "v-max"); i.put(r + 4, 2, 3); out["v-max"] = "root eh_max 3 under its room of 4"
            r = root(i, "v-max2"); i.put(r + 4, 2, 2); out["v-max2"] = "root eh_max 2, two under its room of 4"
            r = root(i, "v-maxover"); i.put(r + 4, 2, 5); out["v-maxover"] = "root eh_max 5 over its room of 4"
            r = root(i, "v-max1"); i.put(r + 4, 2, 1); out["v-max1"] = "root eh_max 1, three under its room of 4"
            room = (BS - 12) // 12
            for rel, mx in (("m-idx-max", 100), ("m-idx-338", room - 2), ("m-idx-337", room - 3)):
                ib = i.child(root(i, rel), 0)[1] * BS
                need(i.header(ib)["depth"] == 1 and i.header(ib)["entries"] <= mx, f"{rel}'s index node {i.header(ib)}")
                i.put(ib + 4, 2, mx); out[rel] = f"index block eh_max {mx} under its room of {room}"
            r = root(i, "v-entries"); i.put(r + 2, 2, 5); out["v-entries"] = "root eh_entries 5 over eh_max 4"
            lb = leafblock(i, "v-depth-child"); i.put(lb + 6, 2, 1); out["v-depth-child"] = "leaf says depth 1 under a depth-1 root"
            # Only the parent-and-child depth rule catches this one: every
            # entry below is well formed, the root merely claims one level more.
            r = root(i, "v-depth-root"); i.put(r + 6, 2, 2); out["v-depth-root"] = "root says depth 2 over a real leaf"
            lb = leafblock(i, "v-unsorted")
            a, b = i.read(lb + 12 + 24, 12), i.read(lb + 12 + 36, 12)
            i.write(lb + 12 + 24, b); i.write(lb + 12 + 36, a); out["v-unsorted"] = "leaf entries 2 and 3 swapped"
            lb = leafblock(i, "v-overlap")
            (s2, _l, _p), _ = i.leaf(lb, 2); (_s, _l3, _p3), e3 = i.leaf(lb, 3)
            i.put(e3, 4, s2); out["v-overlap"] = f"leaf entry 3 starts at entry 2's block {s2}"
            lb = leafblock(i, "v-len0"); (_s, _l, _p), e = i.leaf(lb, 1); i.put(e + 4, 2, 0); out["v-len0"] = "leaf entry 1 ee_len 0"
            lb = leafblock(i, "v-hiaddr"); (_s, _l, _p), e = i.leaf(lb, 0); i.put(e + 6, 2, 1); out["v-hiaddr"] = "leaf entry 0 ee_start_hi 1"
            lb = leafblock(i, "v-pastend"); (_s, _l, _p), e = i.leaf(lb, 0); i.put(e + 8, 4, i.blocks)
            out["v-pastend"] = f"leaf entry 0 at block {i.blocks}, the first past the end"
            lb = leafblock(i, "v-metadata"); (_s, _l, _p), e = i.leaf(lb, 0); i.put(e + 8, 4, i.itable(0))
            out["v-metadata"] = f"leaf entry 0 at the inode table, block {i.itable(0)}"
            lb = leafblock(i, "v-journal"); (_s, _l, _p), e = i.leaf(lb, 0); i.put(e + 8, 4, jphys + 1)
            out["v-journal"] = f"leaf entry 0 inside the journal, block {jphys + 1}"
            r = root(i, "m-depth6"); i.put(r + 6, 2, 6); out["m-depth6"] = "root eh_depth 6"
            ib = i.child(root(i, "m-idx-unsorted"), 0)[1] * BS
            need(i.header(ib)["entries"] >= 3, "m-idx-unsorted's index node has under 3 entries")
            a, b = i.read(ib + 12 + 12, 12), i.read(ib + 12 + 24, 12)
            i.write(ib + 12 + 12, b); i.write(ib + 12 + 24, a); out["m-idx-unsorted"] = "index entries 1 and 2 swapped"
            for rel, bit in (("f-inline", 0x10000000), ("f-encrypt", 0x800)):
                at = i.inode(f[rel]["ino"]) + 0x20
                i.put(at, 4, i.u(at, 4) | bit); out[rel] = f"inode flag 0x{bit:x}"
            for rel in ("d-out", "d-hole", "s-bad"):
                r = root(i, rel)
                h = i.header(r)
                need(h["magic"] == MAGIC and h["depth"] == 0 and h["entries"] == 1, f"{rel} tree {h}")
            (_s, ln, _p), e = i.leaf(root(i, "d-out"), 0); i.put(e + 8, 4, i.blocks)
            out["d-out"] = f"the directory's only extent at block {i.blocks}"
            (_s, ln, _p), e = i.leaf(root(i, "d-hole"), 0)
            need(2 <= ln <= 32768, f"d-hole's extent is {ln} blocks")
            i.put(e + 4, 2, ln - 1); out["d-hole"] = f"the directory's last block of {ln} a hole"
            (_s, ln, _p), e = i.leaf(root(i, "s-bad"), 0); i.put(e + 8, 4, i.blocks)
            out["s-bad"] = f"the link's block at {i.blocks}"
            return out

        damaged(tools, image, "Q", edit, cases)
        f["d-hole"]["names"] = sorted(os.listdir(tree / "d-hole"))
        f["d-out"]["names"] = sorted(os.listdir(tree / "d-out"))
        manifest["Q"] = {"base": rec, **cases["Q"]}
        shutil.rmtree(tree)
        (work / "Q-base.img").unlink()
        kilo = k_image()
        return (f"Q: {len(cases['Q']['edit'])} edits on one copy, e2fsck exit {cases['Q']['e2fsck']}; "
                f"K: 1 KiB blocks, two leaf eh_max edits, e2fsck exit {kilo}")

    # --- K: an extent volume of 1 KiB blocks (leaf room 84), beside Q in its boot ----
    kfiles = [("k-control", "pattern", 6), ("k-max82", "pattern", 6), ("k-max81", "pattern", 6)]

    def k_image():
        """Pinned mke2fs (paxext2 makes only 4 KiB blocks) with exactly the
        extent profile: filetype and extent, sparse_super and large_file,
        no journal. k-max82's leaf says eh_max 82 (two under its room of
        84), k-max81's 81 (three under)."""
        tree = work / "tree-k"
        build_tree(tree, kfiles)
        base = work / "K-base.img"
        r = tools.run([tools.e2fs, work, "mke2fs", "-q", "-F", "-t", "ext4", "-b", "1024", "-I", "256",
                       "-O", "^has_journal,^metadata_csum,^64bit,^flex_bg,^huge_file,^dir_nlink,^extra_isize,"
                       "^ext_attr,^resize_inode,^dir_index",
                       "-U", "6b2d8c1e-4f3a-4e7b-9c5d-0a1b2c3d4e5f", "-L", "xr-K", "-d", tree, base, "8M"], "mke2fs-xr-K")
        need(r.returncode == 0 and base.is_file(), f"mke2fs xr-K exit {r.returncode}; see logs/mke2fs-xr-K.log")
        need(tools.fsck(base, "K-base") == 0, "K-base: e2fsck -fn not clean on mke2fs's own image")
        img = Image(base)
        need(img.bs == 1024 and img.words == (0, 0x42, 3), f"K-base: block size {img.bs}, feature words {img.words}")
        room = (img.bs - 12) // 12
        files = {}
        for rel, *_ in kfiles:
            ino, flags = stat_ino(tools, base, "/" + rel, "K-base-stat-" + rel)
            need(flags & 0x80000, f"K-base: {rel} has no EXTENTS_FL")
            dumped(tools, base, tree / rel, rel, "K-base")
            h = img.header(img.inode(ino) + 40)
            need(h["magic"] == MAGIC and h["depth"] == 1, f"K-base: {rel}'s root {h}")
            files[rel] = {"ino": ino, "bytes": (tree / rel).stat().st_size, "sha256": sha(tree / rel)}

        def edit(i):
            out = {}
            for rel, mx in (("k-max82", room - 2), ("k-max81", room - 3)):
                leaf = i.child(i.inode(files[rel]["ino"]) + 40, 0)[1] * i.bs
                h = i.header(leaf)
                need(h["depth"] == 0 and h["max"] == room and h["entries"] <= mx, f"{rel}'s leaf {h}")
                i.put(leaf + 4, 2, mx)
                out[rel] = f"leaf eh_max {mx} under its room of {room}"
            return out

        cases = {}
        damaged(tools, base, "K", edit, cases)
        manifest["K"] = {**cases["K"], "files": files}
        shutil.rmtree(tree)
        base.unlink()
        return cases["K"]["e2fsck"]

    # --- F: one superblock feature bit a copy, no journal ---------------------------
    features = [(1, 0x1, "compression"), (1, 0x8, "journal_dev"), (1, 0x10, "meta_bg"), (1, 0x80, "64bit"),
                (1, 0x100, "mmp"), (1, 0x200, "flex_bg"), (1, 0x400, "ea_inode"), (1, 0x1000, "dirdata"),
                (1, 0x2000, "metadata_csum_seed"), (1, 0x4000, "large_dir"), (1, 0x8000, "inline_data"),
                (1, 0x10000, "encrypt"), (1, 0x20000, "casefold"), (1, 0x80000000, "incompat-0x80000000"),
                (2, 0x4, "btree_dir"), (2, 0x8, "huge_file"), (2, 0x10, "gdt_csum"), (2, 0x20, "dir_nlink"),
                (2, 0x40, "extra_isize"), (2, 0x100, "quota"), (2, 0x200, "bigalloc"), (2, 0x400, "metadata_csum"),
                (2, 0x1000, "readonly"), (2, 0x2000, "project"), (2, 0x8000, "verity"),
                (2, 0x10000, "orphan_present"), (2, 0x80000000, "ro_compat-0x80000000"),
                (0, 0x1, "dir_prealloc"), (0, 0x2, "imagic_inodes"), (0, 0x8, "ext_attr"),
                (0, 0x10, "resize_inode"), (0, 0x20, "dir_index"), (0, 0x200, "sparse_super2"),
                (0, 0x400, "fast_commit"), (0, 0x1000, "orphan_file"), (0, 0x80000000, "compat-0x80000000")]

    def f_set():
        tree = work / "tree-f"
        build_tree(tree, [("a", "bytes", b"a\n")])
        image, img, rec = checked_base(tools, tree, "8M", "F-base", 0, ["a"])
        out = {}
        for word, bit, name in features:
            def edit(i, word=word, bit=bit):
                at = 1024 + 0x5C + 4 * word
                i.put(at, 4, i.u(at, 4) | bit)
                return {"word": ["compat", "incompat", "ro_compat"][word], "bit": bit}
            damaged(tools, image, "F-" + name, edit, out)
        manifest["F"] = {"base": rec, "cases": out}
        shutil.rmtree(tree)
        return f"F: {len(out)} copies, one bit each, on {rec['sha256'][:16]}"

    # --- J: journal and state refusals, and their clean control ---------------------
    def j_set():
        tree = work / "tree-j"
        build_tree(tree, [("a", "bytes", b"a\n")])
        image, img, rec = checked_base(tools, tree, "32M", "J-base", 1024, ["a"])
        jroot = img.inode(8) + 40
        jh = img.header(jroot)
        need(jh["magic"] == MAGIC and jh["depth"] == 0 and jh["entries"] == 1, f"journal tree {jh}")
        (_s, jlen, jphys), jent = img.leaf(jroot, 0)
        need(img.read(jphys * BS, 4) == bytes.fromhex("c03b3998"), "no journal superblock at the journal's first block")
        out = {}
        edits = {
            "s_start": lambda i: (i.write(jphys * BS + 0x1C, (1).to_bytes(4, "big")), "journal s_start 1")[1],
            "needs_recovery": lambda i: (i.put(1024 + 0x60, 4, i.u(1024 + 0x60, 4) | 0x4), "needs_recovery set")[1],
            "orphan": lambda i: (i.put(1024 + 0xE8, 4, 12), "s_last_orphan 12")[1],
            "error_state": lambda i: (i.put(1024 + 0x3A, 2, i.u(1024 + 0x3A, 2) | 0x2), "s_state errors")[1],
            "not_clean": lambda i: (i.put(1024 + 0x3A, 2, i.u(1024 + 0x3A, 2) & ~0x1), "s_state not clean")[1],
            "journal_unwritten": lambda i: (i.put(jent + 4, 2, jlen + 32768), "the journal's extent unwritten")[1],
            "journal_hole": lambda i: (i.put(jent + 4, 2, jlen - 1), "the journal's last block a hole")[1],
        }
        for name, edit in edits.items():
            damaged(tools, image, "J-" + name, edit, out)
        clean = work / "J-clean.img"
        sparse_copy(image, clean)
        manifest["J"] = {"base": rec, "clean": {"image": clean.name, "sha256": sha(clean)}, "cases": out}
        shutil.rmtree(tree)
        return f"J: clean control and {len(out)} refusals on {rec['sha256'][:16]}"

    # --- M: two groups, a file whose blocks are all in the second ----------------
    def m_set():
        tree = work / "tree-m"
        build_tree(tree, [("a-fill", "blocks", 34000), ("b-far", "pattern", 6)])
        image, img, rec = checked_base(tools, tree, "256M", "M", 4096, ["a-fill", "b-far"])
        need(img.blocks > 32768, f"M has {img.blocks} blocks, one group")
        leaf = img.child(img.inode(rec["files"]["b-far"]["ino"]) + 40, 0)[1] * BS
        (_s, _l, phys), _ = img.leaf(leaf, 0)
        need(phys >= 32768 and img.itable(1) >= 32768, f"b-far's first block {phys}, group 1's table {img.itable(1)}")
        rec["far_block"] = phys
        manifest["M"] = rec
        shutil.rmtree(tree)
        return f"M {rec['sha256'][:16]}: {img.blocks} blocks, b-far from block {phys} (group 1)"

    section("P", p_set)
    section("M", m_set)
    section("Q", q_set)
    section("F", f_set)
    section("J", j_set)
    (work / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"XR-FIXTURE-END exit={0 if ok else 1}", flush=True)  # five sets: P, M, Q, F, J
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--paxext2", required=True, type=lambda s: Path(s).resolve())
    p.add_argument("--e2fs", required=True, type=lambda s: Path(s).resolve())
    p.add_argument("--work", required=True, type=lambda s: Path(s).resolve())
    return make(p.parse_args())


if __name__ == "__main__":
    sys.exit(main())
