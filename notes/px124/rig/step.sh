#!/usr/bin/env bash
# notes/px124/rig/step.sh WHAT [ARGS…] — one step of px124's local takes, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the head,
# under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the new suite's lines)
#   build SUITE ARGS   tests/SUITE --no-boot ARGS in a container (its P0/S0 build)
#   boot SUITE ARGS    tests/SUITE --images the build ARGS, in a container with KVM
#   burrowd ARGS   tests/mpx5-burrowd ARGS whole (its tree, then its boots) in the rig's network image
#   sudo-build ARGS    tests/mpx5-sudo --only build ARGS in a container (no engine there)
#   sudo-auth      tests/mpx5-sudo --only auth on the host: its container sides through
#                  notes/px106/rig/docker-like (docker's shape, as CI runs them)
# A suite says each verdict through tools/lib.sh's `say` (`SUITE: FAIL ROW …`) or at column 0
# (`FAIL ROW …`, the rows' own); `lift` puts the first kind at column 0 as `FAIL ROW …` (the recorder
# keeps a `FAIL ` line there, so a plant's row is named in its record) and changes no other line. The
# step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^mpx[0-9a-z-]+: FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        for i in localhost/px75-ubuntu:2 localhost/px124-net:1 localhost/px103-sudo:1 localhost/px106-auth:1; do
            "$P" image inspect "$i" > /dev/null 2>&1 || echo "REFUSED no-image $i"
        done
        [ -c /dev/net/tun ] || echo "REFUSED no-tun /dev/net/tun"
        echo "preflight: kvm, engine and image looked at; the slot's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    build) s=$1; shift
        lift ctr 0 localhost/px75-ubuntu:2 bash -c 's=$1; shift; export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tests/$s --no-boot "$@"; exit $?' x "$s" "$@" ;;
    boot) s=$1; shift
        lift ctr 1 localhost/px75-ubuntu:2 bash -c 's=$1; shift; tests/$s --images "$PAX_BUILD/$s" "$@"; exit $?' x "$s" "$@" ;;
    sudo-build)
        lift ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tests/mpx5-sudo --only build "$@"; exit $?' x "$@" ;;
    sudo-auth) export PODMAN=$P MEM=${MEM:-12g} CPUS PAX_ENGINE=$CO/notes/px106/rig/docker-like
        lift taskset -c "$CPUS" tests/mpx5-sudo --only auth --images "$PAX_BUILD/mpx5-sudo" < /dev/null ;;
    burrowd)
        lift ctrnet localhost/px124-net:1 bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tests/mpx5-burrowd "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
