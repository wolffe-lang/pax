#!/bin/bash
# px54 on kasumi: tests/mpx5-lope's Linux side (rootless podman, the
# image localhost/px13-ubuntu) and its boots (native BIOS, TCG, under
# taskset -c 0-3) on a build made by build-only.sh.   linux-boot.sh TAG [TIER] [FIRMWARE]
L=$HOME/lanes/px54
T=$1 TI=${2:-native} FW=${3:-bios}
B=$L/build/$T
cd $L/pax
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
tests/mpx5-lope --only linux --images $B/mpx5-lope > $B.linux.log 2>&1
echo "linux: $? ($(tail -n 1 $B.linux.log))"
taskset -c 0-3 tests/mpx5-lope --images $B/mpx5-lope --tier $TI --firmware $FW > $B.boot.log 2>&1
rc=$?
echo "boot: $rc"
grep -a 'FAIL\|PASS\|SKIP' $B.boot.log | cut -c1-300
exit $rc
