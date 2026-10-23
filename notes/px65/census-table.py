#!/usr/bin/env python3
"""notes/px65/census-table.py CENSUSDIR PAXROOT — px65: the census of the
new utilities' calls (census.sh's OUT) against PAX: each call's number
(tools/census/syscall_64.csv), whether the kernel has a handler for it
(a `const SYS_<NAME>` in kernel/, the dispatch's names), and which of the
fourteen utilities make it. Markdown on stdout."""
import csv
import os
import re
import sys

d, root = sys.argv[1], sys.argv[2]
UTILS = ["mkfifo", "link", "unlink", "truncate", "sync", "mktemp", "realpath", "tty",
         "base64", "base32", "comm", "join", "tsort", "shuf"]
nr = {}
for row in csv.reader(l for l in open(os.path.join(root, "tools/census/syscall_64.csv")) if not l.startswith("#")):
    if len(row) >= 3 and row[0].strip().isdigit():
        nr[row[2].strip()] = int(row[0])
served = set()
for dp, _, fs in os.walk(os.path.join(root, "kernel")):
    for f in fs:
        if f.endswith(".lu"):
            for m in re.finditer(r"^const SYS_([A-Z0-9_]+): u64 = (\d+)", open(os.path.join(dp, f)).read(), re.M):
                served.add(int(m.group(2)))
calls = {}
fails = {}
for u in UTILS:
    for line in open(os.path.join(d, u + ".calls")):
        name, n = line.split()
        calls.setdefault(name, {})[u] = int(n)
    for line in open(os.path.join(d, u + ".fails")):
        p = line.split()
        if len(p) == 3:
            fails.setdefault(p[0], set()).add("%s (%s)" % (p[1], u))
print("| nr | call | made by | failures seen on Linux | a PAX handler |")
print("|---:|---|---|---|---|")
for name in sorted(calls, key=lambda c: nr.get(c, 9999)):
    n = nr.get(name)
    by = " ".join(u for u in UTILS if u in calls[name])
    if len(calls[name]) == len(UTILS):
        by = "all fourteen"
    f = ", ".join(sorted(fails.get(name, ())))
    h = "yes" if n in served else "**no**"
    print("| %s | `%s` | %s | %s | %s |" % (n if n is not None else "?", name, by, f, h))
