#!/bin/bash
# px51 on kasumi: each suite built (px13-ubuntu, cpus 4-15) and then booted (taskset -c 0-3, BIOS), one after another.
#   chain-suites.sh TIER SUITE...
L=$HOME/lanes/px51
TI=$1; shift
for s in "$@"; do
  t=c-$s-$TI
  echo "== $s ($TI)"
  bash $L/pax/notes/px51/build-only.sh $s $t $TI
  bash $L/pax/notes/px51/boot-suite.sh $s $t $TI
  cp $L/build/$t.boot.log $L/keep/kasumi-$s-$TI.boot.log; cp $L/build/$t.build.log $L/keep/kasumi-$s-$TI.build.log
  rm -rf $L/build/$t
done
