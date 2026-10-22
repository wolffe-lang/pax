#!/usr/bin/env bash
# R-px61-2: reuse the verified binaries/ELF and Linux references, but
# give each replay case and role its own PAX boot. Keep the bundle.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/partitioned-replay.pid"
ulimit -c 0
while ! awk '{exit !($1 < 16)}' /proc/loadavg; do
    echo 'WAIT partitioned replay: load must be below 16'
    uptime
    sleep 60
done
uptime
export PAX_CACHE=$L/cache PAX_BUILD=$L/build/mpx5-pelt-partitioned PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
mkdir -p "$PAX_BUILD"
cd "$L/pax"
taskset -c 8-11 tests/mpx5-pelt --images "$L/build/mpx5-pelt-r2/mpx5-pelt" --tier native --firmware bios > "$PAX_BUILD.boot.log" 2>&1
uptime
echo 'partitioned replay: PASS'
