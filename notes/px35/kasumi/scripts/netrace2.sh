#!/bin/bash
# netrace.sh, keeping every leg's serial log, verdict and capture of a run that is not rc 0.
# usage: netrace2.sh TREE N K CPUS OUTDIR
set -u
tree=$1 n=$2 k=$3 cpus=$4 out=$5
mkdir -p "$out"; cd "$tree" || exit 2
export PAX_CACHE=$HOME/lanes/px35/cache PAX_REQUIRE_UEFI=1 TMPDIR=$HOME/lanes/px35/tmp
pids=()
for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > "$out/load.pids"
for ((i = 1; i <= n; i++)); do
    taskset -c $cpus env --default-signal=INT,QUIT,HUP,TERM tests/mpx4-net --images build/mpx4-net --firmware bios --tier native > "$out/run-$i.out" 2>&1
    rc=$?
    echo "$i rc=$rc $(grep -a ' FAIL' "$out/run-$i.out" | cut -c1-60 | paste -sd'|' -)" >> "$out/lines.txt"
    if [ $rc != 0 ]; then mkdir -p "$out/keep-$i"; cp build/mpx4-net-native-bios-* "$out/keep-$i/"; fi
done
for p in "${pids[@]}"; do kill "$p"; done
echo done > "$out/done"
