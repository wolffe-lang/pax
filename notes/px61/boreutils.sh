#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/boreutils.pid"
ulimit -c 0
uptime
B=$L/build/mpx3-boreutils
mkdir -p "$B"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
podman run --rm --privileged --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
    set -euo pipefail; cd "$1/pax"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
    tests/mpx3-boreutils --only build --tier native --bore "$1/w/bore"
' px61 "$L" > "$B.build.log" 2>&1
cd "$L/pax"
taskset -c 8-11 tests/mpx3-boreutils --only linux --images "$B/mpx3-boreutils" > "$B.linux.log" 2>&1
uptime
taskset -c 8-11 tests/mpx3-boreutils --images "$B/mpx3-boreutils" --tier native --firmware bios > "$B.boot.log" 2>&1
uptime
echo 'boreutils root and pax: PASS'
