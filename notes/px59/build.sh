#!/bin/bash
set -euo pipefail
L=$HOME/lanes/px59
mkdir -p "$L/cache" "$L/build" "$L/tmp"
podman run --rm --network host --cpuset-cpus 0-3 -v "$L:$L:Z" -e L="$L" -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
set -euo pipefail
ulimit -c 0
cd "$L/pax"
export PAX_WOLF=$(tools/fetch-wolf)
mkdir -p "$L/build/native"
tools/build-kernel --src kernel/kmain_console.lu "$L/build/native"
'
