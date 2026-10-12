#!/bin/bash
# px35 on kasumi: one suite booted from a tree's built images.
# usage: suite.sh TAG OUTNAME [--taskset] suite [args…]   output ev/TAG/OUTNAME.{out,rc}
set -u
L=~/lanes/px35; tag=$1 name=$2; shift 2
ts=(); if [ "${1:-}" = --taskset ]; then ts=(taskset -c 0-3); shift; fi
s=$1; shift
ev=$L/ev/$tag; tree=$L/t-$tag
export PAX_CACHE=$L/cache PAX_REQUIRE_UEFI=1 WOLF_PAIRING_REQUIRE_SIBLING=1 TMPDIR=$L/tmp
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
cd "$tree" || exit 2
t0=$SECONDS
"${ts[@]}" env --default-signal=INT,QUIT,HUP,TERM tests/$s --images build/$s "$@" > $ev/$name.out 2>&1; rc=$?
echo "$rc" > $ev/$name.rc
echo "$name rc=$rc secs=$((SECONDS - t0)) PASS=$(grep -a -c ' PASS ' $ev/$name.out) FAIL=$(grep -a -c ' FAIL' $ev/$name.out)" >> $ev/summary.txt
