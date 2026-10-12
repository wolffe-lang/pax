#!/usr/bin/env python3
# lines.py LEAF X0 X1 [Y0 Y1]: staff-line rows (dark fraction > 0.6) in the column band, grouped into staves of five.
import sys, numpy as np
from PIL import Image
leaf=sys.argv[1]; x0,x1=int(sys.argv[2]),int(sys.argv[3])
a=np.asarray(Image.open("/Users/mfwolffe/lanes/px33/pages/%s.png"%leaf).convert("L")).astype(np.float32)
y0,y1=(int(sys.argv[4]),int(sys.argv[5])) if len(sys.argv)>5 else (0,a.shape[0])
p=(a[y0:y1,x0:x1]<140).mean(axis=1)
rows=np.where(p>0.6)[0]+y0
g=[]
for y in rows:
    if g and y-g[-1][-1]<=2: g[-1].append(y)
    else: g.append([y])
ys=[sum(q)/len(q) for q in g]
i=0
while i+4<len(ys):
    s=ys[i:i+5]; d=np.diff(s)
    if d.max()-d.min()<=3 and 9<=d.min()<=24:
        print("staff", " ".join("%.1f"%v for v in s), "sp %.1f"%(np.mean(d))); i+=5
    else: i+=1
