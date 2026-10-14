#!/bin/bash
# px41 on kasumi: pax#47 counted. Boots TREE's lobo image (TIER, bios, 256M) N times through TREE's
# tools/lobo-session with STEPS (rounds of ROUND s, the census SLEEP s after each), K busy loops on
# CPUS and the session (QEMU and the clients) under taskset to the same CPUS (K=0: no added load, no
# taskset).   usage: censusloop.sh TREE TIER N K CPUS OUTDIR ROUND SLEEP [STEPS]
set -u
tree=$1 tier=$2 n=$3 k=$4 cpus=$5 out=$6 round=$7 slp=$8 steps=${9:-$HOME/lanes/px41/st/censusloop.steps}
mkdir -p "$out"; cd "$tree" || exit 2
export TMPDIR=$HOME/lanes/px41/tmp
img=$tree/build/mpx4-lobo
sed -e "s/@ROUND@/$round/g" -e "s/@SLEEP@/$slp/g" "$steps" > "$out/steps"
{ uptime; echo "tree $tree tier $tier n $n k $k cpus $cpus round $round sleep $slp steps $steps"; } > "$out/conditions.txt"
pids=()
for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c $cpus)
t0=$SECONDS
for ((i = 1; i <= n; i++)); do
    o=$out/boot-$i
    "${ts[@]}" python3 tools/lobo-session --pax "$img/$tier/lobo-trunk.iso" --mem 256M --accel tcg --firmware bios \
        --steps "$out/steps" --out "$o" --forward 80 --data "$img/data" --timeout 1500 > "$o.out" 2>&1; rc=$?
    echo "$i rc=$rc $(python3 $HOME/lanes/px41/st/census.py "$o/console.log" | head -1) $(tail -n 1 "$o.out" | cut -c1-200)" >> "$out/lines.txt"
    rm -rf "$o/resp" "$o/backend"
done
for p in "${pids[@]}"; do kill "$p"; done
{ echo "secs $((SECONDS - t0))"; uptime; } >> "$out/conditions.txt"
python3 $HOME/lanes/px41/st/census.py "$out"/boot-*/console.log > "$out/counts.txt"
echo done > "$out/done"
