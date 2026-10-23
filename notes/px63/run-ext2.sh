#!/usr/bin/env bash
# px63, kasumi only: tests/mpx6-ext2 as CI runs it but split by host: the
# build in px13-ubuntu (CPUs 0-3), the disks and the Linux side
# (live: kasumi's Linux 7.2.8) and the boots on the host under TCG.
#   run-ext2.sh RUN [--record] [BOOT ARGS...]
set -euo pipefail
L=$HOME/lanes/px63
run=${1:-e1}; shift || true
rec=(); if [ "${1:-}" = --record ]; then rec=(--record); shift; fi
printf '%s\n' $$ > "$L/run-ext2-$run.pid"
ulimit -c 0
B=$L/build/$run
rm -rf "$B"; mkdir -p "$B" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman TMPDIR=$L/tmp
cd "$L/pax"
t0=$(date +%s)
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e CARGO_INCREMENTAL=0 localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/mpx6-ext2 --only build --tier native
    ' px63 "$L/pax" > "$B.build.log" 2>&1 || { echo "build FAIL $(date -Is)"; exit 1; }
echo "build PASS in $(( $(date +%s) - t0 )) s $(date -Is)"
cp "$L/bin/busybox" "$B/mpx6-ext2/busybox"
t0=$(date +%s)
taskset -c 0-3 tests/mpx6-ext2 --only linux --images "$B/mpx6-ext2" ${rec[@]+"${rec[@]}"} > "$B.linux.log" 2>&1 || echo "linux rc=$?"
echo "linux side in $(( $(date +%s) - t0 )) s"
t0=$(date +%s)
rc=0
taskset -c 0-3 tests/mpx6-ext2 --images "$B/mpx6-ext2" --tier native --firmware bios "$@" > "$B.boot.log" 2>&1 || rc=$?
echo "boot rc=$rc in $(( $(date +%s) - t0 )) s $(date -Is)"
