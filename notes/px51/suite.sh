#!/bin/bash
# px51 on kasumi: one suite the way a host without the build's libc runs it — `--only build` in px13-ubuntu,
# `--only linux --images` (its containers) and the boots on kasumi itself (BIOS).
#   suite.sh SUITE TAG TIER [BUILD-ARGS...]     (TIER: native, release or both)
L=$HOME/lanes/px51
S=$1 T=$2 TI=$3; shift 3
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $L/pax
podman run --rm --privileged -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S --only build --tier $TI $*" > $B.build.log 2>&1
echo "build: $? ($(tail -n 1 $B.build.log))"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$B/$S
if grep -q -- '--only linux' tests/$S; then
  tests/$S --only linux --images $W > $B.linux.log 2>&1
  echo "linux: $? ($(tail -n 1 $B.linux.log))"
fi
taskset -c 0-3 tests/$S --images $W --tier $TI --firmware bios > $B.boot.log 2>&1
rc=$?
echo "boot: $rc"
grep -a 'FAIL\|PASS\|SKIP' $B.boot.log | sed 's/^[^:]*: //' | cut -c1-200 | sort | uniq -c | sort -rn | head -5
grep -a 'FAIL' $B.boot.log | cut -c1-400 | head -10
tail -n 1 $B.boot.log
exit $rc
