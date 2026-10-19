#!/bin/bash
# px52 on kasumi: build a suite in px13-ubuntu on cpus 4-15 (its `--only build`, or `--no-boot` for a suite
# without one), no boot (PX52_BUILD_CPUS, default 4-15).   build.sh SUITE TAG BUILD-ARGS...   -> ~/lanes/px52/build/TAG/
L=$HOME/lanes/px52
S=$1 T=$2; shift 2
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $L/pax
echo "tree: $(git log --oneline -1)"
podman run --rm --privileged --cpuset-cpus ${PX52_BUILD_CPUS:-4-15} -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S $*" > $B.build.log 2>&1
rc=$?
echo "build: $rc ($(tail -n 1 $B.build.log | cut -c1-300))"
exit $rc
