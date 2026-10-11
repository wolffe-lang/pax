#!/usr/bin/env python3
# px29: the capture as runs of periods: every rising crossing's period,
# classified to the nearest of the given pitches (within 3%), else '?'.
import sys, struct
sys.path.insert(0, sys.argv[1]); import importlib.util
spec=importlib.util.spec_from_file_location("wn", sys.argv[1]+"/wav-notes"); 
from importlib.machinery import SourceFileLoader
wn=SourceFileLoader("wn", sys.argv[1]+"/wav-notes").load_module()
vals, rate, ch, bits = wn.samples(sys.argv[2])
want=[float(x) for x in sys.argv[3].split(",")]
swing=max(vals)-min(vals); mid=(max(vals)+min(vals))/2
cr=[]
for i in range(1,len(vals)):
    a,b=vals[i-1],vals[i]
    if a<=mid<b: cr.append(i-1+(mid-a)/float(b-a))
runs=[]
for a,b in zip(cr,cr[1:]):
    hz=rate/(b-a); lab='?'
    for w in want:
        if abs(hz-w)/w<0.03: lab="%g"%w
    if runs and runs[-1][0]==lab and a-runs[-1][2]<2: runs[-1][2]=b; runs[-1][3]+=1
    else: runs.append([lab,a,b,1])
for lab,a,b,n in runs[:int(sys.argv[4]) if len(sys.argv)>4 else 400]:
    print("%7.1f ms %6.1f ms %-6s %d periods" % (a*1000/rate,(b-a)*1000/rate,lab,n))
print("samples", len(vals), "seconds %.3f"%(len(vals)/rate))
