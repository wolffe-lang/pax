#!/bin/bash
# px51 on kasumi: a built suite's Linux side (its containers) and its boots on kasumi (TCG, BIOS), under taskset -c 0-3.
#   boot-suite.sh SUITE TAG TIER
L=$HOME/lanes/px51
S=$1 T=$2 TI=$3
B=$L/build/$T
cd $L/pax
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
if grep -q -- '--only linux' tests/$S; then
  tests/$S --only linux --images $W > $B.linux.log 2>&1
  echo "linux: $? ($(tail -n 1 $B.linux.log))"
fi
taskset -c 0-3 tests/$S --images $W --tier $TI --firmware bios > $B.boot.log 2>&1
rc=$?
echo "boot: $rc"
grep -a 'FAIL' $B.boot.log | cut -c1-600 | head -40
tail -n 1 $B.boot.log
exit $rc
