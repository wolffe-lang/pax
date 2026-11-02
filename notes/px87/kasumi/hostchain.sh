#!/usr/bin/env bash
# px87 on kasumi: host steps and container steps under ONE hold of kasumi-cores-0-3.lock, everything on
# CPUs 0-3 (this shell's affinity, inherited by podman's processes and by `taskset -c 0-3` inside).
#   hostchain.sh NAME SCRIPT [ARGS...]   SCRIPT runs on the host; `ctr CMD...` runs CMD in
#   localhost/px76-ubuntu (CTR_ROOT=1 ctr ...: as the rootless container's root).
set -uo pipefail
L=/home/mfwolffe/lanes/px87
name=$1; shift
ts() { date -u +%FT%TZ; }
exec 9>/home/mfwolffe/lanes/kasumi-cores-0-3.lock
printf '%s waiting for kasumi-cores-0-3.lock (%s)\n' "$(ts)" "$name"
( while sleep 240; do printf '%s still waiting for kasumi-cores-0-3.lock (%s)\n' "$(ts)" "$name"; done ) 9>&- &
pr=$!
flock -w 21600 9; got=$?
kill "$pr" 2>/dev/null; wait "$pr" 2>/dev/null
[ "$got" = 0 ] || { printf '%s the lock was not taken in 6 h (%s)\n' "$(ts)" "$name"; exit 3; }
printf '%s kasumi-cores-0-3.lock held (%s)\n' "$(ts)" "$name"
taskset -cp 0-3 $$ > /dev/null
ctr() {
    local userns=(--userns=keep-id)
    [ "${CTR_ROOT:-0}" != 1 ] || userns=()
    [ "${CTR_CAPS:-0}" != 1 ] || userns+=(--cap-add SYS_ADMIN)
    podman run --rm --init ${userns[@]+"${userns[@]}"} --memory 12g --pids-limit 16384 \
        --ulimit nproc=32768:32768 --ulimit core=0:0 \
        -v "$L:$L" -w "$L" -e HOME="$L/home" -e TMPDIR="$L/tmp" \
        -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
        localhost/px76-ubuntu taskset -c 0-3 "$@" 9>&-
}
export -f ctr ts
export L
rc=0
bash "$@" 9>&- || rc=$?
flock -u 9
exec 9>&-
printf '%s END %s exit=%s (the lock released)\n' "$(ts)" "$name" "$rc"
exit "$rc"
