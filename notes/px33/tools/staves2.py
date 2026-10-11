#!/usr/bin/env python3
# staves2.py PAGE: staff tops (5-line groups) found in any of 12 vertical bands; prints top, spacing.
import sys, subprocess
pg=int(sys.argv[1]); src="/Users/mfwolffe/lanes/px33/pages/%04d.png"%pg
d=subprocess.run(["sips","-g","pixelWidth","-g","pixelHeight",src],capture_output=True,text=True).stdout.split()
PW,PH=int(d[d.index("pixelWidth:")+1]),int(d[d.index("pixelHeight:")+1])
raw=subprocess.run(["ffmpeg","-v","error","-i",src,"-vf","format=gray","-f","rawvideo","-"],capture_output=True).stdout
found=[]
for b in range(12):
    X0=int(PW*(0.12+b*0.07)); X1=X0+int(PW*0.05)
    w=X1-X0
    rows=[sum(1 for c in range(X0,X1) if raw[r*PW+c]<140)/w for r in range(PH)]
    g=[]
    for r in range(PH):
        if rows[r]>0.7:
            if g and r-g[-1][-1]<=2: g[-1].append(r)
            else: g.append([r])
    ys=[sum(a)/len(a) for a in g]; i=0
    while i+4<len(ys):
        s=ys[i:i+5]; dd=[q-p for p,q in zip(s,s[1:])]
        if max(dd)-min(dd)<=3 and 9<=min(dd)<=24: found.append((s[0],(s[4]-s[0])/4)); i+=5
        else: i+=1
found.sort(); out=[]
for t,sp in found:
    if out and abs(t-out[-1][0])<20: continue
    out.append((t,sp))
for k,(t,sp) in enumerate(out): print(k,int(t),int(t+4*sp),"%.1f"%sp)
