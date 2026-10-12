#!/usr/bin/env python3
# tunes.py JOIN HEADER-FULL HEADER-CLOSE OUTDIR: user/tunes/auferstehung (the join from its title, with the header)
# and auferstehung-close (the join's head and bars 63-131 renumbered from 1, with its header).
import sys, re
join, hf, hc, out = sys.argv[1:5]
L = open(join).read().split("\n")
t = next(i for i, l in enumerate(L) if l.startswith("title "))
body = L[t:]
body[0] = 'title Auferstehung, "Bereite dich" to the end (Mahler, Symphony No. 2, 1897)'
open(out + "/auferstehung", "w").write(open(hf).read() + "\n".join(body).rstrip("\n") + "\n")
head = [l for l in body if l.startswith("part ")]
b63 = next(i for i, l in enumerate(body) if l.startswith("bar 63"))
t63 = re.search(r"tempo (\d+) (\d+)", body[b63]).group(0)   # the close's head takes 47.1's own tempo
close = ["title Auferstehung, fig. 47 to the end (Mahler, Symphony No. 2, 1897)", t63, "meter 2/2"] + head
for l in body[b63:]:
    m = re.match(r"^bar (\d+)(.*)$", l)
    close.append("bar %d%s" % (int(m.group(1)) - 62, m.group(2)) if m else l)
open(out + "/auferstehung-close", "w").write(open(hc).read() + "\n".join(close).rstrip("\n") + "\n")
