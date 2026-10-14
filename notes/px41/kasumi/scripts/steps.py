#!/usr/bin/env python3
# px41: a speaker timeline of many short plays (one chord each, cut at each `off`): per play the ticks
# between its tones. Counts: plays, plays whose steps are the usual 3 2 2 …, plays whose first step is
# 2 (a tick fell between play's first clock read and its first tone), plays with a step of 0 at the
# first step (4 0 3 …: pax#45's shape) and anywhere later.   usage: steps.py TIMELINE…
import sys
tot = dict(plays=0, usual=0, first2=0, first_collapse=0, later_collapse=0, other=0)
shapes = {}
for f in sys.argv[1:]:
    ev = [l.split() for l in open(f) if l.startswith("event ")]
    cur = []
    for e in ev:
        if e[4] == "on":
            cur.append(int(e[3]))
        elif cur:
            h = [b - a for a, b in zip(cur, cur[1:])]
            cur = []
            if len(h) < 2:
                continue
            tot["plays"] += 1
            if h[0] == 3 and all(x == 2 for x in h[1:]):
                tot["usual"] += 1
            elif h[0] == 2 and all(x == 2 for x in h[1:]):
                tot["first2"] += 1
            elif len(h) > 1 and h[1] == 0 and all(x != 0 for x in h[2:]):
                tot["first_collapse"] += 1
            elif 0 in h[2:]:
                tot["later_collapse"] += 1
            else:
                tot["other"] += 1
            if not (h[0] in (2, 3) and all(x == 2 for x in h[1:])):
                k = " ".join(map(str, h))
                shapes[k] = shapes.get(k, 0) + 1
print(" ".join("%s=%d" % kv for kv in tot.items()))
for k, v in sorted(shapes.items(), key=lambda kv: -kv[1]):
    print("  %d x  %s" % (v, k))
