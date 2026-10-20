#!/bin/bash
# px54 on kasumi: a PLANT branch's tree (TREE) run as suite.sh runs one suite, px53's notes/px53/suite.sh runs it — `--only
# build` in localhost/px13-ubuntu (cpus 4-15), `--only linux --images`
# (its containers, rootless podman) and the boots on kasumi itself under
# taskset -c 0-3 — then its build tree pruned, the logs kept.
#   TREE=DIR plant.sh SUITE TAG TIER FIRMWARE
L=$HOME/lanes/px54
TREE=${TREE:?TREE: the plant tree}
S=$1 T=$2 TI=$3 FW=$4
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $TREE
git log --oneline -1
podman run --rm --privileged --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    -e PAX_LOPE_REPO=$L/lope localhost/px13-ubuntu bash -c "cd $TREE && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S --only build --tier $TI" > $B.build.log 2>&1
echo "$S build: $? ($(tail -n 1 $B.build.log))"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
if grep -q -- '--only linux' tests/$S; then
  tests/$S --only linux --images $W > $B.linux.log 2>&1
  echo "$S linux: $? ($(tail -n 1 $B.linux.log))"
fi
taskset -c 0-3 tests/$S --images $W --tier $TI --firmware $FW > $B.boot.log 2>&1
rc=$?
echo "$S boot: $rc ($TI $FW; load $(cut -d' ' -f1-3 /proc/loadavg))"
grep -a 'PASS\|FAIL\|SKIP' $B.boot.log | sed 's/^[^:]*: //' | cut -c1-12 | sort | uniq -c
grep -a 'FAIL\|SKIP' $B.boot.log | cut -c1-400 | head -12
tail -n 1 $B.boot.log
podman unshare rm -rf $W $B/*.iso 2>/dev/null || rm -rf $W
exit $rc
