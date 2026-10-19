#!/bin/bash
# px52 on kasumi: boot a built suite's images on kasumi itself (TCG), under taskset -c 0-3; the suite's Linux side
# first when it has an `--only linux`.   boot.sh SUITE TAG BOOT-ARGS...
L=$HOME/lanes/px52
S=$1 T=$2; shift 2
B=$L/build/$T
cd $L/pax
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
if grep -q -- '--only linux' tests/$S && [ -z "${PX52_NO_LINUX:-}" ]; then
  tests/$S --only linux --images $W > $B.linux.log 2>&1
  echo "linux: $? ($(tail -n 1 $B.linux.log | cut -c1-200))"
fi
taskset -c 0-3 tests/$S --images $W "$@" > $B.boot.log 2>&1
rc=$?
echo "boot: $rc"
grep -a 'FAIL' $B.boot.log | cut -c1-600 | head -40
tail -n 1 $B.boot.log
exit $rc
