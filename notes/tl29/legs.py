#!/usr/bin/env python3
"""tl29: which legs a failed pax job's FAIL lines name.
    legs.py LOG...
A leg is a compiler tier (native, release) on a firmware (bios, uefi).
Each `<suite>: FAIL ...` line names the legs whose words it carries; a
line with a tier and no firmware names both firmwares (a build), one with
neither is unattributed (a harness or download failure)."""
import re, sys
TIER = re.compile(r"\b(native|release)\b"); FW = re.compile(r"\b(bios|uefi)\b")
def legs_of(path):
    legs, unattr, n = set(), 0, 0
    for line in open(path, errors="replace"):
        m = re.search(r"\b[a-z0-9-]+: FAIL (.*)$", line)
        if not m:
            continue
        n += 1
        text = m.group(1)
        ts_, fs = set(TIER.findall(text)), set(FW.findall(text))
        if not ts_ and not fs:
            unattr += 1
            continue
        for t in (ts_ or {"native", "release"}):
            for f in (fs or {"bios", "uefi"}):
                legs.add(t + "-" + f)
    return legs, unattr, n
if __name__ == "__main__":
    for p in sys.argv[1:]:
        l, u, n = legs_of(p)
        print("%s\t%d FAIL lines\t%s\t%s" % (p, n, " ".join(sorted(l)) or "-", "%d unattributed" % u if u else ""))
