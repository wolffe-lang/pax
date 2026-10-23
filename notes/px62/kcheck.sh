#!/usr/bin/env bash
# px62, kasumi only: compile one kernel entry point with every diagnostic
# (wolf --error-limit=0), errors only, in px13-ubuntu on CPUs 0-3.
#   kcheck.sh KMAIN
set -euo pipefail
L=$HOME/lanes/px62
k=${1:-kmain_console}
mkdir -p "$L/kc" "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        cd "$1/pax/kernel"; w=$(../tools/fetch-wolf | tail -1)
        "$w" build "$2.lu" --target x86_64-unknown-none --emit=obj -o "$1/kc/$2.o" --error-limit=0 2>&1
    ' px62 "$L" "$k" | awk '/^error\[/{on=1} /^warning\[/{on=0} on'
