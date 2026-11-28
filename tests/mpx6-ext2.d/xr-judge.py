#!/usr/bin/env python3
"""The host half of tests/mpx6-ext2's extent read rows (XR): every boot's
disks, its probe plan, and every expectation, judged from the boot's log.

    xr-judge.py boots MANIFEST             one line a boot: NAME IMAGE...
    xr-judge.py plan BOOT MANIFEST         the probe's /etc/xr/plan
    xr-judge.py cmdline BOOT               the boot's kernel command line (or none)
    xr-judge.py fstab BOOT                 the boot's /etc/fstab (or none)
    xr-judge.py rootplan                   the plan the ext4 root image carries
    xr-judge.py lplan                      the Linux guest's plan: the files it makes
    xr-judge.py judge BOOT MANIFEST LOG DISKDIR TAG
                                           `PASS|FAIL XR-<row> TAG: why` lines,
                                           then XR-BOOT-END <boot> TAG rows=N failures=M

The expected bytes come from the manifest tests/mpx6-ext2.d/xr-fixture.py
wrote (each source file's recipe, held there to pinned debugfs), never from
the kernel under test. The rows assert the ext4 profile of the contract:
an explicit `ext4` mount reads extent trees read-only; ext2 and ext3 asks
keep today's refusal; damage is EIO on its own path, never absence, a
short listing or other bytes; every unsupported feature bit and every
unclean state is refused by name; no disk is written. A mapped page whose
blocks cannot be read is noted, not judged (pax#571).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

BS = 4096
ENOENT, EIO, EACCES, ENODEV, EINVAL, EROFS = 2, 5, 13, 19, 22, 30
DEVS = ["vda", "vdb", "vdc", "vdd"]
POINTS = ["/mnt", "/mnt2", "/mnt3", "/mnt4"]
LEGACY = "ext2: refused: vda: unsupported optional features (40): s_feature_incompat extent"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Sources:
    """Expected bytes of P's files, rebuilt from their recipes."""

    def __init__(self, recipes):
        self.r = recipes

    def size(self, rel):
        kind, v = self.r[rel]["kind"], self.r[rel]["value"]
        return {"bytes": lambda: len(bytes.fromhex(v)), "blocks": lambda: v * BS,
                "pattern": lambda: (v * 2 - 1) * BS, "big": lambda: 5 << 30}[kind]()

    def range(self, rel, off, n):
        kind, v = self.r[rel]["kind"], self.r[rel]["value"]
        end = min(off + n, self.size(rel))
        if end <= off:
            return b""
        if kind == "bytes":
            return bytes.fromhex(v)[off:end]
        out = bytearray(end - off)
        if kind == "big":
            block = bytes(range(256)) * 16
            for at in v:
                lo, hi = max(at, off), min(at + BS, end)
                if lo < hi:
                    out[lo - off:hi - off] = block[lo - at:hi - at]
            return bytes(out)
        for b in range(off // BS, (end - 1) // BS + 1):
            if kind == "blocks":
                fill = b % 251 + 1
            else:  # pattern: run n at block 2n, a hole between
                fill = (b // 2) % 251 + 1 if b % 2 == 0 else 0
            lo, hi = max(b * BS, off), min((b + 1) * BS, end)
            out[lo - off:hi - off] = bytes([fill]) * (hi - lo)
        return bytes(out)

    def whole(self, rel):
        return self.range(rel, 0, self.size(rel))


# --- the boots ---------------------------------------------------------------------

def boots(m):
    out = [("map", [m["P"]["image"], m["U"]["image"]]), ("multi", [m["M"]["image"]]),
           ("damage", [m["Q"]["image"], m["K"]["image"]])]
    feats = [("F-base", m["F"]["base"]["image"])] + [(k, v["image"]) for k, v in sorted(m["F"]["cases"].items())]
    for i in range(0, len(feats), 4):
        out.append((f"feat-{i // 4}", [img for _n, img in feats[i:i + 4]]))
    states = [("J-clean", m["J"]["clean"]["image"])] + [(k, v["image"]) for k, v in sorted(m["J"]["cases"].items())]
    for i in range(0, len(states), 4):
        out.append((f"state-{i // 4}", [img for _n, img in states[i:i + 4]]))
    out += [("fstab", [m["J"]["clean"]["image"]]), ("root", [m["R"]["image"]]), ("notype", [m["R"]["image"]]),
            ("rootbad", [m["R"]["image"]]), ("default", [m["D"]["image"]])]
    if "W" in m:
        out.append(("linux", [m["W"]["image"]]))
    return out


# Each boot's kernel command line and /etc/fstab, where it has one.
CMDLINES = {"root": "root=/dev/vda rootfstype=ext4", "notype": "root=/dev/vda",
            "rootbad": "root=/dev/vda rootfstype=btrfs"}
FSTABS = {"fstab": ["/dev/vda /mnt ext4 defaults 0 0", "/dev/vdb /mnt2 btrfs ro 0 0"]}

# The plan the ext4 root image carries in /etc/xr/plan (xr-fixture.py's R
# set writes it there; the initramfs carries it too, for the boots that keep
# the initramfs as `/`).
ROOT_PLAN = ["mounts root", "file /small", "file /six", "list /", "tries /"]
TRIES = ("create", "open-write", "truncate", "chmod", "utimens", "rename", "unlink", "mkdir", "symlink", "link",
         "mmap-shared-write")

# The files the Linux guest makes on a fresh image of the profile, and reads
# back itself: block k of a file holds (SEED * 7 + k) % 251 + 1.
LONG_TARGET = "ld/" + "a-long-link-target-" * 4
LINUX_READS = ["file /mnt/lcontig", "file /mnt/lsparse", "file /mnt/lfalloc", "file /mnt/ld/n000",
               "file /mnt/ld/n299", "readlink /mnt/lfast", "readlink /mnt/lslow", "list /mnt/ld", "stat /mnt/lsparse"]


def lplan():
    lines = ["mkdir /mnt/ld", "wblocks /mnt/lcontig 300 1", "wsparse /mnt/lsparse 1500 2", "falloc /mnt/lfalloc 3"]
    lines += [f"wtext /mnt/ld/n{k:03d} n{k:03d}" for k in range(300)]
    lines += ["symlink lcontig /mnt/lfast", f"symlink {LONG_TARGET} /mnt/lslow"]
    return lines + LINUX_READS


def lbytes(path):
    """What the Linux guest wrote at `path`, from lplan's recipe."""
    blk = lambda seed, k: bytes([(seed * 7 + k) % 251 + 1]) * BS
    if path == "/mnt/lcontig":
        return b"".join(blk(1, k) for k in range(300))
    if path == "/mnt/lsparse":
        return b"".join(blk(2, k // 2) if k % 2 == 0 else bytes(BS) for k in range(2 * 1500 - 1))
    if path == "/mnt/lfalloc":
        return b"".join(blk(3, k) for k in range(4)) + bytes(8 * BS) + blk(3, 12)
    if path.startswith("/mnt/ld/n"):
        return path[len("/mnt/ld/"):].encode() + b"\n"
    raise KeyError(path)


class Plan:
    """Plan lines, each with the row that judges it."""

    def __init__(self):
        self.lines, self.checks = [], []

    def op(self, line, row=None, check=None, needs=None):
        """`needs`: a row that must have passed first, so this one cannot pass
        for the wrong reason (an ENOENT because nothing was mounted)."""
        self.lines.append(line)
        if row:
            self.checks.append((row, line, len([l for l in self.lines if l == line]) - 1, check, needs))

    def watch(self, key, row, check, needs=None):
        """A row on an observation a plan line makes under another key (a
        pair's children say `pair-a PATH` and `pair-b PATH`)."""
        self.checks.append((row, key, 0, check, needs))


def ok_rc(rc, errno):
    return lambda o: (o["rc"] == rc and o["errno"] == errno, f"rc={o['rc']} errno={o['errno']} (want {rc}/{errno})")


def ok_bytes(data):
    want = digest(data)
    return lambda o: (o["rc"] == 0 and o.get("bytes") == str(len(data)) and o.get("sha256") == want,
                      f"rc={o['rc']} errno={o['errno']} bytes={o.get('bytes')} (want {len(data)}) "
                      f"sha256 {'equal' if o.get('sha256') == want else 'differs'}")


def ok_eio():
    return lambda o: (o["rc"] == -1 and o["errno"] == EIO,
                      f"rc={o['rc']} errno={o['errno']} at={o.get('at', '-')} (want EIO, never other bytes or ENOENT)")


def plan_map(m):
    p, src = Plan(), Sources(m["P"]["sources"])
    p.op("mount /dev/vda /mnt ext2 ro", "XR-type-ext2-refused", ok_rc(-1, EINVAL))
    p.op("mount /dev/vda /mnt ext3 ro", "XR-type-ext3-refused", ok_rc(-1, EINVAL))
    p.op("mount /dev/vda /mnt ext4 rw", "XR-ro-rw-ask", ok_rc(0, 0))
    p.op("mounts rw-ask")
    p.op("umount /mnt", "XR-ro-rw-ask-umount", ok_rc(0, 0))
    p.op("mount /dev/vda /mnt ext4 ro", "XR-type-mount", ok_rc(0, 0))
    p.op("mounts ro")
    for rel, row in (("empty", "XR-empty"), ("small", "XR-small"), ("long", "XR-map-0"), ("six", "XR-map-1"),
                     ("many", "XR-map-2")):
        p.op(f"file /mnt/{rel}", row, ok_bytes(src.whole(rel)))
    reads = {"six": [(4095, 2), (8191, 2), (5 * BS + 100, 9000), (10 * BS, BS), (11 * BS - 10, 100), (0, 11 * BS)],
             "many": [(678 * BS + 4000, 3 * BS), (1360 * BS - 5, 10), (2040 * BS - 7, 3 * BS), (2998 * BS, BS),
                      (2999 * BS - 1, 50)],
             "long": [(1024 * BS - 7, 14), (2049 * BS - 3, 10)],
             "big": [(0, BS), (BS, BS), ((4 << 30) + 8192, BS), (4 << 30, BS), ((5 << 30) - BS - 2, 4),
                     ((5 << 30) - 1, 10), (5 << 30, 10)]}
    rows = {"six": "XR-map-1-ranges", "many": "XR-map-2-ranges", "long": "XR-map-0-ranges", "big": "XR-large"}
    for rel, spans in reads.items():
        for i, (off, n) in enumerate(spans):
            p.op(f"read /mnt/{rel} {off} {n}", f"{rows[rel]}-{i}", ok_bytes(src.range(rel, off, n)))
    p.op("stat /mnt/big", "XR-large-size", lambda o: (o["rc"] == 0 and o.get("size") == str(5 << 30), f"size={o.get('size')}"))
    p.op("stat /mnt/six", "XR-stat-file", lambda o: (o["rc"] == 0 and o.get("size") == str(11 * BS)
                                                     and o.get("mode", "").startswith("100"), f"mode={o.get('mode')} size={o.get('size')}"))
    p.op("stat /mnt/d", "XR-stat-dir", lambda o: (o["rc"] == 0 and o.get("mode", "").startswith("40"), f"mode={o.get('mode')}"))
    names = m["P"]["files"]["d"]["names"]
    p.op("list /mnt/d", "XR-dir-list", lambda o, names=names: (o["rc"] == 0 and o["names"] == names,
                                                                 f"rc={o['rc']} errno={o['errno']} {len(o['names'])} names (want {len(names)})"))
    top = sorted({r.split("/")[0] for r in m["P"]["sources"]})
    p.op("list /mnt", "XR-root-list", lambda o, top=top: (
        o["rc"] == 0 and set(top) <= set(o["names"]) and set(o["names"]) - set(top) <= {"lost+found"},
        f"rc={o['rc']} names {o['names']}"))
    for k in ("n000", "n299", "n300", "n599"):
        p.op(f"file /mnt/d/{k}", f"XR-dir-lookup-{k}", ok_bytes(src.whole("d/" + k)))
    p.op("stat /mnt/d/absent", "XR-dir-absent", ok_rc(-1, ENOENT), needs="XR-dir-list")
    p.op("file /mnt/d/sub/deep.txt", "XR-dir-nested", ok_bytes(src.whole("d/sub/deep.txt")))
    for rel, row in (("fl", "XR-fastlink"), ("sl", "XR-slowlink")):
        t = src.r[rel]["value"]
        p.op(f"readlink /mnt/{rel}", row, lambda o, t=t: (o["rc"] == 0 and o.get("target") == t and o.get("len") == str(len(t)),
                                                         f"rc={o['rc']} errno={o['errno']} target={o.get('target')}"))
    p.op("file /mnt/fl", "XR-fastlink-follow", ok_bytes(src.whole("small")))
    want = digest(src.whole("six"))
    p.op(f"mmap /mnt/six {11 * BS}", "XR-mmap", lambda o, want=want: (
        o["rc"] == 0 and o.get("exit") == "0" and o.get("mmap_sha256") == want,
        f"exit={o.get('exit')} signal={o.get('signal')} bytes {'equal' if o.get('mmap_sha256') == want else 'differ'}"))
    p.op("tries /mnt")
    p.op("remount /mnt", "XR-ro-remount", ok_rc(-1, EROFS))
    # Past the cache's 512 buffers: many's 1500 runs, the directory, long's
    # 2049 blocks, then many and a name again, every byte right.
    p.op("file /mnt/many", "XR-cache-many-first", ok_bytes(src.whole("many")))
    p.op("list /mnt/d", "XR-cache-list", lambda o, names=names: (o["rc"] == 0 and o["names"] == names,
                                                                  f"rc={o['rc']} errno={o['errno']} {len(o['names'])} names"))
    p.op("file /mnt/long", "XR-cache-long", ok_bytes(src.whole("long")))
    p.op("file /mnt/many", "XR-cache-many-again", ok_bytes(src.whole("many")))
    p.op("file /mnt/d/n599", "XR-cache-lookup", ok_bytes(src.whole("d/n599")))
    # Two readers released together (on separate processors when the boot
    # has them): each one's bytes right.
    p.op("pair /mnt/many /mnt/long", "XR-smp-pair", lambda o: (o["rc"] == 0 and o.get("exits") == "0,0",
                                                              f"rc={o['rc']} exits={o.get('exits')}"),
         needs="XR-type-mount")
    p.watch("pair-a /mnt/many", "XR-smp-pair-a", ok_bytes(src.whole("many")))
    p.watch("pair-b /mnt/long", "XR-smp-pair-b", ok_bytes(src.whole("long")))
    p.op("mount /dev/vdb /mnt2 ext4 ro", "XR-unwritten-mount", ok_rc(0, 0))
    u = m["U"]
    p.op("file /mnt2/six", "XR-unwritten", lambda o, u=u: (
        o["rc"] == 0 and o.get("bytes") == str(u["six_bytes"]) and o.get("sha256") == u["six_sha256"],
        f"rc={o['rc']} bytes={o.get('bytes')} sha256 {'equal' if o.get('sha256') == u['six_sha256'] else 'differs (unwritten bytes must read as zeros)'}"))
    lo = u["edit"]["logical"] * BS
    p.op(f"read /mnt2/six {lo - 1} {BS + 2}", "XR-unwritten-range", ok_bytes(bytes(BS + 2)))
    p.op("file /mnt2/many", "XR-unwritten-neighbors", ok_bytes(src.whole("many")))
    p.op("umount /mnt2", "XR-umount-mnt2", ok_rc(0, 0))
    p.op("umount /mnt", "XR-umount-mnt", ok_rc(0, 0))
    return p


def plan_multi(m):
    """Two groups: group 1's superblock and descriptor copies, bitmaps and
    table sit where the layout says, and a file there reads back whole."""
    p = Plan()
    f = m["M"]["files"]
    whole = lambda rel: (lambda o: (o["rc"] == 0 and o.get("sha256") == f[rel]["sha256"] and o.get("bytes") == str(f[rel]["bytes"]),
                                    f"rc={o['rc']} errno={o['errno']} bytes={o.get('bytes')} sha256 {'equal' if o.get('sha256') == f[rel]['sha256'] else 'differs'}"))
    p.op("mount /dev/vda /mnt ext4 ro", "XR-multigroup-mount", ok_rc(0, 0))
    p.op("file /mnt/b-far", "XR-multigroup-far", whole("b-far"))
    p.op("file /mnt/a-fill", "XR-multigroup-fill", whole("a-fill"))
    p.op("umount /mnt", "XR-multigroup-umount", ok_rc(0, 0))
    return p


def plan_damage(m):
    p = Plan()
    q = m["Q"]
    f = q["base"]["files"]
    six = lambda o, rel: (o["rc"] == 0 and o.get("sha256") == f[rel]["sha256"],
                          f"rc={o['rc']} errno={o['errno']} sha256 {'equal' if o.get('sha256') == f[rel]['sha256'] else 'differs'}")
    p.op("mount /dev/vda /mnt ext4 ro", "XR-damage-mount", ok_rc(0, 0))
    p.op("file /mnt/c-before", "XR-damage-control-before", lambda o: six(o, "c-before"))
    # An eh_max one or two under its node's room is no damage: pinned e2fsck
    # accepts exactly the room and the two values under it at rooms 4, 84 and
    # 340, whatever the entry count, and the Linux guest reads them whole.
    # Past the room (v-maxover) or three and more under it (v-max1,
    # m-idx-337, m-idx-max) is refused.
    reads = {"v-max": "XR-eh_max-under-room", "v-max2": "XR-eh_max-root-2-under",
             "m-idx-338": "XR-eh_max-block-2-under"}
    for rel in sorted(k for k in q["edit"] if k.startswith(("v-", "m-", "f-")) and k not in reads):
        p.op(f"file /mnt/{rel}", f"XR-damage-{rel[2:]}", ok_eio())
    for rel, row in reads.items():
        p.op(f"file /mnt/{rel}", row, lambda o, rel=rel: six(o, rel))
    p.op("list /mnt/d-out", "XR-dir-eio-list-out", ok_eio())
    p.op("stat /mnt/d-out/n000", "XR-dir-eio-lookup-out", ok_eio())
    p.op("list /mnt/d-hole", "XR-dir-eio-list-hole", ok_eio())
    p.op("stat /mnt/d-hole/n599", "XR-dir-eio-lookup-hole", ok_eio())
    p.op("stat /mnt/d-hole/absent", "XR-dir-eio-absent", ok_eio())
    p.op("readlink /mnt/s-bad", "XR-link-eio", ok_eio())
    # A mapped page whose blocks cannot be read maps as zeros, on ext4 as on
    # ext2 and ext3 (pax#571; Linux answers SIGBUS). Observed and noted here,
    # never a row, until that change lands with rows of its own.
    p.op(f"mmap /mnt/v-pastend {11 * BS}")
    p.op("file /mnt/c-after", "XR-damage-control-after", lambda o: six(o, "c-after"))
    p.op("umount /mnt", "XR-damage-umount", ok_rc(0, 0))
    # K: an extent volume of 1 KiB blocks, whose leaf room is 84.
    kf = m["K"]["files"]
    kread = lambda o, rel: (o["rc"] == 0 and o.get("sha256") == kf[rel]["sha256"],
                            f"rc={o['rc']} errno={o['errno']} sha256 {'equal' if o.get('sha256') == kf[rel]['sha256'] else 'differs'}")
    p.op("mount /dev/vdb /mnt2 ext4 ro", "XR-1k-mount", ok_rc(0, 0))
    p.op("file /mnt2/k-control", "XR-1k-control", lambda o: kread(o, "k-control"))
    p.op("file /mnt2/k-max82", "XR-eh_max-1k-2-under", lambda o: kread(o, "k-max82"))
    p.op("file /mnt2/k-max81", "XR-damage-1k-3-under", ok_eio(), needs="XR-1k-control")
    p.op("umount /mnt2", "XR-1k-umount", ok_rc(0, 0))
    return p


def feature_name(image):
    return image[len("F-"):-len(".img")]


def plan_disks(m, images, kind):
    p = Plan()
    for dev, point, image in zip(DEVS, POINTS, images):
        if image in (m["F"]["base"]["image"], m["J"]["clean"]["image"]):
            row = "XR-type-nojournal" if kind == "feat" else "XR-journal-clean"
            p.op(f"mount /dev/{dev} {point} ext4 ro", row, ok_rc(0, 0))
            p.op(f"file {point}/a", row + "-read", ok_bytes(b"a\n"))
            p.op(f"umount {point}", row + "-umount", ok_rc(0, 0))
            continue
        name = feature_name(image) if kind == "feat" else image[len("J-"):-len(".img")]
        prefix = "XR-feature-" if kind == "feat" else "XR-state-"
        for how in ("ro", "rw"):
            p.op(f"mount /dev/{dev} {point} ext4 {how}", f"{prefix}{name}-{how}", ok_rc(-1, EINVAL))
    return p


def whole_of(files, rel):
    return lambda o: (o["rc"] == 0 and o.get("sha256") == files[rel]["sha256"] and o.get("bytes") == str(files[rel]["bytes"]),
                      f"rc={o['rc']} errno={o['errno']} bytes={o.get('bytes')} "
                      f"sha256 {'equal' if o.get('sha256') == files[rel]['sha256'] else 'differs'}")


def plan_fstab(m):
    """fstab names `ext4` for the clean journalled image, asked read-write;
    a btrfs line is refused by name before its device is looked for."""
    p = Plan()
    p.op("mounts fstab")
    p.op("file /mnt/a", "XR-type-fstab-read", ok_bytes(b"a\n"))
    return p


def plan_root(m):
    """`/` is the ext4 image itself (root=/dev/vda rootfstype=ext4): its own
    probe reads ROOT_PLAN from it."""
    p = Plan()
    f = m["R"]["files"]
    for line in ROOT_PLAN:
        if line == "file /small":
            p.op(line, "XR-root-small", whole_of(f, "small"))
        elif line == "file /six":
            p.op(line, "XR-root-six", whole_of(f, "six"))
        elif line == "list /":
            want = {"small", "six", "bin", "etc", "mnt", "proc", "dev", "sys", "tmp"}
            p.op(line, "XR-root-list", lambda o, want=want: (o["rc"] == 0 and want <= set(o["names"]),
                                                              f"rc={o['rc']} names {o['names']}"))
        else:
            p.op(line)
    return p


def plan_kept(m):
    """A root refused as asked: `/` stays the initramfs, whose probe says only
    what is mounted."""
    p = Plan()
    p.op("mounts kept")
    return p


def plan_default(m):
    """A default `mke2fs -t ext4` image: refused, read-only or read-write
    asked, naming every incompat bit outside the profile."""
    p = Plan()
    for how in ("ro", "rw"):
        p.op(f"mount /dev/vda /mnt ext4 {how}", f"XR-type-default-{how}", ok_rc(-1, EINVAL))
    return p


def plan_linux(m):
    """The files the Linux guest made on a fresh image of the profile: PAX
    reads every byte and attribute as Linux read them, and as lplan wrote."""
    p = Plan()
    w = m["W"]
    p.op("mount /dev/vda /mnt ext4 ro", "XR-linux-mount", ok_rc(0, 0))
    for line in LINUX_READS:
        row = "XR-linux-" + line.split()[0] + "-" + line.split()[-1].rsplit("/", 1)[-1]
        seen = (w.get("linux") or {}).get(line)

        def check(o, line=line, seen=seen):
            if seen is None:
                return False, "Linux left no observation of this line"
            path = line.split()[-1]
            if line.startswith("file "):
                data = lbytes(path)
                ok = (o["rc"] == 0 and o.get("sha256") == seen.get("sha256") == digest(data)
                      and o.get("bytes") == seen.get("bytes") == str(len(data)))
                return ok, f"PAX bytes={o.get('bytes')} sha256 {o.get('sha256', '-')[:16]}; Linux {seen.get('bytes')} {seen.get('sha256', '-')[:16]}; written {len(data)} {digest(data)[:16]}"
            if line.startswith("readlink "):
                want = "lcontig" if path.endswith("lfast") else LONG_TARGET
                ok = o["rc"] == 0 and o.get("target") == seen.get("target") == want
                return ok, f"PAX {o.get('target')}; Linux {seen.get('target')}"
            if line.startswith("list "):
                want = sorted(f"n{k:03d}" for k in range(300))
                ok = o["rc"] == 0 and o["names"] == seen.get("names") == want
                return ok, f"PAX {len(o['names'])} names, Linux {len(seen.get('names', []))}, written {len(want)}"
            ok = o["rc"] == 0 and o.get("size") == seen.get("size") == str((2 * 1500 - 1) * BS)
            return ok, f"PAX size={o.get('size')}; Linux {seen.get('size')}"

        p.op(line, row, check, needs="XR-linux-mount")
    p.op("umount /mnt", "XR-linux-umount", ok_rc(0, 0))
    return p


def plan_for(boot, m):
    for name, images in boots(m):
        if name == boot:
            if boot == "map":
                return plan_map(m), images
            if boot == "damage":
                return plan_damage(m), images
            if boot == "multi":
                return plan_multi(m), images
            if boot == "fstab":
                return plan_fstab(m), images
            if boot == "root":
                return plan_root(m), images
            if boot in ("notype", "rootbad"):
                return plan_kept(m), images
            if boot == "default":
                return plan_default(m), images
            if boot == "linux":
                return plan_linux(m), images
            return plan_disks(m, images, boot.split("-")[0]), images
    raise SystemExit(f"no boot {boot}")


# --- judging -------------------------------------------------------------------------

def observations(lines):
    """Each plan line's observations in order, parsed."""
    obs, ents, mounts = {}, {}, {}
    mm = {}
    for l in lines:
        if not l.startswith("XRO "):
            continue
        body = l[4:]
        if body.startswith("ent "):
            _e, d, name = body.split(" ", 2)
            ents.setdefault(d, []).append(name)
            continue
        if body.startswith(("mounts ", "mountinfo ")):
            kind, tag, rest = (body.split(" ", 2) + [""])[:3]
            mounts.setdefault((kind, tag), []).append(rest)
            continue
        if body.startswith("mmap-bytes "):
            _k, path, h = body.split(" ", 2)
            mm[path] = h.split("=", 1)[1]
            continue
        g = re.match(r"(.*?) rc=(-?\d+) errno=(\d+)(.*)$", body)
        if not g:
            continue
        o = {"rc": int(g[2]), "errno": int(g[3])}
        rest = g[4].strip()
        t = re.search(r"\btarget=(.*)$", rest)
        if t:
            o["target"] = t[1]
            rest = rest[:t.start()]
        o.update(dict(kv.split("=", 1) for kv in rest.split() if "=" in kv))
        key = g[1]
        if key.startswith("list "):
            o["names"] = sorted(ents.pop(key[5:], []))
        if key.startswith("mmap ") and key.split()[1] in mm:
            o["mmap_sha256"] = mm.pop(key.split()[1])
        obs.setdefault(key, []).append(o)
    return obs, mounts


def judge(boot, m, log, diskdir, tag):
    plan, images = plan_for(boot, m)
    text = Path(log).read_text(errors="replace").splitlines()
    obs, mounts = observations(text)
    results = []

    def row(name, ok, why):
        results.append((name, ok, why))

    passed = {}
    for name, line, k, check, needs in plan.checks:
        got = obs.get(line, [])
        if k >= len(got):
            ok, why = False, "no observation (the probe did not reach it)"
        else:
            ok, why = check(got[k])
        if needs and not passed.get(needs, False):
            ok, why = False, f"needs {needs}, which did not pass; {why}"
        passed[name] = ok
        row(name, ok, f"'{line}': {why}")
    if boot == "map":
        for kind, listing, pattern, name in (
                ("mounts", "rw-ask", r"^/dev/vda /mnt ext4 ro[, ]", "XR-ro-rw-ask-mounted-ro"),
                ("mounts", "ro", r"^/dev/vda /mnt ext4 ro[, ]", "XR-type-mounts"),
                ("mountinfo", "ro", r" - ext4 /dev/vda ro\b", "XR-type-mountinfo")):
            seen = mounts.get((kind, listing), [])
            row(name, any(re.search(pattern, s) for s in seen), f"{kind} {listing}: {[s for s in seen if 'vda' in s]}")
        n = text.count(LEGACY)
        row("XR-type-legacy-line", n == 2, f"{n} x today's ext2/ext3 refusal line (want 2: the ext2 and ext3 asks, none for ext4)")
        tries = {tuple(l[4:].split()[1:3]): l for l in text if l.startswith("XRO try ")}
        for t in ("create", "open-write", "truncate", "chmod", "utimens", "rename", "unlink", "mkdir", "symlink", "link",
                  "mmap-shared-write"):
            l = tries.get(("/mnt", t), "")
            g = re.search(r"rc=(-?\d+) errno=(\d+)", l)
            want = (EROFS, EACCES) if t == "mmap-shared-write" else (EROFS,)
            row(f"XR-ro-{t}", bool(g) and g[1] == "-1" and int(g[2]) in want, l[4:] if l else "no observation")
    if boot.startswith(("feat-", "state-")):
        for dev, image in zip(DEVS, images):
            if image in (m["F"]["base"]["image"], m["J"]["clean"]["image"]):
                continue
            lines = [l for l in text if l.startswith(f"ext2: refused: {dev}: ")]
            if boot.startswith("feat-"):
                name = feature_name(image)
                token = name.split("-0x")[1] if "-0x" in name else name
                hit = [l for l in lines if re.search(r"(?<![\w])" + re.escape(token) + r"(?![\w])", l)]
                row(f"XR-feature-{name}-named", len(hit) == 2, f"{len(hit)} refusal lines for {dev} naming {token} (want 2): {lines[:1]}")
            else:
                name = image[len("J-"):-len(".img")]
                word = "journal" if name.startswith("journal") else "offline"
                hit = [l for l in lines if word in l]
                row(f"XR-state-{name}-named", len(hit) == 2, f"{len(hit)} refusal lines for {dev} saying '{word}' (want 2): {lines[:1]}")
    said = lambda pattern: [l for l in text if re.search(pattern, l)]
    if boot == "fstab":
        hit = said(r"^fstab: /dev/vda( \(vda\))? on /mnt: ext4, read-only")
        row("XR-type-fstab-line", len(hit) == 1, f"{hit[:1]} (want one `fstab: /dev/vda on /mnt: ext4, read-only` line)")
        hit = said(r"^ext2: vda: an extent volume, mounted read-only")
        row("XR-type-fstab-said", len(hit) == 1, f"{hit[:1]} (want the read-write ask said mounted read-only)")
        seen = mounts.get(("mounts", "fstab"), [])
        row("XR-type-fstab-mounts", any(re.search(r"^/dev/vda /mnt ext4 ro[, ]", x) for x in seen),
            f"mounts: {[x for x in seen if 'vda' in x]}")
        hit = said(r"^fstab: refused: /dev/vdb on /mnt2: a file system type PAX does not mount "
                   r"\(btrfs; ext2, ext3, ext4 and tmpfs are the ones\)")
        row("XR-type-unknown-fstab", len(hit) == 1, f"{said(r'^fstab: refused: /dev/vdb')[:1]} (want ext4 among the types named)")
    if boot == "root":
        hit = said(r"^root: /dev/vda \(vda\) on /: ext4, read-only")
        row("XR-root-line", len(hit) == 1, f"{said(r'^root: ')[:2]} (want `root: /dev/vda (vda) on /: ext4, read-only`)")
        seen = mounts.get(("mounts", "root"), [])
        row("XR-root-mounts", any(re.search(r"^/dev/root / ext4 ro[, ]", x) for x in seen), f"mounts: {seen[:3]}")
        tries = {tuple(l[4:].split()[1:3]): l for l in text if l.startswith("XRO try ")}
        for t in TRIES:
            l = tries.get(("/", t), "")
            g = re.search(r"rc=(-?\d+) errno=(\d+)", l)
            want = (EROFS, EACCES) if t == "mmap-shared-write" else (EROFS,)
            row(f"XR-root-ro-{t}", bool(g) and g[1] == "-1" and int(g[2]) in want, l[4:] if l else "no observation")
    if boot == "notype":
        hit = said(r"^root: /dev/vda: the volume did not mount; / stays the initramfs in memory$")
        row("XR-root-notype", len(hit) == 1, f"{said(r'^root: ')[:2]} (a root with no type keeps today's refusal)")
        n = text.count(LEGACY)
        row("XR-root-notype-refusal", n == 1, f"{n} x today's ext2 refusal line (want 1)")
    if boot == "rootbad":
        hit = said(r"^root: /dev/vda: rootfstype= names a file system PAX does not mount \(ext2, ext3 and ext4 are the ones\); "
                   r"/ stays the initramfs in memory$")
        row("XR-type-unknown-root", len(hit) == 1, f"{said(r'^root: ')[:2]} (want ext4 among the types named)")
    if boot == "default":
        lines = [l for l in text if l.startswith("ext2: refused: vda: ")]
        names = m["D"]["names"]
        hit = [l for l in lines if all(re.search(r"(?<![\w])" + re.escape(x) + r"(?![\w])", l) for x in names)]
        row("XR-type-default-named", len(hit) == 2, f"{len(hit)} refusal lines naming {', '.join(names)} (want 2): {lines[:1]}")
    if boot == "linux":
        w = m["W"]
        row("XR-linux-profile", bool(w.get("ok")), "; ".join(w.get("why", [])) or
            f"Linux {w.get('kernel', '?')} left the image clean, words {w.get('words')}, its shapes as asked")
    want = {m["P"]["image"]: m["P"]["sha256"], m["U"]["image"]: m["U"]["sha256"], m["Q"]["image"]: m["Q"]["sha256"],
            m["M"]["image"]: m["M"]["sha256"], m["K"]["image"]: m["K"]["sha256"],
            m["F"]["base"]["image"]: m["F"]["base"]["sha256"], m["J"]["clean"]["image"]: m["J"]["clean"]["sha256"],
            m["R"]["image"]: m["R"]["sha256"], m["D"]["image"]: m["D"]["sha256"]}
    if "W" in m:
        want[m["W"]["image"]] = m["W"]["sha256"]
    want.update({v["image"]: v["sha256"] for v in m["F"]["cases"].values()})
    want.update({v["image"]: v["sha256"] for v in m["J"]["cases"].values()})
    for image in images:
        got = file_sha(Path(diskdir) / image)
        row(f"XR-unchanged-{boot}-{image[:-4]}", got == want[image], f"sha256 {got[:16]} after the boot, {want[image][:16]} made")
    if boot == "damage":
        got = obs.get(f"mmap /mnt/v-pastend {11 * BS}", [])
        seen = (f"exit={got[0].get('exit')} signal={got[0].get('signal')}"
                f"{', it read bytes' if 'mmap_sha256' in got[0] else ''}") if got else "no observation"
        print(f"NOTE XR-damage-mmap {tag}: {seen} (pax#571: noted, not gated)", flush=True)
    end = "XRO-END" in text and "halt" in text and not any(l.startswith("PANIC") for l in text)
    row(f"XR-{boot}-end", end, "the probe ended, the kernel halted, no PANIC")
    failures = 0
    for name, ok, why in results:
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'} {name} {tag}: {why}", flush=True)
    print(f"XR-BOOT-END {boot} {tag} rows={len(results)} failures={failures}", flush=True)
    return 1 if failures else 0


def main(argv):
    if len(argv) >= 2 and argv[0] == "boots":
        for name, images in boots(json.loads(Path(argv[1]).read_text())):
            print(name, *images)
        return 0
    if len(argv) == 3 and argv[0] == "plan":
        plan, _images = plan_for(argv[1], json.loads(Path(argv[2]).read_text()))
        print("\n".join(plan.lines))
        return 0
    if len(argv) == 2 and argv[0] == "cmdline":
        print(CMDLINES.get(argv[1], ""))
        return 0
    if len(argv) == 2 and argv[0] == "fstab":
        print("\n".join(FSTABS.get(argv[1], [])))
        return 0
    if argv == ["rootplan"]:
        print("\n".join(ROOT_PLAN))
        return 0
    if argv == ["lplan"]:
        print("\n".join(lplan()))
        return 0
    if len(argv) == 6 and argv[0] == "judge":
        return judge(argv[1], json.loads(Path(argv[2]).read_text()), argv[3], argv[4], argv[5])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
