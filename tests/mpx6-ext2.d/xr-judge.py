#!/usr/bin/env python3
"""The host half of tests/mpx6-ext2's extent read rows (XR): every boot's
disks, its probe plan, and every expectation, judged from the boot's log.

    xr-judge.py boots MANIFEST             one line a boot: NAME IMAGE...
    xr-judge.py plan BOOT MANIFEST         the probe's /etc/xr/plan
    xr-judge.py judge BOOT MANIFEST LOG DISKDIR TAG
                                           `PASS|FAIL XR-<row> TAG: why` lines,
                                           then XR-BOOT-END <boot> TAG rows=N failures=M

The expected bytes come from the manifest tests/mpx6-ext2.d/xr-fixture.py
wrote (each source file's recipe, held there to pinned debugfs), never from
the kernel under test. The rows assert the ext4 profile of the contract:
an explicit `ext4` mount reads extent trees read-only; ext2 and ext3 asks
keep today's refusal; damage is EIO on its own path, never absence, a
short listing or other bytes; every unsupported feature bit and every
unclean state is refused by name; no disk is written.
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
    out = [("map", [m["P"]["image"], m["U"]["image"]]), ("damage", [m["Q"]["image"]])]
    feats = [("F-base", m["F"]["base"]["image"])] + [(k, v["image"]) for k, v in sorted(m["F"]["cases"].items())]
    for i in range(0, len(feats), 4):
        out.append((f"feat-{i // 4}", [img for _n, img in feats[i:i + 4]]))
    states = [("J-clean", m["J"]["clean"]["image"])] + [(k, v["image"]) for k, v in sorted(m["J"]["cases"].items())]
    for i in range(0, len(states), 4):
        out.append((f"state-{i // 4}", [img for _n, img in states[i:i + 4]]))
    return out


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


def plan_damage(m):
    p = Plan()
    q = m["Q"]
    f = q["base"]["files"]
    six = lambda o, rel: (o["rc"] == 0 and o.get("sha256") == f[rel]["sha256"],
                          f"rc={o['rc']} errno={o['errno']} sha256 {'equal' if o.get('sha256') == f[rel]['sha256'] else 'differs'}")
    p.op("mount /dev/vda /mnt ext4 ro", "XR-damage-mount", ok_rc(0, 0))
    p.op("file /mnt/c-before", "XR-damage-control-before", lambda o: six(o, "c-before"))
    for rel in sorted(k for k in q["edit"] if k.startswith(("v-", "m-", "f-"))):
        p.op(f"file /mnt/{rel}", f"XR-damage-{rel[2:]}", ok_eio())
    p.op("list /mnt/d-out", "XR-dir-eio-list-out", ok_eio())
    p.op("stat /mnt/d-out/n000", "XR-dir-eio-lookup-out", ok_eio())
    p.op("list /mnt/d-hole", "XR-dir-eio-list-hole", ok_eio())
    p.op("stat /mnt/d-hole/n599", "XR-dir-eio-lookup-hole", ok_eio())
    p.op("stat /mnt/d-hole/absent", "XR-dir-eio-absent", ok_eio())
    p.op("readlink /mnt/s-bad", "XR-link-eio", ok_eio())
    p.op(f"mmap /mnt/v-pastend {11 * BS}", "XR-damage-mmap", lambda o: (
        o["rc"] == 0 and o.get("exit") != "0" and "mmap_sha256" not in o,
        f"exit={o.get('exit')} signal={o.get('signal')}{' and it read bytes' if 'mmap_sha256' in o else ''}"),
         needs="XR-damage-mount")
    p.op("file /mnt/c-after", "XR-damage-control-after", lambda o: six(o, "c-after"))
    p.op("umount /mnt", "XR-damage-umount", ok_rc(0, 0))
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


def plan_for(boot, m):
    for name, images in boots(m):
        if name == boot:
            if boot == "map":
                return plan_map(m), images
            if boot == "damage":
                return plan_damage(m), images
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
    want = {m["P"]["image"]: m["P"]["sha256"], m["U"]["image"]: m["U"]["sha256"], m["Q"]["image"]: m["Q"]["sha256"],
            m["F"]["base"]["image"]: m["F"]["base"]["sha256"], m["J"]["clean"]["image"]: m["J"]["clean"]["sha256"]}
    want.update({v["image"]: v["sha256"] for v in m["F"]["cases"].values()})
    want.update({v["image"]: v["sha256"] for v in m["J"]["cases"].values()})
    for image in images:
        got = file_sha(Path(diskdir) / image)
        row(f"XR-unchanged-{boot}-{image[:-4]}", got == want[image], f"sha256 {got[:16]} after the boot, {want[image][:16]} made")
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
    if len(argv) == 6 and argv[0] == "judge":
        return judge(argv[1], json.loads(Path(argv[2]).read_text()), argv[3], argv[4], argv[5])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
