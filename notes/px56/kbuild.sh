#!/bin/bash
# px56 on kasumi: build one kernel in px13-ubuntu (cpus 4-15), no suite: tools/build-kernel --src kernel/KMAIN.lu
#   kbuild.sh KMAIN TAG [--release]   -> ~/lanes/px56/build/k-TAG/ (the build log in k-TAG.log)
L=$HOME/lanes/px56
K=$1 T=$2; shift 2
B=$L/build/k-$T
rm -rf $B && mkdir -p $B
cd $L/pax
podman run --rm --cpuset-cpus ${PX56_BUILD_CPUS:-4-15} -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e CARGO_INCREMENTAL=0 \
    localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tools/build-kernel $* --src kernel/$K.lu $B" > $B.log 2>&1
rc=$?
echo "kbuild $K: $rc"
grep -v '^\s*$' $B.log | tail -n 30
exit $rc
