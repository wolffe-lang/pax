#!/bin/bash
# px51 on kasumi: build a suite (one tier or both) in px13-ubuntu on cpus 4-15, no boot.   build-only.sh SUITE TAG TIER
L=$HOME/lanes/px51
S=$1 T=$2 TI=$3
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $L/pax
podman run --rm --privileged --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S --only build --tier $TI" > $B.build.log 2>&1
echo "build: $? ($(tail -n 1 $B.build.log))"
