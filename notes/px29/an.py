#!/usr/bin/env python3
# px29: the probe's verdict: per tune, the kernel's held ticks per tone and
# onset spacing, and the capture's tones (count, lengths, pitches).
import sys, collections
tones=[l.split() for l in open(sys.argv[1]) if l.startswith("tone ")]
ev=[l.split() for l in open(sys.argv[2]) if l.startswith("event ")]
names=sys.argv[3].split(",") ; per=int(sys.argv[4])
on=[(int(e[1]),int(e[3]),int(e[5])) for e in ev if e[4]=="on"]
nxt={}
for a,b in zip(ev,ev[1:]):
    if a[4]=="on": nxt[int(a[1])]=int(b[3])-int(a[3])
print("kernel tones", len(on), "events", len(ev))
k=0
for nm in names:
    mine=on[k:k+per]; k+=per
    held=[nxt.get(i,-1) for i,_,_ in mine]
    gaps=[b[1]-a[1] for a,b in zip(mine,mine[1:])]
    print("%s held %s gaps %s span %d" % (nm, dict(collections.Counter(held)), dict(collections.Counter(gaps)), mine[-1][1]-mine[0][1]))
print("capture tones", len(tones))
for t in tones: print(" ", " ".join(t[1:]))
