#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/replay-again.pid"
ulimit -c 0
uptime
old=$L/build/mpx5-pelt/mpx5-pelt
B=$L/build/mpx5-pelt-r2
W=$B/mpx5-pelt
mkdir -p "$B"
cp -a --reflink=auto "$old" "$W"
python3 -I - "$W" <<'PY'
from pathlib import Path
import sys
w=Path(sys.argv[1]); allkeys=[]
for name in (w/'run-names').read_text().splitlines():
    c,role=name.rsplit('-',1)
    path=f'/tmp/px61-{c}-{role}'
    text=f'mkdir -p {path}; cd {path}\n'+(w/'keys'/(c+'.keys')).read_text().replace('cd /tmp\n','cd '+path+'\n')
    (w/'keys'/(name+'.keys')).write_text(text);allkeys.append(text)
(w/'all.keys').write_text(''.join(allkeys))
PY
cd "$L/pax"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
tests/mpx5-pelt --only linux --images "$W" > "$B.linux.log" 2>&1
echo "r2 Linux PASS $(date -Is)"
uptime
taskset -c 8-11 tests/mpx5-pelt --images "$W" --tier native --firmware bios > "$B.boot.log" 2>&1
echo "r2 PAX PASS $(date -Is)"
