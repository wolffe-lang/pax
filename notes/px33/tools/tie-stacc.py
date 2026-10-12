#!/usr/bin/env python3
# tie-stacc.py FILE: every tie (`~`) whose next event in the same part carries a staccato (`'`): play sounds the
# joined note at half its whole length, so such a tie cuts the held note early.
import sys, re
last, bar = {}, None
for ln, line in enumerate(open(sys.argv[1]), 1):
    w = re.sub(r"(^|\s)#.*", "", line).split()
    if not w or w[0] in ("title", "tempo", "meter", "part"): continue
    if w[0] == "bar": bar = w[1]; continue
    p = w[0]
    for t in w[1:]:
        m = re.match(r"^([^/]+)/([0-9.tx+]+)([\^'>\-_*~]*)$", t)
        if not m: continue
        if p in last and "~" in last[p][1] and "'" in m.group(3):
            print("bar %s line %d part %s: tie from bar %s into %s" % (bar, ln, p, last[p][0], t))
        last[p] = (bar, m.group(3))
