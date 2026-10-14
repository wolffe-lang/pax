#!/usr/bin/env python3
# px41: every `px41 ofiles` line of a scratch kernel's console.log: per census, the kinds at each of its
# opens of a /proc file; prints the censuses where the kinds differ between opens, and the extra records.
import re, sys, collections
K = {3: "file", 4: "dir", 6: "pipe", 7: "sock", 8: "udp", 9: "tcp", 10: "eventfd", 11: "epoll", 13: "unix", 14: "proc"}
for f in sys.argv[1:]:
    c = open(f, "rb").read().decode(errors="replace").replace("\r", "")
    for m in re.finditer(r"(?m)^census (\d+)\n([\s\S]*?)^census end", c):
        rows = []
        for d in re.finditer(r"px41 ofiles (\d+) ref (\d+):(.*)", m.group(2)):
            recs = [tuple(int(x) for x in r.split("/")) for r in d.group(3).split()]
            rows.append((int(d.group(1)), int(d.group(2)), recs))
        if not rows:
            continue
        base = min(n for n, _, _ in rows)
        kinds0 = collections.Counter(k for _, k, _, _ in rows[0][2])
        odd = [(i, n, ref, recs) for i, (n, ref, recs) in enumerate(rows) if n != base or collections.Counter(k for _, k, _, _ in recs) != kinds0]
        tag = "%s census %s: %d opens, counts %s" % (f.split("/")[-3] if f.count("/") > 2 else f, m.group(1), len(rows), " ".join(str(n) for n, _, _ in rows))
        if odd:
            print(tag)
            lo = min(rows, key=lambda r: r[0])
            have = set((i, k, n) for i, k, _, n in lo[2])
            for i, n, ref, recs in odd:
                extra = [(i_, K.get(k, k), r, nd) for i_, k, r, nd in recs if (i_, k, nd) not in have]
                print("   open %d (ref %d): %d records; not in the smallest: %s" % (i, ref, n, extra))
        else:
            print(tag + "  (the same kinds at every open)")
