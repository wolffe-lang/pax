#!/bin/bash
# px57 on kasumi: build a suite in px13-ubuntu on cpus 4-15 (its `--only build`, or `--no-boot` for a suite
# without one), no boot.   build.sh SUITE TAG BUILD-ARGS...   -> ~/lanes/px57/build/TAG/
# The tree is PX57_TREE (default ~/lanes/px57/pax), so a chain can run on a worktree of its own.
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}
S=$1 T=$2; shift 2
B=$L/build/$T
rm -rf $B && mkdir -p $B
cd $X
echo "tree: $(git log --oneline -1) $(git status --short | tr '\n' ' ')"
podman run --rm --privileged --cpuset-cpus ${PX57_BUILD_CPUS:-4-15} -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    -e CARGO_INCREMENTAL=0 ${PX57_BUILD_ENV:-} ${PX57_BUILD_IMAGE:-localhost/px13-ubuntu} bash -c "cd $X && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S $*" > $B.build.log 2>&1
rc=$?
echo "build: $rc ($(tail -n 1 $B.build.log | cut -c1-300))"
exit $rc
