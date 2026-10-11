#!/usr/bin/env python3
# check.py FILE: px32 part-format bar-fill and word check (a lane-side aid; px32's parser is the judge).
import sys, re
from fractions import Fraction as F
DYN={"ppp","pp","p","mp","mf","f","ff","fff","sfz","sf","fz","fp","<",">","!","cresc","dim"}
ev=re.compile(r"^(r|[A-G](##|bb|#|b)?[0-8](,[A-G](##|bb|#|b)?[0-8]){0,5})/([0-9.tx+]+)([\^'>\-_*~]*)$")
def length(s):
    tot=F(0)
    for part in s.split("+"):
        m=re.match(r"^(1|2|4|8|16|32|64)(\.{0,2})(t|x\d+)?$",part)
        if not m: raise ValueError("length "+s)
        b=F(1,int(m.group(1))); d=b; add=b
        for _ in m.group(2): add/=2; d+=add
        if m.group(3):
            if m.group(3)=="t": d*=F(2,3)
            else:
                n=int(m.group(3)[1:]); p=1
                while p*2<n: p*=2
                d*=F(p,n)
        tot+=d
    return tot
meter=F(1); parts=set(); bar=None; fill={}; errs=0; nb=None; total=F(0)
tempo=None
def close():
    global errs
    if bar is None: return
    for k,v in fill.items():
        if v!=meter: print("bar %s part %s: %s of %s"%(bar,k,v,meter)); errs+=1
for ln,line in enumerate(open(sys.argv[1]),1):
    line=re.sub(r"(^|\s)#.*","",line).strip()
    if not line: continue
    w=line.split()
    if w[0]=="part": parts.add(w[1]); continue
    if w[0] in ("title","tempo","meter") and bar is None:
        if w[0]=="meter": a,b=w[1].split("/"); meter=F(int(a),int(b))
        continue
    if w[0]=="bar":
        close(); n=int(w[1])
        if nb is not None and n!=nb+1: print("line %d: bar %d after %d"%(ln,n,nb)); errs+=1
        nb=n; bar=n; fill={}
        if "meter" in w: a,b=w[w.index("meter")+1].split("/"); meter=F(int(a),int(b))
        continue
    if w[0] not in parts: print("line %d: unknown part %s"%(ln,w[0])); errs+=1; continue
    fill.setdefault(w[0],F(0))
    for t in w[1:]:
        if t in DYN: continue
        m=ev.match(t)
        if not m: print("line %d: bad word %s"%(ln,t)); errs+=1; continue
        try: fill[w[0]]+=length(m.group(5))
        except ValueError as e: print("line %d: %s"%(ln,e)); errs+=1
close(); print("bars to", nb, "errors", errs)
