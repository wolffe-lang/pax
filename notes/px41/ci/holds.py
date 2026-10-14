#!/usr/bin/env python3
# px41: the 'on' events of a speaker timeline and the ticks between them; print those not 2 apart with context.
import sys
for f in sys.argv[1:]:
    ev = [l.split() for l in open(f) if l.startswith("event ")]
    ons = [(int(e[3]), e[4], int(e[5]) if len(e) > 5 else 0) for e in ev]
    out = []
    for i in range(1, len(ons)):
        d = ons[i][0] - ons[i-1][0]
        if ons[i][1] == "on" and ons[i-1][1] == "on" and d != 2:
            out.append("#%d@%d:%d" % (i, ons[i-1][0], d))
    print(f.split("/")[-1], len(ons), " ".join(out))
