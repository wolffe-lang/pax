#!/usr/bin/env python3
import json, os, pathlib, resource, subprocess, sys, time
label, tree, entry, out = sys.argv[1:]
out=pathlib.Path(out); out.mkdir(parents=True,exist_ok=True)
(out/'ir').mkdir(exist_ok=True)
env=dict(os.environ, WOLF_CLANG='/home/mfwolffe/lanes/px74/capture-clang',PX74_CAPTURE_DIR=str(out/'ir'))
cmd=[env['PAX_WOLF'],'build',entry,'--no-cache','--release','--target','x86_64-unknown-none','--emit=obj','-o',str(out/'kernel.o')]
usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
start=time.monotonic()
print(label, 'START', time.strftime('%FT%T%z'), flush=True)
with (out/'build.log').open('wb') as log:
    rc=subprocess.run(cmd,cwd=pathlib.Path(tree)/'kernel',env=env,stdout=log,stderr=subprocess.STDOUT).returncode
elapsed=time.monotonic()-start
r=resource.getrusage(resource.RUSAGE_CHILDREN)
record=dict(label=label,command=cmd,cwd=tree,elapsed_seconds=elapsed,user_seconds=r.ru_utime-usage_before.ru_utime,system_seconds=r.ru_stime-usage_before.ru_stime,maxrss_kib=r.ru_maxrss,exit=rc)
(out/'time.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record),flush=True)
if rc: raise SystemExit(rc)
irs=sorted((out/'ir').glob('*.ll'))
if not irs: raise SystemExit('no captured LLVM IR')
with (out/'census.csv').open('w') as census:
    subprocess.run(['python3','-I','/home/mfwolffe/lanes/px74/ir-census.py',*map(str,irs)],stdout=census,check=True)
