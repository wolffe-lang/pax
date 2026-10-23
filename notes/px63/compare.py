#!/usr/bin/env python3
# px63: a PAX session's lines (the serial between `user: exec pid 1` and
# init's exit, kernel/user's own `user: ` lines cut out, as
# tests/mpx3-maps cuts them) against a Linux guest's (tools/linux-blk's
# serial between `linux-blk: run 1:` and `linux-blk: run 1 status`).
#   compare.py PAX-SERIAL LINUX-SERIAL OUT-PREFIX
import re
import sys


def norm(path):
    b = open(path, "rb").read().replace(b"\r", b"")
    b = re.sub(rb"\x1b\[[0-9;?=<>]*[A-Za-z]", b"", b)
    return b.decode("utf-8", "replace").split("\n")


def pax(lines):
    out, on = [], False
    for l in lines:
        if l.startswith("user: exec pid 1 "):
            on = True
            continue
        if on and re.match(r"^user: [^ ]+ pid 1 (exit_group|exit) [0-9]+ after ", l):
            break
        if on:
            i = l.find("user: ")
            if i == 0:
                continue
            if i > 0:
                l = l[:i]
            out.append(l)
    return out


def linux(lines):
    out, on = [], False
    for l in lines:
        if l.startswith("linux-blk: run 1:"):
            on = True
            continue
        if on and l.startswith("linux-blk: run 1 status"):
            break
        if on:
            out.append(l)
    return out


p = pax(norm(sys.argv[1]))
x = linux(norm(sys.argv[2]))
open(sys.argv[3] + ".pax", "w").write("\n".join(p) + "\n")
open(sys.argv[3] + ".linux", "w").write("\n".join(x) + "\n")
if p == x:
    print("compare: %d lines identical" % len(p))
    sys.exit(0)
import difflib
d = list(difflib.unified_diff(x, p, "linux", "pax", lineterm="", n=0))
print("compare: %d lines PAX, %d Linux, %d diff lines" % (len(p), len(x), len(d)))
print("\n".join(d[:60]))
sys.exit(1)
