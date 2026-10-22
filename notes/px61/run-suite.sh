#!/usr/bin/env bash
# kasumi only: compile in the Ubuntu baseline; Linux reference in its
# own throwaway container; PAX under TCG and four CPUs. No package install.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/suite-$1.pid"
ulimit -c 0
uptime
suite=$1
B=$L/build/$suite
mkdir -p "$B" "$L/tmp"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
cd "$L/pax"
if grep -q fetch-busybox "tests/$suite"; then tools/fetch-busybox "$L/bin/busybox"; fi
podman run --rm --privileged --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR="$L/tmp" -e PAX_LOPE_REPO="$L/lope" \
    -e CARGO_INCREMENTAL=0 "${PX61_BUILD_IMAGE:-localhost/px13-ubuntu}" bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/"$2" --only build --tier native
    ' px61 "$L/pax" "$suite" > "$B.build.log" 2>&1
printf 'build %s PASS %s\n' "$suite" "$(date -Is)"
"tests/$suite" --only linux --images "$B/$suite" > "$B.linux.log" 2>&1
printf 'linux %s PASS %s\n' "$suite" "$(date -Is)"
uptime
taskset -c 8-11 "tests/$suite" --images "$B/$suite" --tier native --firmware bios > "$B.boot.log" 2>&1
printf 'boot %s PASS %s\n' "$suite" "$(date -Is)"
