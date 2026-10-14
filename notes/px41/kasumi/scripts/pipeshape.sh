#!/bin/bash
# px41 on kasumi: tests/mpx3-sound's `grep … | grep -qv` under pipefail, old shape and new, on cost
# files whose FIRST line is clamped (the case the line exists to catch). usage: pipeshape.sh OUT [K CPUS]
set -uo pipefail
out=$1 k=${2:-0} cpus=${3:--}
mkdir -p "$out"; cd "$out" || exit 2
grep() { command grep -a "$@"; }
mk() { { echo "cost scale 123 ms, 7 clamped"; for ((i = 1; i < $1; i++)); do echo "cost tune$i 123 ms, 0 clamped"; done; } > "$2"; }
mk 3 small.txt; mk 200 mid.txt; mk 20000 big.txt
pids=(); for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
ts=(); [ "$k" -gt 0 ] && taskset -cp $cpus $$ > /dev/null
for f in small.txt mid.txt big.txt; do
    n=300; [ $f = big.txt ] && n=50
    old=0 new=0
    for ((i = 0; i < n; i++)); do
        grep -E '^cost ' $f | grep -qv ' 0 clamped$' && old=$((old + 1))
        grep -v ' 0 clamped$' $f > /dev/null && new=$((new + 1))
    done
    echo "$f ($(wc -l < $f) lines, $(wc -c < $f) bytes, the first clamped), $k loops on $cpus: clamping seen, of $n: old shape $old, new $new"
done | tee -a result.txt
for p in "${pids[@]}"; do kill "$p"; done
