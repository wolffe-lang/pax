#!/usr/bin/env python3
# g.py PAGE NAME X Y W H [SCALE]: crop page image (pixels), find staff lines per 100px strip,
# colour staff lines red and ledger-line positions above/below (2 each) blue; print staves' line ys.
import sys, subprocess
pg, name = int(sys.argv[1]), sys.argv[2]
X, Y, W, H = [int(v) for v in sys.argv[3:7]]
sc = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
src = "/Users/mfwolffe/lanes/px33/pages/%04d.png" % pg
raw = subprocess.run(["ffmpeg","-v","error","-i",src,"-vf","crop=%d:%d:%d:%d,format=gray"%(W,H,X,Y),"-f","rawvideo","-"],capture_output=True).stdout
img = bytearray()
col = [[None]*W for _ in range(H)]
STRIP=100
for sx in range(0, W, STRIP):
    sw=min(STRIP,W-sx)
    if sw<30: continue
    rows=[sum(1 for b in raw[r*W+sx:r*W+sx+sw] if b<140)/sw for r in range(H)]
    cand=[r for r in range(H) if rows[r]>0.8]
    g=[]
    for r in cand:
        if g and r-g[-1][-1]<=2: g[-1].append(r)
        else: g.append([r])
    ys=[sum(a)/len(a) for a in g]
    i=0
    while i+4<len(ys):
        s=ys[i:i+5]; d=[b-a for a,b in zip(s,s[1:])]
        if max(d)-min(d)<=4 and 8<=min(d)<=30:
            sp=sum(d)/4
            for k,yy in enumerate(s):
                for c in range(sx,sx+sw):
                    for dy in (-1,0,1):
                        rr=int(round(yy))+dy
                        if 0<=rr<H and raw[rr*W+c]<150: col[rr][c]=(230,0,0)
            for k in (1,2,3):
                for yy in (s[0]-k*sp, s[4]+k*sp):
                    yy=int(round(yy))
                    if 0<=yy<H:
                        pass
            i+=5
        else: i+=1
out=bytearray()
for r in range(H):
    for c in range(W):
        v=col[r][c]
        if v: out+=bytes(v)
        else:
            b=raw[r*W+c]; out+=bytes((b,b,b))
ppm="/Users/mfwolffe/lanes/px33/crops/%s.ppm"%name
open(ppm,"wb").write(b"P6 %d %d 255\n"%(W,H)+out)
png="/Users/mfwolffe/lanes/px33/crops/%s.png"%name
subprocess.run(["ffmpeg","-v","error","-y","-i",ppm,"-vf","scale=%d:-1:flags=lanczos"%int(W*sc),png])
import os; os.remove(ppm); print(png)
