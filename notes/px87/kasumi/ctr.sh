#!/usr/bin/env bash
# px87 on kasumi: one container run on CPUs 0-3 under kasumi-cores-0-3.lock, held for this run alone
# (never idle, never killed), the wait one long flock with a line every 4 minutes.
#   ctr.sh NAME SCRIPT [ARGS...]   SCRIPT runs inside localhost/px76-ubuntu under taskset -c 0-3
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
rc=0
# CTR_ROOT=1: the rootless container's root (the host's mfwolffe), for a Linux side that makes namespaces.
userns=(--userns=keep-id)
[ "${CTR_ROOT:-0}" != 1 ] || userns=()
# CTR_CAPS=1 (with CTR_ROOT): CAP_SYS_ADMIN inside the rootless user namespace, for a Linux side that
# makes a pid namespace (tools/linux-tty --pid1); still unprivileged on the host.
[ "${CTR_CAPS:-0}" != 1 ] || userns+=(--cap-add SYS_ADMIN)
podman run --rm --name "px87-$name" --init ${userns[@]+"${userns[@]}"} --memory 12g --pids-limit 16384 \
    --ulimit nproc=32768:32768 --ulimit core=0:0 \
    -v "$L:$L" -w "$L" -e HOME="$L/home" -e TMPDIR="$L/tmp" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    localhost/px76-ubuntu taskset -c 0-3 bash "$@" 9>&- || rc=$?
flock -u 9
exec 9>&-
printf '%s END %s exit=%s (the lock released)\n' "$(ts)" "$name" "$rc"
exit "$rc"
