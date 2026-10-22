#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/census-store-and-forks.pid"
ulimit -c 0
uptime
podman run --rm --cap-add SYS_PTRACE --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" localhost/px13-ubuntu bash -c '
set -euo pipefail
O=$L/census/store-and-forks
mkdir -p "$O/home" "$O/target"
export HOME=$O/home LOPE_DATA_DIR=$O/data
A=$L/bin/lope-1/lope
for mode in init add list query; do
    case $mode in
      init) args=(init pelt) ;; add) args=(add -- "$O/target") ;;
      list) args=(list) ;; query) args=(query -- target) ;;
    esac
    strace -f -n -o "$O/lope-$mode.trace" "$A" "${args[@]}" > "$O/lope-$mode.out" 2>&1
done
export PATH="$L/bin/bore-1:/usr/bin:/bin"
strace -f -n -o "$O/fork-shapes.trace" "$L/bin/pelt-1/pelt" -c '\''( sleep 1 ) & wait; x=$(echo a; :); echo fork-shapes:$x'\'' > "$O/fork-shapes.out" 2>&1
echo "== store synchronisation and rename"
grep -E "fsync\(|rename\(" "$O/lope-add.trace"
echo "== background/substitution process forks"
grep -E "clone\(.*CLONE_CHILD_CLEARTID.*CLONE_CHILD_SETTID.*SIGCHLD" "$O/fork-shapes.trace"
cat "$O/fork-shapes.out"
python3 -I - "$O" <<"PY"
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);calls=set()
for f in p.glob("lope-*.trace"):
    calls |= set(re.findall(r"\[\s*\d+\]\s+(\w+)\(",f.read_text()))
print("lope-only census",len(calls)," ".join(sorted(calls)))
assert "fsync" in calls
PY
'
uptime
