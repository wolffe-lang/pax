#!/usr/bin/env python3
"""tests/mpx7-mux.d/check.py — px125: hold a PAX transcript of the
multiplexer probe (user/elf/muxprobe.c) to Ubuntu's, row by row.

    check.py LINUX.txt RULED.txt PAX.txt     every row; exit 1 on any FAIL
    check.py --refusals RULED.txt            the `refused:` lines ruled, sorted
    check.py --selftest

A row's id is its first word (`A1.4`, `A6.2`), and `#2`, `#3`, ... after
it for the second and later rows with that word. A line that starts
with `~` is a measurement: it is never compared with Linux's, and each
`bound` line of RULED.txt holds PAX's (below). Every other Linux row is
expected on PAX exactly, unless RULED.txt names PAX's own line for it:

    # why (comment lines and blank lines are skipped)
    row ID <TAB> PAX'S LINE           the line PAX prints instead (a gap, named)
    row ID <TAB> -                    a row PAX does not print
    refusal <TAB> refused: ...        a refusal the kernel names, once a run
    bound ID NAME OP NUMBER           the `~ID` line's number after NAME
                                      (`max 250`: the first integer that
                                      follows the word NAME) holds OP
                                      (<=, >=, ==) against NUMBER

Prints `PASS ID` or `FAIL ID: pax ... want ...` per row (FAIL lines at
column 0, so a plant's named red reaches the record), `FAIL ID: extra`
for a PAX row Linux never printed, and `PASS bound ...` or `FAIL bound
...` for each bound.
"""
import re
import sys


def rows(lines):
    out, seen = [], {}
    for ln in lines:
        ln = ln.rstrip("\r")
        if not ln.strip() or ln.startswith("~"):
            continue
        rid = ln.split(" ", 1)[0]
        seen[rid] = seen.get(rid, 0) + 1
        out.append((rid if seen[rid] == 1 else "%s#%d" % (rid, seen[rid]), ln))
    return out


def measures(lines):
    out = {}
    for ln in lines:
        ln = ln.rstrip("\r")
        if ln.startswith("~"):
            rid = ln[1:].split(" ", 1)[0]
            out.setdefault(rid, []).append(ln)
    return out


def ruled(path):
    sub, refusals, bounds = {}, [], []
    for raw in open(path, encoding="utf-8", errors="replace"):
        ln = raw.rstrip("\n")
        if not ln.strip() or ln.startswith("#"):
            continue
        head, _, text = ln.partition("\t")
        w = head.split()
        if w[0] == "row" and len(w) == 2:
            sub[w[1]] = None if text == "-" else text
        elif w[0] == "refusal" and len(w) == 1:
            refusals.append(text)
        elif w[0] == "bound" and len(w) == 5 and w[3] in ("<=", ">=", "=="):
            bounds.append((w[1], w[2], w[3], int(w[4])))
        else:
            raise SystemExit("check.py: a ruled line of no known kind: %r" % ln)
    return sub, refusals, bounds


def number_after(lines, name):
    for ln in lines:
        m = re.search(r"\b%s (-?\d+)" % re.escape(name), ln)
        if m:
            return int(m.group(1))
    return None


def check(linux_lines, ruled_path, pax_lines):
    sub, _, bounds = ruled(ruled_path)
    want = []
    for rid, ln in rows(linux_lines):
        if rid in sub:
            if sub[rid] is not None:
                want.append((rid, sub[rid]))
        else:
            want.append((rid, ln))
    hv, order = {}, []
    for rid, ln in rows(pax_lines):
        if rid not in hv:
            hv[rid] = []
            order.append(rid)
        hv[rid].append(ln)
    out, bad = [], 0
    for rid, ln in want:
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
    ms = measures(pax_lines)
    for rid, name, op, n in bounds:
        v = number_after(ms.get(rid, []), name)
        ok = v is not None and ((op == "<=" and v <= n) or (op == ">=" and v >= n) or (op == "==" and v == n))
        out.append("%s bound %s %s %s %d: %s" % ("PASS" if ok else "FAIL", rid, name, op, n, "none" if v is None else v))
        bad += 0 if ok else 1
    return out, bad


def read(path):
    return open(path, encoding="utf-8", errors="replace").read().split("\n")


def selftest():
    import os
    import tempfile
    d = tempfile.mkdtemp()
    lin = ["muxprobe: px125's probe, as root, init", "A1.1 32 ptys", "A6.7 SCM_RIGHTS: sendmsg 1; arrived",
           "A7.3 timerfd_create: a descriptor", "A7.3 signalfd4: a descriptor", "~A1.6 latency median 1 ms, max 3 ms"]
    rl = os.path.join(d, "ruled.txt")
    with open(rl, "w") as f:
        f.write("# a comment\nrow A6.7\tA6.7 SCM_RIGHTS: sendmsg ENOSYS; nothing\nrow A7.3#2\t-\n"
                "refusal\trefused: x, -22\nbound A1.6 max <= 250\n")
    good = ["muxprobe: px125's probe, as root, init", "A1.1 32 ptys", "A6.7 SCM_RIGHTS: sendmsg ENOSYS; nothing",
            "A7.3 timerfd_create: a descriptor", "~A1.6 latency median 20 ms, max 120 ms"]
    o, b = check(lin, rl, good)
    assert b == 0, o
    o, b = check(lin, rl, good[:1] + ["A1.1 31 ptys"] + good[2:])
    assert b == 1 and any(x.startswith("FAIL A1.1:") for x in o), o
    o, b = check(lin, rl, good[:-1] + ["~A1.6 latency median 20 ms, max 900 ms"])
    assert b == 1 and any(x.startswith("FAIL bound A1.6") for x in o), o
    o, b = check(lin, rl, good + ["A9.9 more"])
    assert b == 1 and any(x.startswith("FAIL A9.9: extra") for x in o), o
    o, b = check(lin, rl, good[:2] + good[3:])
    assert b == 1 and any(x.startswith("FAIL A6.7: missing") for x in o), o
    o, b = check(lin, rl, good[:-1])
    assert b == 1 and any(x.startswith("FAIL bound A1.6 max <= 250: none") for x in o), o
    _, r, _ = ruled(rl)
    assert r == ["refused: x, -22"], r
    print("check.py selftest: 7 cases held")
    return 0


def main(argv):
    if argv[1:] == ["--selftest"]:
        return selftest()
    if len(argv) == 3 and argv[1] == "--refusals":
        _, refusals, _ = ruled(argv[2])
        if refusals:
            print("\n".join(sorted(refusals)))
        return 0
    if len(argv) != 4:
        sys.stderr.write(__doc__)
        return 2
    linux, rl, pax = argv[1:]
    out, bad = check(read(linux), rl, read(pax))
    print("\n".join(out))
    print("check.py: %d rows, %d differ" % (len(out), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
