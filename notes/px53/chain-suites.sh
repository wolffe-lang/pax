#!/bin/bash
# px53 on kasumi: each suite built (px13-ubuntu, cpus 4-15) and then booted (taskset -c 0-3, BIOS), one after another.
#   chain-suites.sh TIER SUITE...
L=$HOME/lanes/px53
TI=$1; shift
for s in "$@"; do
  t=c-$s-$TI
  echo "== $s ($TI)"
  if grep -q -- "--only build" $L/pax/tests/$s; then bash $L/pax/notes/px53/build-only.sh $s $t $TI; else bash $L/pax/notes/px53/build-nb.sh $s $t $TI; fi
  bash $L/pax/notes/px53/boot-suite.sh $s $t $TI
  cp $L/build/$t.boot.log $L/keep/kasumi-$s-$TI.boot.log; cp $L/build/$t.build.log $L/keep/kasumi-$s-$TI.build.log
  rm -rf $L/build/$t
done
