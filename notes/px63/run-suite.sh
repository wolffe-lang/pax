#!/usr/bin/env bash
# px63, kasumi only (px62's run-suite.sh on this lane's CPUs, 0-3): the
# suite's build in the Ubuntu baseline container, PAX under TCG on the
# host. No package installed.
#   run-suite.sh SUITE [RUN] [EXTRA BOOT ARGS...]
set -euo pipefail
L=$HOME/lanes/px63
suite=$1; run=${2:-$1}; shift; [ $# -gt 0 ] && shift
printf '%s\n' $$ > "$L/suite-$run.pid"
ulimit -c 0
uptime
B=$L/build/$run
rm -rf "$B"; mkdir -p "$B" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman TMPDIR=$L/tmp
cd "$L/pax"
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e CARGO_INCREMENTAL=0 localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/"$2" --no-boot --tier native
    ' px63 "$L/pax" "$suite" > "$B.build.log" 2>&1
printf 'build %s PASS %s\n' "$suite" "$(date -Is)"
img=$B/$(ls "$B" | grep -m1 "^$suite\$" || echo "$suite")
rc=0
taskset -c 0-3 "tests/$suite" --images "$img" --tier native --firmware bios "$@" > "$B.boot.log" 2>&1 || rc=$?
printf 'boot %s rc=%s %s\n' "$suite" "$rc" "$(date -Is)"
uptime
