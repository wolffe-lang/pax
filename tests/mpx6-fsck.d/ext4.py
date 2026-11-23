#!/usr/bin/env python3
"""fsck.ext2 on X3's ext4 (ext3's features and `extent`), held to e2fsck.

  ext4.py CHECKER WORK [PAXEXT2]

Each row prints `PASS F-ext4-<name> …` or `FAIL F-ext4-<name> …`; the exit is
1 when any row failed. The oracles (mke2fs, e2fsck, debugfs, dumpe2fs) are
e2fsprogs' own programs on PATH (tests/mpx6-fsck's wrappers or the pinned
image's), run as black boxes. Damage is made here, byte by byte, from the
documented layout (Documentation/filesystems/ext4/ifork.rst, inodes.rst); a
damage row first asks e2fsck -fn whether the copy is damaged at all.

  F-ext4-clean-*     no finding, nothing written, on mke2fs's, paxext2's and a mixed image
  F-ext4-damage-*    e2fsck -fn exit 4, fsck.ext2 -fn exit 4 with a finding that names
                     the inode and its extent tree; both leave the copy unchanged; no hang
  F-ext4-repair-*    damage no tree holds, fsck.ext2 -fy's bytes against e2fsck -fy's
  F-ext4-refused-*   a repair that would change an extent tree: refused by name, nothing written
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

sys.dont_write_bytecode = True
CHECKER = Path(sys.argv[1]).resolve()
WORK = Path(sys.argv[2]).resolve()
PAXEXT2 = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None
WORK.mkdir(parents=True, exist_ok=True)
os.environ.update(SOURCE_DATE_EPOCH="1700000000", E2FSPROGS_FAKE_TIME="1700000000", TZ="UTC", LC_ALL="C")
PROFILE = {"extent", "filetype", "has_journal", "large_file", "sparse_super"}
EXTENTS_FL = 0x80000
CAP = 60
failed = 0


def row(name, ok, why):
    global failed
    print(("PASS " if ok else "FAIL ") + "F-ext4-" + name + " " + why, flush=True)
    if not ok:
        failed += 1


def run(argv, timeout=None):
    try:
        return subprocess.run([str(x) for x in argv], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, b"timeout\n")


def digest(path):
    st = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), st.st_mtime_ns, st.st_ctime_ns


def features(path):
    for line in run(["dumpe2fs", "-h", path]).stdout.decode(errors="replace").splitlines():
        if line.startswith("Filesystem features:"):
            return set(line.split(":", 1)[1].split())
    return set()


def fresh(path, mib):
    if path.exists():
        path.unlink()
    with path.open("wb") as f:
        f.truncate(mib << 20)


def profile_o(mib):
    probe = WORK / "defaults.img"
    fresh(probe, mib)
    assert run(["mke2fs", "-q", "-F", "-t", "ext4", "-b", "4096", probe]).returncode == 0
    have = features(probe)
    probe.unlink()
    return ",".join(sorted("^" + f for f in have - PROFILE) + sorted(PROFILE - have))


class Image:
    def __init__(self, path):
        self.path = path
        self.b = bytearray(path.read_bytes())
        self.sb = 1024
        self.ipg = self.u(self.sb + 40)
        self.isize = self.u(self.sb + 88, 2)
        self.blocks = self.u(self.sb + 4)

    def u(self, at, n=4):
        return int.from_bytes(self.b[at:at + n], "little")

    def put(self, at, value, n=4):
        self.b[at:at + n] = value.to_bytes(n, "little")

    def table(self, g):
        return self.u(4096 + g * 32 + 8)

    def ino(self, number):
        g, i = divmod(number - 1, self.ipg)
        return self.table(g) * 4096 + i * self.isize

    def save(self, path):
        path.write_bytes(bytes(self.b))

    def nodes(self, number):
        """[(offset of the node's header, depth)] of inode NUMBER's tree, the root first."""
        out = []

        def walk(at):
            depth, entries = self.u(at + 6, 2), self.u(at + 2, 2)
            out.append((at, depth))
            if depth:
                for e in range(entries):
                    o = at + 12 + 12 * e
                    walk(((self.u(o + 8, 2) << 32) | self.u(o + 4)) * 4096)
        walk(self.ino(number) + 40)
        return out

    def leaves(self, number):
        return [at for (at, d) in self.nodes(number) if d == 0]


def debugfs_w(img, cmds):
    f = WORK / "cmds.txt"
    f.write_text("\n".join(cmds) + "\n")
    return run(["debugfs", "-w", "-f", f, img])


def inode_of(img, path):
    m = re.search(rb"Inode: (\d+)", run(["debugfs", "-R", f"stat {path}", img]).stdout)
    return int(m.group(1)) if m else None


# --- the fixtures: mke2fs's profile image populated by debugfs (write, punch, fallocate, mkdir, symlink)
O = profile_o(64)
base = WORK / "base.img"
fresh(base, 64)
assert run(["mke2fs", "-q", "-F", "-t", "ext4", "-O", O, "-b", "4096", "-I", "256", "-J", "size=16", base]).returncode == 0
src = WORK / "src.bin"
src.write_bytes(bytes(range(1, 256)) * 16 * 3000)
small = WORK / "small.bin"
small.write_bytes(b"extent fixture\n")
cmds = ["write %s a" % small, "write %s six" % src, "write %s many" % src, "write %s pre" % small, "mkdir d", "write %s d/b" % small,
        "symlink fast a", "symlink slow " + "d/" + "x" * 100]
cmds += ["punch six %d %d" % (b, b) for b in range(1, 11, 2)]
cmds += ["punch many %d %d" % (b, b) for b in range(1, 3000, 2)]
cmds += ["fallocate pre 1 99"]
p = debugfs_w(base, cmds)
(WORK / "populate.log").write_bytes(p.stdout)
INO = {n: inode_of(base, n) for n in ("a", "six", "many", "pre", "d")}
depths = {}
img0 = Image(base)
for n in ("six", "many"):
    nodes = img0.nodes(INO[n]) if INO[n] else []
    depths[n] = nodes[0][1] if nodes else None
print(f"ext4.py: the fixture: -O {O}; inodes {INO}; root depths {depths}", flush=True)


def checker(img, mode):
    return run([CHECKER, mode, img], timeout=CAP)


def clean_row(name, img):
    before = digest(img)
    c = checker(img, "-fn")
    out = c.stdout.decode(errors="replace")
    e = run(["e2fsck", "-fn", img]).returncode
    ok = c.returncode == 0 and e == 0 and digest(img) == before
    (WORK / f"clean-{name}.log").write_text(out)
    row(f"clean-{name}", ok, f"fsck.ext2 -fn exit {c.returncode} (e2fsck -fn {e}), {'nothing written' if digest(img) == before else 'the image changed'}" + ("" if ok else ": " + out.strip().splitlines()[-1] if out.strip() else ""))


clean_row("mke2fs", base)
if PAXEXT2 and PAXEXT2.exists():
    tree = WORK / "tree"
    shutil.rmtree(tree, ignore_errors=True)
    (tree / "d").mkdir(parents=True)
    (tree / "a").write_bytes(b"paxext2 fixture\n")
    shutil.copyfile(src, tree / "d" / "big")
    pimg = WORK / "paxext2.img"
    pimg.unlink(missing_ok=True)
    p = run([PAXEXT2, "--from", tree, "--journal", "4096", "--extents", "64M", pimg])
    if p.returncode == 0:
        clean_row("paxext2", pimg)
    else:
        row("clean-paxext2", False, f"paxext2 --extents exit {p.returncode}: {p.stdout.decode(errors='replace').strip()}")
else:
    row("clean-paxext2", False, "no paxext2 beside the checker (tests/mpx6-fsck builds it)")
mixed = WORK / "mixed.img"
fresh(mixed, 64)
assert run(["mke2fs", "-q", "-F", "-t", "ext3", "-b", "4096", mixed]).returncode == 0
debugfs_w(mixed, ["write %s old" % src, "feature extent", "write %s new" % src])
clean_row("mixed", mixed)


# --- damage, each on a copy; e2fsck must call it damage, fsck.ext2 must name it
def damage(name, fn, ino_name, img_path=base, finding=None):
    copy = WORK / f"damage-{name}.img"
    shutil.copyfile(img_path, copy)
    im = Image(copy)
    try:
        ino = fn(im)
    except (IndexError, KeyError, TypeError, ValueError) as e:
        row(f"damage-{name}", False, f"the fixture cannot carry this damage ({e}); root depths {depths}")
        return
    im.save(copy)
    before = digest(copy)
    e = run(["e2fsck", "-fn", copy])
    ea = digest(copy)
    c = checker(copy, "-fn")
    out = c.stdout.decode(errors="replace")
    (WORK / f"damage-{name}.log").write_text(out)
    pattern = finding(ino) if finding else rf"[Ii]node {ino}\b[^\n]*extent"
    named = re.search(pattern, out) is not None and "unsupported: filesystem features" not in out
    # e2fsck's verdict is its exit's uncorrected bit (4): on a loop it also says 8, an operational error (exit 12).
    ok = e.returncode & 4 != 0 and c.returncode == 4 and named and ea == before and digest(copy) == before
    row(f"damage-{name}", ok, f"inode {ino} ({ino_name}): e2fsck -fn exit {e.returncode}, fsck.ext2 -fn exit {c.returncode}{', named' if named else ', no finding naming the inode and its extent tree'}{'' if digest(copy) == before else ', the copy changed'}")


def leaf_entry(im, ino, k=0, entry=0):
    return im.leaves(ino)[k] + 12 + 12 * entry


A, SIX, MANY = INO["a"], INO["six"], INO["many"]


def first_index(im, ino):
    return next(at for (at, d) in im.nodes(ino) if d > 0)


def child_of(im, at, e=0):
    o = at + 12 + 12 * e
    return ((im.u(o + 8, 2) << 32) | im.u(o + 4)) * 4096


damage("bad-magic", lambda im: (im.put(im.ino(A) + 40, 0x1234, 2), A)[1], "a")
# A depth over five (the documented maximum) in the root. (A leaf whose own depth disagrees with its parent's is
# not damage to e2fsck: -fn exits 0 on it, the rows take of 2026-11-23, so it is no row here.)
damage("bad-depth", lambda im: (im.put(im.ino(SIX) + 40 + 6, 6, 2), SIX)[1], "six")
damage("bad-max", lambda im: (im.put(im.ino(A) + 40 + 4, 5, 2), A)[1], "a")
damage("entries-over-max", lambda im: (im.put(im.ino(A) + 40 + 2, 5, 2), A)[1], "a")
damage("overlap", lambda im: (im.put(leaf_entry(im, SIX, 0, 1), im.u(leaf_entry(im, SIX, 0, 0))), SIX)[1], "six")


def unsorted(im):
    a, b = leaf_entry(im, SIX, 0, 0), leaf_entry(im, SIX, 0, 1)
    x, y = bytes(im.b[a:a + 12]), bytes(im.b[b:b + 12])
    im.b[a:a + 12], im.b[b:b + 12] = y, x
    return SIX


damage("unsorted", unsorted, "six")


def index_order(im):
    # many's root holds one index entry (debugfs's tree, depth 2); the index block below it holds several.
    at = next((a for (a, d) in im.nodes(MANY) if d > 0 and im.u(a + 2, 2) >= 2), None)
    if at is None:
        raise ValueError("no index node of many's holds two entries")
    a, b = at + 12, at + 24
    x, y = bytes(im.b[a:a + 4]), bytes(im.b[b:b + 4])
    im.b[a:a + 4], im.b[b:b + 4] = y, x
    return MANY


damage("index-order", index_order, "many")


def loop(im):
    nodes = im.nodes(MANY)
    inner = next((at for (at, d) in nodes[1:] if d > 0), None)
    if inner is None:
        raise ValueError("many has no index block below its root")
    im.put(inner + 12 + 4, inner // 4096)
    im.put(inner + 12 + 8, 0, 2)
    return MANY


damage("loop", loop, "many")
damage("out-of-range", lambda im: (im.put(leaf_entry(im, SIX) + 8, im.blocks + 10), SIX)[1], "six")
damage("over-metadata", lambda im: (im.put(leaf_entry(im, SIX) + 8, im.table(0)), SIX)[1], "six")
damage("zero-length", lambda im: (im.put(leaf_entry(im, SIX) + 4, 0, 2), SIX)[1], "six")


def shared(im):
    # six's first leaf named by an index of many's whose children are leaves: one tree block claimed twice.
    at = next(a for (a, d) in im.nodes(MANY) if d == 1)
    leaf = im.leaves(SIX)[0] // 4096
    im.put(at + 12 + 4, leaf)
    im.put(at + 12 + 8, 0, 2)
    return MANY


damage("shared-leaf", shared, "many")
# Not tree damage: its finding is the counted i_blocks (repair-i_blocks-wrong holds its repair to e2fsck's).
damage("i_blocks-wrong", lambda im: (im.put(im.ino(A) + 28, im.u(im.ino(A) + 28) + 8), A)[1], "a",
       finding=lambda ino: rf"Inode {ino}: i_blocks should be")
plain = WORK / "plain-ext3.img"
fresh(plain, 64)
assert run(["mke2fs", "-q", "-F", "-t", "ext3", "-b", "4096", plain]).returncode == 0
debugfs_w(plain, ["write %s f" % small])
FINO = inode_of(plain, "f")
damage("flag-without-feature", lambda im: (im.put(im.ino(FINO) + 32, im.u(im.ino(FINO) + 32) | EXTENTS_FL), FINO)[1], "f on ext3", plain)


# --- repairs of damage no tree holds: fsck.ext2 -fy's bytes against e2fsck -fy's
def repair(name, fn):
    oracle_img, wolf_img = WORK / f"repair-{name}.oracle.img", WORK / f"repair-{name}.wolf.img"
    shutil.copyfile(base, oracle_img)
    im = Image(oracle_img)
    fn(im)
    im.save(oracle_img)
    shutil.copyfile(oracle_img, wolf_img)
    ep = run(["e2fsck", "-fy", oracle_img])
    wp = checker(wolf_img, "-fy")
    vp = run(["e2fsck", "-fn", wolf_img])
    (WORK / f"repair-{name}.log").write_bytes(wp.stdout)
    eb, wb = oracle_img.read_bytes(), wolf_img.read_bytes()
    diffs = [i for i in range(len(eb)) if eb[i] != wb[i] and not (1072 <= i < 1078 or 1088 <= i < 1092)]
    ok = ep.returncode == wp.returncode and vp.returncode == 0 and not diffs and "unsupported" not in wp.stdout.decode(errors="replace")
    row(f"repair-{name}", ok, f"e2fsck -fy exit {ep.returncode}, fsck.ext2 -fy exit {wp.returncode}, then e2fsck -fn {vp.returncode}; {len(diffs)} bytes differ outside the time fields")


def first_data(im, ino):
    return im.u(leaf_entry(im, ino) + 8)


repair("block-bit-cleared", lambda im: im.b.__setitem__(im.u(4096) * 4096 + first_data(im, A) // 8, im.b[im.u(4096) * 4096 + first_data(im, A) // 8] & ~(1 << first_data(im, A) % 8)))
repair("inode-bit-cleared", lambda im: im.b.__setitem__(im.u(4096 + 4) * 4096 + (A - 1) // 8, im.b[im.u(4096 + 4) * 4096 + (A - 1) // 8] & ~(1 << (A - 1) % 8)))
repair("free-count", lambda im: im.put(im.sb + 12, im.u(im.sb + 12) + 1))
repair("i_blocks-wrong", lambda im: im.put(im.ino(A) + 28, im.u(im.ino(A) + 28) + 8))

# lost+found's entry dropped from the root (corpus.py's missing-lost-found, on this base: debugfs rmdir left it in
# place, the head take of 2026-11-23): e2fsck -fn must call the copy damaged; fsck.ext2 -fy makes lost+found again
# (an indirect map: no tree writer) and e2fsck -fn is clean after.
def drop_entry(im, name):
    at = im.u(leaf_entry(im, 2) + 8) * 4096
    o = 0
    while o < 4096:
        ino, rec, nl = im.u(at + o), im.u(at + o + 4, 2), im.b[at + o + 6]
        if ino and bytes(im.b[at + o + 8:at + o + 8 + nl]) == name.encode():
            im.put(at + o, 0)
            return
        o += rec or 4096
    raise ValueError("no entry " + name + " in the root's first block")


lf = WORK / "repair-lost-found.img"
shutil.copyfile(base, lf)
im = Image(lf)
drop_entry(im, "lost+found")
im.save(lf)
ep = run(["e2fsck", "-fn", lf])
wp = checker(lf, "-fy")
vp = run(["e2fsck", "-fn", lf])
(WORK / "repair-lost-found.log").write_bytes(wp.stdout)
row("repair-lost-found", ep.returncode & 4 != 0 and wp.returncode in (1, 2) and vp.returncode == 0 and inode_of(lf, "lost+found") is not None,
    f"lost+found's entry dropped: e2fsck -fn exit {ep.returncode} on the copy; fsck.ext2 -fy exit {wp.returncode} makes it again; e2fsck -fn exit {vp.returncode} after")


# --- repairs that would change an extent tree: refused by name, the copy unchanged
def refused(name, fn, ino_name):
    copy = WORK / f"refused-{name}.img"
    shutil.copyfile(base, copy)
    im = Image(copy)
    ino = fn(im)
    im.save(copy)
    before = digest(copy)
    oracle_copy = WORK / f"refused-{name}.oracle.img"
    shutil.copyfile(copy, oracle_copy)
    ep = run(["e2fsck", "-fy", oracle_copy])
    c = checker(copy, "-fy")
    out = c.stdout.decode(errors="replace")
    (WORK / f"refused-{name}.log").write_text(out)
    inos = ino if isinstance(ino, tuple) else (ino,)
    named = any(re.search(rf"unsupported: inode {i}\b[^\n]*extent tree; no repair committed", out) for i in inos)
    ok = named and digest(copy) == before and c.returncode == 4
    row(f"refused-{name}", ok, f"inode {ino} ({ino_name}): fsck.ext2 -fy exit {c.returncode}{', refused by name' if named else ', no named refusal'}, {'nothing written' if digest(copy) == before else 'the copy changed'} (e2fsck -fy exit {ep.returncode}, not compared)")


refused("cross-linked-extent", lambda im: (im.put(leaf_entry(im, INO["d"]) + 8, first_data(im, A)), (A, INO["d"]))[1], "a and d")
refused("bad-tree", lambda im: (im.put(im.ino(A) + 40, 0x1234, 2), A)[1], "a")

print(f"EXT4-FSCK: {'FAIL' if failed else 'PASS'} ({failed} failed)", flush=True)
sys.exit(1 if failed else 0)
