#!/usr/bin/env python3
# rs.py PAGE BARLINES(comma) STAFF:CLEF:KEY[:REACH] ... : heads per bar on each staff, tight box (REACH spaces beyond, default 3.5).
import sys, subprocess
T="/Users/mfwolffe/lanes/px33/tools/"
pg=sys.argv[1]; bars=[int(v) for v in sys.argv[2].split(",")]
st=[l.split() for l in subprocess.run(["python3",T+"staves2.py",pg],capture_output=True,text=True).stdout.splitlines()]
for spec in sys.argv[3:]:
    f=spec.split(":"); k=int(f[0]); clef=f[1]; key=f[2]; reach=float(f[3]) if len(f)>3 else 3.5
    top,bot,sp=int(st[k][1]),int(st[k][2]),float(st[k][3])
    out=subprocess.run(["python3",T+"heads.py",pg,str(bars[0]+6),str(bars[-1]),str(int(top-reach*sp)),str(int(bot+reach*sp)),clef,key],capture_output=True,text=True).stdout.splitlines()
    res={}
    for l in out:
        if l.startswith("#") or l.startswith("no"): continue
        x,step,nat,nm,fill=l.split(); x=int(x)
        b=sum(1 for v in bars if v<=x)
        res.setdefault(b,[]).append("%s%s"%(nm,"" if fill=="filled" else "o"))
    print("staff %d %s: "%(k,clef)+" | ".join("b%d %s"%(b," ".join(res[b])) for b in sorted(res)))
