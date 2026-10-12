#!/usr/bin/env python3
# length.py FILE: the written length of a part-format tune from its bar lines alone (meter, tempo, rit/accel
# moved linearly in musical position, fermatas), integrated numerically; an independent check of play's figure.
import sys, re
from fractions import Fraction as F
meter, bpm, unit, bars = F(1), None, F(1, 4), []
for line in open(sys.argv[1]):
    w = re.sub(r"(^|\s)#.*", "", line).split()
    if not w: continue
    if w[0] == "tempo" and not bars and bpm is None:
        bpm = float(w[1]); unit = F(1, int(w[2].rstrip("."))) if len(w) > 2 else F(1, 4); continue
    if w[0] == "meter" and not bars: a, b = w[1].split("/"); meter = F(int(a), int(b)); continue
    if w[0] != "bar": continue
    d = {"meter": None, "tempo": None, "rit": None, "fermata": []}
    i = 2
    while i < len(w):
        k = w[i]
        if k == "meter": a, b = w[i + 1].split("/"); d["meter"] = F(int(a), int(b)); i += 2
        elif k in ("tempo", "rit", "accel"):
            v = float(w[i + 1]); j = i + 2; u = None
            if j < len(w) and re.match(r"^\d+\.?$", w[j]): u = F(1, int(w[j].rstrip("."))); j += 1
            if k == "tempo": d["tempo"] = (v, u); i = j
            else: d["rit"] = (v, u, int(w[j + 1])); i = j + 2
        elif k == "fermata": d["fermata"].append(w[i + 1]); i += 2; i += 2 if i < len(w) and w[i] == "at" else 0
        else: i += 1
    bars.append(d)
t, ramp = 0.0, None   # ramp: (start bpm in quarters/min, end, bars left, bars total)
q = lambda v, u: v * float(u / F(1, 4))  # tempo as quarters a minute
cur = q(bpm, unit)
for bi, d in enumerate(bars, 1):
    if len(sys.argv) > 2: print("bar %d %.1f" % (bi, t))
    if d["meter"]: meter = d["meter"]
    if d["tempo"]:
        v, u = d["tempo"]; unit = u or F(1, 4); cur = q(v, unit); ramp = None
    if d["rit"]:
        v, u, k = d["rit"]; ramp = [cur, q(v, u or unit), k, k, 0.0]
    quarters = float(meter * 4); n = 2000
    for s in range(n):
        if ramp:
            frac = (ramp[3] - ramp[2] + (s + 0.5) / n) / ramp[3]; tq = ramp[0] + (ramp[1] - ramp[0]) * frac
        else: tq = cur
        t += quarters / n * 60.0 / tq
    if ramp:
        ramp[2] -= 1
        if ramp[2] == 0: cur = ramp[1]; ramp = None
    for f in d["fermata"]:
        L = F(1, int(f.rstrip(".")));  t += float(L * 4) * 60.0 / cur * (1.5 if f.endswith(".") else 1)
print("bars %d, written %.1f s" % (len(bars), t))
