#!/usr/bin/env python3
# px41: the censuses of a console.log: open files less two a lobo thread, census by census.
# usage: census.py CONSOLE.LOG…   prints one line a log and the totals.
import re, sys, collections
tot = collections.Counter()
for f in sys.argv[1:]:
    c = open(f, "rb").read().decode(errors="replace").replace("\r", "")
    vals = []
    for m in re.finditer(r"(?m)^census (\d+)\n([\s\S]*?)^census end", c):
        t = m.group(2)
        files = re.search(r"(?m)^(\d+)\t0\t\d+$", t)
        procs = re.findall(r"(?m)^Name:\t(\S+)[\s\S]*?^Threads:\t(\d+)", t)
        if not files:
            continue
        th = sum(int(n) for name, n in procs if name == "lobo")
        vals.append(int(files.group(1)) - 2 * th)
    for v in vals:
        tot[v] += 1
    print("%s: %s" % (f.split("/")[-2] if "/" in f else f, " ".join(map(str, vals))))
print("censuses %d: %s" % (sum(tot.values()), " ".join("%d x %d" % (n, v) for v, n in sorted(tot.items()))))
