#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/init-cost.pid"
ulimit -c 0
while ! awk '{exit !($1 < 16)}' /proc/loadavg; do uptime; sleep 60; done
uptime
podman run --rm --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" localhost/px13-ubuntu python3 -I -c '
import os, statistics, subprocess, time
from pathlib import Path
l=Path(os.environ["L"])
pelt=l/"bin/pelt-1/pelt"
lope=l/"bin/lope-1/lope"
env={"PATH":str(lope.parent)+":"+str(l/"bin/bore-1")+":/usr/bin:/bin","HOME":"/","TERM":"linux","LC_ALL":"C"}
text=subprocess.check_output([str(lope),"init","pelt"],env=env,text=True)
lines=text.splitlines(True)
guards=[i for i,line in enumerate(lines) if "(set -o autocd)" in line]
assert len(guards)==1, "guard shape changed; do not guess how to remove it"
i=guards[0]
assert "&&" in lines[i], "guard is not one complete conditional line"
without=lines.copy(); without[i]=":\n"
programs={"guarded":text,"guard-removed":"".join(without)}
values={k:[] for k in programs}
for turn in range(33):
    for mode in (list(programs) if turn%2==0 else list(reversed(programs))):
        start=time.perf_counter_ns()
        subprocess.run([str(pelt),"-c",programs[mode]],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
        elapsed=(time.perf_counter_ns()-start)/1_000_000
        if turn>=2:values[mode].append(elapsed)
for mode,v in values.items():
    print(mode,"n",len(v),"median-ms",round(statistics.median(v),4),"min-ms",round(min(v),4),"max-ms",round(max(v),4))
print("guard-median-delta-ms",round(statistics.median(values["guarded"])-statistics.median(values["guard-removed"]),4))
'
uptime
