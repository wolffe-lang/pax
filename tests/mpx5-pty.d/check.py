#!/usr/bin/env python3
"""tests/mpx5-pty.d/check.py — px111: hold a PAX transcript of the pty
probe to the Linux reference, row by row.

    check.py NAME LINUX.txt RULED.txt PAX.txt     every row; exit 1 on any FAIL
    check.py --refusals IMAGE RULED.txt           the `refused:` lines ruled for IMAGE, sorted
    check.py --selftest

A row's id is its first word (`O8`, `T69a`, `ptyprobe:`, `done:`); the
session's transcript lines (`S| …`) are numbered in order (`S|1`, `S|2`,
…). Each Linux row is expected on PAX exactly, unless RULED.txt names
PAX's own line for that run and row:

    # R-px111-N: why (comment lines and blank lines are skipped)
    row NAME|* ID <TAB> PAX'S LINE           the line PAX prints instead
    row NAME|* ID <TAB> -                    a row PAX does not print
    refusal IMAGE|* <TAB> refused: …         a refusal the kernel names, once a run

Prints `PASS ID` or `FAIL ID: pax … want …` per row (FAIL lines at column
0: a plant's named red reaches the record), and `FAIL ID: extra` for a
PAX row Linux never printed.
"""
import sys


def rows(lines):
    out = []
    n = 0
    for ln in lines:
        if not ln.strip():
            continue
        if ln.startswith("S| "):
            n += 1
            out.append(("S|%d" % n, ln))
        else:
            out.append((ln.split(" ", 1)[0], ln))
    return out


def ruled(path, name):
    sub, refusals = {}, {}
    for raw in open(path, encoding="utf-8", errors="replace"):
        ln = raw.rstrip("\n")
        if not ln.strip() or ln.startswith("#"):
            continue
        head, _, text = ln.partition("\t")
        w = head.split()
        if w[0] == "row" and len(w) == 3 and w[1] in (name, "*"):
            sub[w[2]] = None if text == "-" else text
        elif w[0] == "refusal" and len(w) == 2:
            refusals.setdefault(w[1], []).append(text)
        elif w[0] not in ("row", "refusal"):
            raise SystemExit("check.py: a ruled line of no known kind: %r" % ln)
    return sub, refusals


def check(name, linux_lines, ruled_path, pax_lines):
    sub, _ = ruled(ruled_path, name)
    want = []
    for rid, ln in rows(linux_lines):
        if rid in sub:
            if sub[rid] is not None:
                want.append((rid, sub[rid]))
        else:
            want.append((rid, ln))
    have = rows(pax_lines)
    hv = {}
    order = []
    for rid, ln in have:
        if rid in hv:
            hv[rid].append(ln)
        else:
            hv[rid] = [ln]
            order.append(rid)
    out = []
    bad = 0
    seen = set()
    for rid, ln in want:
        seen.add(rid)
        got = hv.get(rid, [])
        if not got:
            out.append("FAIL %s: missing; want %r" % (rid, ln))
            bad += 1
            continue
        g = got.pop(0)
        if g == ln:
            out.append("PASS %s" % rid)
        else:
            out.append("FAIL %s: pax %r want %r" % (rid, g, ln))
            bad += 1
    for rid in order:
        for g in hv.get(rid, []):
            out.append("FAIL %s: extra %r" % (rid, g))
            bad += 1
    return out, bad


def read(path):
    return open(path, encoding="utf-8", errors="replace").read().split("\n")


def selftest():
    import os
    import tempfile
    d = tempfile.mkdtemp()
    lin = ["ptyprobe: px111's probe, as root", "O1 stat /dev/ptmx: chr 5:2", "O2 x: 1", "S| \"a\"", "S| \"b\"", "done: R exited 0"]
    rl = os.path.join(d, "ruled.txt")
    with open(rl, "w") as f:
        f.write("# a comment\nrow probe-root O2\tO2 x: 2\nrow * S|2\t-\nrefusal probe\trefused: tty ioctl 0x5420, -ENOTTY\n")
    good = ["ptyprobe: px111's probe, as root", "O1 stat /dev/ptmx: chr 5:2", "O2 x: 2", "S| \"a\"", "done: R exited 0"]
    o, b = check("probe-root", lin, rl, good)
    assert b == 0, o
    o, b = check("probe-root", lin, rl, good[:1] + ["O1 stat /dev/ptmx: ENOENT"] + good[2:])
    assert b == 1 and any(x.startswith("FAIL O1:") for x in o), o
    o, b = check("probe-root", lin, rl, good[:2] + good[3:])
    assert b == 1 and any(x.startswith("FAIL O2: missing") for x in o), o
    o, b = check("probe-root", lin, rl, good + ["O9 more: 1"])
    assert b == 1 and any(x.startswith("FAIL O9: extra") for x in o), o
    o, b = check("probe-user", lin, rl, good)
    assert b == 1 and any(x.startswith("FAIL O2:") for x in o), o
    _, r = ruled(rl, "probe-root")
    assert r == {"probe": ["refused: tty ioctl 0x5420, -ENOTTY"]}, r
    print("check.py selftest: 5 cases held")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    if len(argv) == 4 and argv[1] == "--refusals":
        _, refusals = ruled(argv[3], "")
        out = sorted(refusals.get(argv[2], []) + refusals.get("*", []))
        if out:
            print("\n".join(out))
        return 0
    if len(argv) != 5:
        sys.stderr.write(__doc__)
        return 2
    name, linux, rl, pax = argv[1:]
    out, bad = check(name, read(linux), rl, read(pax))
    print("\n".join(out))
    print("check.py %s: %d rows, %d differ" % (name, len(out), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
