#!/usr/bin/env bash
# px68, kasumi only: build one kernel entry point in px13-ubuntu (the CI
# runner's baseline), the lane's own cache and CPUs 0-3 (the caller holds
# the cores' lock). No install.
#   kbuild.sh KMAIN [native|release] [OUTNAME]
set -euo pipefail
L=$HOME/lanes/px68
T=${PAX_TREE:-$L/pax}
k=${1:-kmain_console}
tier=${2:-native}
o=${3:-$tier}
mkdir -p "$L/kb/$o" "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -e CARGO_INCREMENTAL=0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1"; w=$(tools/fetch-wolf | tail -1)
        flag=(); [ "$3" = release ] && flag=(--release)
        PAX_WOLF=$w tools/build-kernel ${flag[@]+"${flag[@]}"} --src kernel/$2.lu "$5/kb/$4"
    ' px68 "$T" "$k" "$tier" "$o" "$L"
