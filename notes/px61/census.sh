#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/census.pid"
mkdir -p "$L/census"
podman run --rm --cap-add SYS_PTRACE --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" localhost/px13-ubuntu bash -c '
set -euo pipefail
export PATH="$L/bin/lope-1:$L/bin/bore-1:$PATH"
P=$L/bin/pelt-1/pelt
for mode in plain guarded; do
    code=":"; [ "$mode" != guarded ] || code="eval \"\$(lope init pelt)\""
    strace -f -n -o "$L/census/lope-$mode.trace" "$P" -c "$code" > "$L/census/lope-$mode.out" 2>&1
    echo "== lope-$mode forks and threads"
    grep -E "clone\(|clone3\(|wait4\(" "$L/census/lope-$mode.trace" || true
done
for mode in plain metadata; do
    opts=(); [ "$mode" != metadata ] || opts=(-pugsD)
    strace -f -n -o "$L/census/aspen-$mode.trace" "$L/bin/aspen-1/aspen" "${opts[@]}" "$L/build/mpx5-aspen/mpx5-aspen/root/etc" > "$L/census/aspen-$mode.out" 2>&1
done
python3 -I - "$L/census" <<"PY"
from pathlib import Path
import re,sys
p=Path(sys.argv[1])
for group in ("lope", "aspen"):
    calls=set()
    for trace in sorted(p.glob(group+"-*.trace")):
        calls |= set(re.findall(r"\[\s*\d+\]\s+(\w+)\(", trace.read_text()))
    text="\n".join(sorted(calls))+"\n"
    (p/(group+".calls")).write_text(text)
    print(group, len(calls), text)
PY
'
echo 'census PASS'
