#!/usr/bin/env python3
# vs.py OUT IN...: stack PNGs vertically (pad to widest)
import sys,subprocess
out=sys.argv[1]; ins=sys.argv[2:]
ws=[int(subprocess.run(["sips","-g","pixelWidth",i],capture_output=True,text=True).stdout.split()[-1]) for i in ins]
W=max(ws); a=[]; f=""
for k,i in enumerate(ins): a+=["-i",i]; f+="[%d]pad=%d:ih[p%d];"%(k,W,k)
f+="".join("[p%d]"%k for k in range(len(ins)))+"vstack=inputs=%d"%len(ins)
subprocess.run(["ffmpeg","-v","error","-y"]+a+["-filter_complex",f,out])
