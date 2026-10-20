#!/bin/bash
# px54 on kasumi: build tests/mpx5-lope (one tier or both) in
# localhost/px13-ubuntu on cpus 4-15, no boot.   build-only.sh TAG TIER
L=$HOME/lanes/px54
T=$1 TI=$2
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $L/pax
podman run --rm --privileged --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    -e PAX_LOPE_REPO=$L/lope localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/mpx5-lope --only build --tier $TI" > $B.build.log 2>&1
echo "build: $? ($(tail -n 1 $B.build.log))"
