#!/usr/bin/env python3
# heads.py PAGE X0 X1 Y0 Y1 CLEF [KEY]: noteheads on the one staff inside the box (pixels).
# CLEF: treble bass alto tenor treble8 (octave below). KEY: e.g. -4 (4 flats) or 3 (sharps).
# Prints per head: x, staff step (0 = bottom line, +1 per line/space), natural name, keyed name, fill.
import sys, subprocess
pg=int(sys.argv[1]); X0,X1,Y0,Y1=[int(v) for v in sys.argv[2:6]]; clef=sys.argv[6]; key=int(sys.argv[7]) if len(sys.argv)>7 else 0
src="/Users/mfwolffe/lanes/px33/pages/%04d.png"%pg
W,H=X1-X0,Y1-Y0
raw=subprocess.run(["ffmpeg","-v","error","-i",src,"-vf","crop=%d:%d:%d:%d,format=gray"%(W,H,X0,Y0),"-f","rawvideo","-"],capture_output=True).stdout
D=[[raw[r*W+c]<140 for c in range(W)] for r in range(H)]
# staff lines per strip
STRIP=120; lines_at={}
for sx in range(0,W,STRIP):
    sw=min(STRIP,W-sx)
    if sw<40: continue
    rows=[sum(D[r][sx:sx+sw])/sw for r in range(H)]
    g=[]
    for r in range(H):
        if rows[r]>0.75:
            if g and r-g[-1][-1]<=2: g[-1].append(r)
            else: g.append([r])
    ys=[sum(a)/len(a) for a in g]
    best=None
    for i in range(len(ys)-4):
        s=ys[i:i+5]; d=[b-a for a,b in zip(s,s[1:])]
        if max(d)-min(d)<=3 and 9<=min(d)<=24: best=s; break
    if best: lines_at[sx]=best
if not lines_at: print("no staff found"); sys.exit(1)
def staff(x):
    k=min(lines_at, key=lambda s: abs(s+STRIP/2-x)); return lines_at[k]
sp=sum((s[4]-s[0])/4 for s in lines_at.values())/len(lines_at)
# remove lines: pixels on a line row whose vertical run is <= 3
E=[row[:] for row in D]
for c in range(W):
    s=staff(c)
    for yy in s:
        for r in range(int(yy)-2,int(yy)+3):
            if 0<=r<H and D[r][c]:
                up=r; 
                while up>0 and D[up-1][c]: up-=1
                dn=r
                while dn<H-1 and D[dn+1][c]: dn+=1
                if dn-up+1<=4: E[r][c]=False
# remove thin vertical strokes (stems, barlines): horizontal run <= 3 and vertical run > 1.5 sp
for r in range(H):
    c=0
    while c<W:
        if E[r][c]:
            c2=c
            while c2<W-1 and E[r][c2+1]: c2+=1
            if c2-c+1<=3:
                for cc in range(c,c2+1):
                    up=r
                    while up>0 and D[up-1][cc]: up-=1
                    dn=r
                    while dn<H-1 and D[dn+1][cc]: dn+=1
                    if dn-up>1.6*sp: E[r][cc]=False
            c=c2+1
        else: c+=1
# connected components
seen=[[False]*W for _ in range(H)]; blobs=[]
for r in range(H):
    for c in range(W):
        if E[r][c] and not seen[r][c]:
            st=[(r,c)]; seen[r][c]=True; pts=[]
            while st:
                y,x=st.pop(); pts.append((y,x))
                for dy,dx in ((1,0),(-1,0),(0,1),(0,-1)):
                    yy,xx=y+dy,x+dx
                    if 0<=yy<H and 0<=xx<W and E[yy][xx] and not seen[yy][xx]:
                        seen[yy][xx]=True; st.append((yy,xx))
            ys=[p[0] for p in pts]; xs=[p[1] for p in pts]
            blobs.append((min(xs),max(xs),min(ys),max(ys),len(pts)))
NAMES="CDEFGAB"
base={"treble":(2,4),"bass":(4,2),"alto":(3,3),"tenor":(1,3),"treble8":(2,3)}[clef]  # bottom line letter idx, octave
sharps="FCGDAEB"; flats="BEADGCF"
acc={}
for i in range(abs(key)): acc[(sharps if key>0 else flats)[i]]="#" if key>0 else "b"
out=[]
for x0,x1,y0,y1,n in blobs:
    w=x1-x0+1; h=y1-y0+1
    if w<0.9*sp or w>2.2*sp or h<0.6*sp: continue
    nh=max(1,round(h/(sp*0.95)))  # heads stacked
    if nh>4: continue
    fill=n/(w*h)
    for k in range(nh):
        cy=y0+(k+0.5)*h/nh
        s=staff((x0+x1)/2)
        step=round((s[4]-cy)/(sp/2))
        li,oc=base; idx=li+step; o=oc+idx//7; nm=NAMES[idx%7]
        out.append((x0+X0,step,"%s%d"%(nm,o),"%s%s%d"%(nm,acc.get(nm,""),o),"filled" if fill>0.6 else "open"))
for o in sorted(out): print(*o)
print("# spacing %.1f, staff strips %d"%(sp,len(lines_at)))
