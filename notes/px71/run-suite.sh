#!/usr/bin/env bash
# One durable suite checkpoint on kasumi; no traps or host process signals.
# run-suite.sh NAME IMAGE COMMAND [ARG...]
set -u
L=$HOME/lanes/px71
name=$1 image=$2; shift 2
case $name in ''|*[!a-zA-Z0-9_-]*) exit 2 ;; esac
mkdir -p "$L/runs"
[ ! -e "$L/runs/$name.exit" ] || { echo 'use a fresh checkpoint name'; exit 2; }
printf '%s\n' "$$" > "$L/runs/$name.pid"
date -Is > "$L/runs/$name.started"
exec 9> "$HOME/lanes/kasumi-cores-8-11.lock"
flock 9
cpu=taskset
[ "$image" != localhost/s267-gauntlet ] || cpu=/usr/bin/taskset.real
podman run --rm --memory 8g --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" -e CARGO_INCREMENTAL=0 \
    -e SOURCE_DATE_EPOCH=1700000000 -e PAX_LOPE_REPO="$L/lope" \
    -w "$L/pax" "$image" "$cpu" -c 8-11 "$@" 9>&- 2>&1 | tee "$L/runs/$name.log"
rc=${PIPESTATUS[0]}
flock -u 9
exec 9>&-
printf '%s\n' "$rc" > "$L/runs/$name.exit"
date -Is > "$L/runs/$name.finished"
exit "$rc"
