#!/usr/bin/env bash
# px62, kasumi only: build one kernel entry point in px13-ubuntu (the CI
# runner's baseline), the lane's own cache and CPUs 0-3. No install.
#   kbuild.sh KMAIN [native|release]
set -euo pipefail
L=$HOME/lanes/px62
k=${1:-kmain_console}
tier=${2:-native}
mkdir -p "$L/kb/$tier" "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE="$L/cache" -e TMPDIR="$L/tmp" localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$1/pax"; w=$(tools/fetch-wolf | tail -1)
        flag=(); [ "$3" = release ] && flag=(--release)
        PAX_WOLF=$w tools/build-kernel ${flag[@]+"${flag[@]}"} --src kernel/$2.lu "$1/kb/$3"
    ' px62 "$L" "$k" "$tier"
