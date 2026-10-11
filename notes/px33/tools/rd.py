#!/usr/bin/env python3
# rd.py PAGE STAFF CLEF KEY [BARLINES comma list] : heads on one staff, grouped by bar (uses staves.py).
import sys, subprocess
pg,k,clef,key=sys.argv[1],int(sys.argv[2]),sys.argv[3],sys.argv[4]
T="/Users/mfwolffe/lanes/px33/tools/"
st=subprocess.run(["python3",T+"staves.py",pg],capture_output=True,text=True).stdout.splitlines()
line=[l for l in st if int(l.split()[0])==k][0].split()
top,bot=int(line[2]),int(line[4]); sp=float(line[6])
bars=[int(v) for v in sys.argv[5].split(",")] if len(sys.argv)>5 else [int(v) for v in line[8:]]
x0=bars[0]+8; x1=bars[-1]
out=subprocess.run(["python3",T+"heads.py",pg,str(x0),str(x1),str(int(top-5*sp)),str(int(bot+5*sp)),clef,key],capture_output=True,text=True).stdout.splitlines()
cur=-1
for l in out:
    if l.startswith("#"): continue
    f=l.split(); x=int(f[0])
    b=sum(1 for v in bars if v<=x)
    if b!=cur: print("\n bar%d:"%b,end=""); cur=b
    print(" %s(%s%s)"%(f[3],f[1],"o" if f[4]=="open" else ""),end="")
print()
