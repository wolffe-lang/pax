#!/usr/bin/env bash
# Preserve every log/input/verdict and canonical binaries; remove only
# completed px61 build products. No shared cache/image/tree is touched.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/prune.pid"
echo '== before'; df -h /home; du -sh "$L"
[ -z "$(podman ps -q --filter volume="$L")" ] || { echo 'active px61 container: refuse prune'; exit 1; }
python3 -I - "$L" <<'PY'
from pathlib import Path
import os, shutil, subprocess, sys
l=Path(sys.argv[1]); ev=l/'evidence-builds';ev.mkdir(exist_ok=True)
me=os.getpid()
for f in l.glob('*.pid'):
    if f.name=='prune.pid':continue
    try:pid=int(f.read_text().strip())
    except ValueError:continue
    r=subprocess.run(['ps','-p',str(pid),'-o','stat=,args='],capture_output=True,text=True)
    if r.returncode==0 and str(l) in r.stdout and not r.stdout.lstrip().startswith('Z'):
        raise SystemExit('live recorded job, refuse prune: '+f.name+' '+r.stdout)
# All earlier raw attempts remain, including failures and their inputs.
keep={'.log','.norm','.verdict','.meta','.typed','.halt','.session','.cmp','.txt','.out','.keys','.run','.sums','.pax','.linux'}
build=l/'build'
for p in build.rglob('*'):
    if p.is_file() and (p.suffix in keep or p.name=='sums.txt'):
        d=ev/p.relative_to(build);d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
k=l/'evidence-kernels';k.mkdir(exist_ok=True)
for p in (l/'cost').glob('*/*.elf'):shutil.copy2(p,k/(p.parent.name+'.elf'))
for p in (l/'cost').glob('*.log'):shutil.copy2(p,k/p.name)
print('saved all completed build logs, inputs, verdicts, normalized pairs and kernel ELFs')
PY
podman unshare rm -rf "$L/build" "$L/cost" "$L/base" "$L/tmp" "$L/bin/bore-1" "$L/bin/bore-2" "$L/bin/bore-all-second"
mkdir -p "$L/tmp"
echo '== after'; df -h /home; du -sh "$L"
echo 'px61 prune: PASS (canonical w/, out/, source snapshots and all raw evidence kept)'
