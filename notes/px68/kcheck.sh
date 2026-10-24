#!/usr/bin/env bash
# px68, kasumi only: `wolf build` of one kernel entry point with every
# diagnostic (--error-limit=0), printing the errors alone (each with its
# lines), in px13-ubuntu on CPUs 0-3 (the caller holds the lock).
#   kcheck.sh [KMAIN]
set -uo pipefail
L=$HOME/lanes/px68
T=${PAX_TREE:-$L/pax}
k=${1:-kmain_console}
mkdir -p "$L/kc" "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        cd "$1"; w=$(tools/fetch-wolf | tail -1)
        cd kernel && "$w" build "$2.lu" --target x86_64-unknown-none --emit=obj -o "$3/kc/$2.o" --error-limit=0 2>&1
    ' px68 "$T" "$k" "$L" > "$L/kc/$k.log" 2>&1
rc=$?
awk '/^error/{p=1} /^warning/{p=0} p' "$L/kc/$k.log" | head -n 150
echo "kcheck $k: exit $rc, $(grep -c '^error' "$L/kc/$k.log") errors, $(grep -c '^warning' "$L/kc/$k.log") warnings"
