#!/usr/bin/env bash
# px87: a stand-in for `podman run` / `docker run` inside the lane's px76-ubuntu container, which has no
# engine of its own, so that tools/e2fs, tools/disktools (and through them tools/mkdisk and tools/check-usb)
# run beside the container's QEMU 8.2.2, as CI's runner runs them beside its QEMU. Used as PAX_ENGINE.
#   engine-local.sh run [--rm] [--network X] [--security-opt X] [--user X] [-e K=V]... [-v SRC:DST[:ro]]...
#                       [-w DIR] IMAGE PROGRAM [ARG...]
# IMAGE is not pulled or entered: PROGRAM runs here, in the container, with the -e variables set and in -w's
# directory. A -v whose two paths are equal is already true here ($L is mounted at its own path); a -v onto
# another path (tools/disktools' /opt/pax-disktools, its pinned packages) is kept as SRC itself: DST is
# replaced by SRC in every -e value and argument (no write outside $L, no root needed). So
# tools/disktools runs its own pinned binaries; tools/e2fs runs the container's e2fsprogs, which
# notes/px87/kasumi/probe-ci.sh compares with the pinned image's by version and sha256 before any row runs.
set -euo pipefail
die() { echo "engine-local: $*" >&2; exit 2; }
[ "${1:-}" = run ] || die "only 'run' is stood in for: $*"
shift
envs=() wd= srcs=() dsts=()
while [ $# -gt 0 ]; do
    case $1 in
        --rm) shift ;;
        --network|--security-opt|--user) shift 2 ;;
        -e) envs+=("$2"); shift 2 ;;
        -w) wd=$2; shift 2 ;;
        -v) spec=$2; shift 2
            src=${spec%%:*}; rest=${spec#*:}; dst=${rest%%:*}
            [ "$src" = "$dst" ] || { [ -d "$src" ] || die "no $src"; srcs+=("$src"); dsts+=("$dst"); } ;;
        -*) die "an option not stood in for: $1" ;;
        *) break ;;
    esac
done
[ $# -ge 2 ] || die "no IMAGE and PROGRAM"
shift # IMAGE
args=("$@")
for i in ${srcs[@]+"${!srcs[@]}"}; do
    for j in ${envs[@]+"${!envs[@]}"}; do envs[$j]=${envs[$j]//"${dsts[$i]}"/"${srcs[$i]}"}; done
    for j in "${!args[@]}"; do args[$j]=${args[$j]//"${dsts[$i]}"/"${srcs[$i]}"}; done
done
[ -z "$wd" ] || cd "$wd"
exec env ${envs[@]+"${envs[@]}"} "${args[@]}"
