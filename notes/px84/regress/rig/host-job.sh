#!/usr/bin/env bash
# px84: a host-side step (container-engine oracles, as CI's runner) on cores 4-7 under the lock.
set -euo pipefail
L=/mnt/steamlib/lanes/px84
name=$1; shift
printf '%s\n' "$$" > "$L/runs/$name.pid"
{
    printf '%s start %s\n' "$name" "$(date -Is)"
    exec 9>/home/mfwolffe/lanes/kasumi-cores-4-7.lock
    flock 9
    printf '%s locked %s\n' "$name" "$(date -Is)"
    rc=0
    ulimit -c 0
    cd "$L/pax"
    env PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_ENGINE=podman SOURCE_DATE_EPOCH=1700000000 TZ=UTC \
        taskset -c 4-7 "$@" 9>&- || rc=$?
    printf '%s exit=%s %s\n' "$name" "$rc" "$(date -Is)"
    printf '%s\n' "$rc" > "$L/runs/$name.exit"
} > "$L/runs/$name.log" 2>&1
exit "$rc"
