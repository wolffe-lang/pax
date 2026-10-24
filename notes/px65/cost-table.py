#!/usr/bin/env python3
"""px65: cost.sh's COST lines (any number of files) as one table: for
each kernel and tier, trunk's and the branch's .text, and the deltas of
.text, .rodata, .data and .bss.   cost-table.py COST-OUTPUT...
"""
import sys
rows = {}
for p in sys.argv[1:]:
    for l in open(p):
        if not l.startswith("COST "):
            continue
        f = l.split()
        if f[4] == "BUILD-FAILED":
            rows[(f[2], f[3], f[1])] = None
            continue
        rows[(f[2], f[3], f[1])] = (f[4], dict(x.split("=", 1) for x in f[6:] if "=" in x))
print("| kernel | tier | trunk .text | branch .text | .text | .rodata | .data | .bss | branch ELF (first 16 of sha256) |")
print("|---|---|---:|---:|---:|---:|---:|---:|---|")
for k, tier in sorted({(k, t) for k, t, _ in rows}, key=lambda x: (x[1] != "native", x[0])):
    a, b = rows.get((k, tier, "trunk")), rows.get((k, tier, "branch"))
    if not a or not b:
        print("| %s | %s | %s | %s | | | | | |" % (k, tier, "failed" if a is None else a[1][".text"], "failed" if b is None else b[1][".text"]))
        continue
    d = [int(b[1].get(s, 0)) - int(a[1].get(s, 0)) for s in (".text", ".rodata", ".data", ".bss")]
    print("| %s | %s | %s | %s | %+d | %+d | %+d | %+d | `%s` |" % ((k, tier, a[1][".text"], b[1][".text"]) + tuple(d) + (b[0],)))
