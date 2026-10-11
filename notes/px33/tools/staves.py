#!/usr/bin/env python3
# staves.py PAGE [X0 X1]: every staff's 5 line ys (measured in the x band), and barline xs per staff.
import sys, subprocess
pg=int(sys.argv[1]); src="/Users/mfwolffe/lanes/px33/pages/%04d.png"%pg
d=subprocess.run(["sips","-g","pixelWidth","-g","pixelHeight",src],capture_output=True,text=True).stdout.split()
PW,PH=int(d[d.index("pixelWidth:")+1]),int(d[d.index("pixelHeight:")+1])
X0,X1=(int(sys.argv[2]),int(sys.argv[3])) if len(sys.argv)>3 else (PW*45//100,PW*55//100)
raw=subprocess.run(["ffmpeg","-v","error","-i",src,"-vf","format=gray","-f","rawvideo","-"],capture_output=True).stdout
def dk(x,y): return raw[y*PW+x]<140
w=X1-X0
rows=[sum(1 for c in range(X0,X1) if dk(c,r))/w for r in range(PH)]
g=[]
for r in range(PH):
    if rows[r]>0.7:
        if g and r-g[-1][-1]<=2: g[-1].append(r)
        else: g.append([r])
ys=[sum(a)/len(a) for a in g]; i=0; st=[]
while i+4<len(ys):
    s=ys[i:i+5]; dd=[b-a for a,b in zip(s,s[1:])]
    if max(dd)-min(dd)<=3 and 9<=min(dd)<=24: st.append(s); i+=5
    else: i+=1
for k,s in enumerate(st):
    t,b=int(s[0]),int(s[4])
    # barlines: columns dark over the whole staff height
    xs=[]
    for x in range(150,PW-20):
        if all(dk(x,y) or dk(x+1,y) for y in range(t,b+1)):
            if not xs or x-xs[-1][-1]>3: xs.append([x])
            else: xs[-1].append(x)
    bl=[a[0] for a in xs]
    print("%2d top %4d bot %4d sp %.1f bars %s"%(k,t,b,(s[4]-s[0])/4," ".join(map(str,bl))))
