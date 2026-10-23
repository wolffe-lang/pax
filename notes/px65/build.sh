#!/bin/bash
# px65, kasumi: build a suite in the lane's own Ubuntu 24.04 container
# (localhost/px65-ubuntu, notes/px65/Containerfile) on CPUs 12-15, no
# boot.   build.sh SUITE TAG BUILD-ARGS...   -> ~/lanes/px65/build/TAG/
# The tree is PX65_TREE (default ~/lanes/px65/pax).
L=$HOME/lanes/px65; X=${PX65_TREE:-$L/pax}
S=$1 T=$2; shift 2
B=$L/build/$T
rm -rf "$B" && mkdir -p "$B" "$L/cache" "$L/tmp"
cd "$X" || exit 2
echo "tree: $(git log --oneline -1) $(git status --short | tr '\n' ' ')"
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B \
    -e CARGO_INCREMENTAL=0 ${PX65_BUILD_ENV:-} ${PX65_BUILD_IMAGE:-localhost/px65-ubuntu} \
    bash -c "cd $X && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/$S $*" > "$B.build.log" 2>&1
rc=$?
echo "build $S: $rc ($(tail -n 1 "$B.build.log" | cut -c1-300))"
exit $rc
