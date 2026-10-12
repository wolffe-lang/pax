#!/usr/bin/env python3
# guide.py LEAF X0 X1 TOPLINE_Y CLEF OUT [SCALE]: crop one staff (x band X0-X1, the staff whose top line is near TOPLINE_Y),
# its five lines measured in this band, scaled; every step (line and space, 6 above to 6 below) drawn as a thin guide
# labelled with its natural name in CLEF, so heads are read against the lines at their own x.
import sys, numpy as np
from PIL import Image, ImageDraw
leaf, x0, x1, ty, clef, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
S = int(sys.argv[7]) if len(sys.argv) > 7 else 4
im = Image.open("/Users/mfwolffe/lanes/px33/pages/%s.png" % leaf).convert("RGB")
a = np.asarray(im.convert("L")).astype(np.float32)
xm = (x0 + x1) // 2; band = a[int(ty) - 6:int(ty) + 90, xm - 60:xm + 60]
p = (band < 140).mean(axis=1)
rows = np.where(p > 0.5)[0] + int(ty) - 6
g = []
for y in rows:
    if g and y - g[-1][-1] <= 2: g[-1].append(y)
    else: g.append([y])
ys = [sum(q) / len(q) for q in g][:5]
if len(ys) < 5: sys.exit("staff not found: %s" % ys)
sp = (ys[4] - ys[0]) / 4
NAMES = "CDEFGAB"
base = {"treble": (2, 4), "bass": (4, 2), "alto": (3, 3), "tenor": (1, 3)}[clef]  # bottom-line letter, octave
top = int(ys[0] - 6 * sp); bot = int(ys[4] + 6 * sp)
c = im.crop((x0, top, x1, bot)).resize(((x1 - x0) * S, (bot - top) * S), Image.LANCZOS)
d = ImageDraw.Draw(c)
for step in range(-10, 21):
    y = (ys[4] - step * sp / 2 - top) * S
    li = base[0] + step; nm = "%s%d" % (NAMES[li % 7], base[1] + li // 7)
    col = (255, 0, 0) if step % 2 == 0 else (0, 140, 255)
    for xx in range(0, c.size[0], 24): d.line((xx, y, xx + 6, y), fill=col, width=1)
    d.text((2, y - 6), nm, fill=col)
c.save(out)
print("lines", " ".join("%.1f" % v for v in ys), "sp %.2f" % sp, "->", out)
