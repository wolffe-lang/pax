#!/bin/bash
# px41 on kasumi: one suite booted from a tree's built images, K busy loops on CPUS and the suite under
# taskset to the same CPUS (K=0: no added load, no taskset).
# usage: suite.sh TAG OUTNAME K CPUS suite [args…]   output ev/TAG/OUTNAME.{out,rc}, a line in ev/TAG/summary.txt
set -u
L=~/lanes/px41; tag=$1 name=$2 k=$3 cpus=$4 s=$5; shift 5
ev=$L/ev/$tag; tree=$L/t-$tag
export PAX_CACHE=$L/cache PAX_REQUIRE_UEFI=1 WOLF_PAIRING_REQUIRE_SIBLING=1 TMPDIR=$L/tmp PAX_REQUIRE_QEMU=1
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
cd "$tree" || exit 2
pids=(); for ((j = 0; j < k; j++)); do taskset -c $cpus bash -c 'while :; do :; done' & pids+=($!); done
echo "${pids[*]}" > $ev/$name.load.pids
ts=(); [ "$k" -gt 0 ] && ts=(taskset -c $cpus)
u0=$(uptime); t0=$SECONDS
"${ts[@]}" env --default-signal=INT,QUIT,HUP,TERM tests/$s --images build/$s "$@" > $ev/$name.out 2>&1; rc=$?
for p in "${pids[@]}"; do kill "$p"; done
echo "$rc" > $ev/$name.rc
echo "$name rc=$rc secs=$((SECONDS - t0)) PASS=$(grep -a -c ' PASS ' $ev/$name.out) FAIL=$(grep -a -c ' FAIL' $ev/$name.out) SKIP=$(grep -a -ci 'skip' $ev/$name.out) k=$k cpus=$cpus before:$u0" >> $ev/summary.txt
