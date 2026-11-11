#!/usr/bin/env bash
# notes/px119/rig/step.sh WHAT [ARGS…] — one step of px119's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the head,
# under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the images
#   ci-plan        tests/ci-plan (the tiers map, the new probe's line)
#   build ARGS     tests/mpx5-sudo --only build ARGS, in a container (no engine there: the container
#                  sides are the next step's)
#   auth           tests/mpx5-sudo --only auth on the host: px103's sudo rows and the password sessions
#                  (P2 P3 P4 P5, sudo-n-tty-reused among P4's) in throwaway Ubuntu containers, the
#                  engine through notes/px106/rig/docker-like (docker's shape, as CI runs them)
#   boot ARGS      tests/mpx5-sudo --images the build ARGS, in a container with KVM (P1, P6, P7, P8,
#                  P9, S1, S5), held to the auth step's output
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        for i in localhost/px75-ubuntu:2 localhost/px103-sudo:1 localhost/px106-auth:1; do
            "$P" image inspect "$i" > /dev/null 2>&1 || echo "REFUSED no-image $i"
        done
        command -v python3 > /dev/null || echo "REFUSED no-python3 on the host"
        echo "preflight: kvm, engine, images and python3 looked at; the slot's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    build) ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tests/mpx5-sudo --only build "$@"; exit $?' x "$@" ;;
    auth) PODMAN=$P MEM=${MEM:-12g} CPUS=$CPUS PAX_ENGINE=$CO/notes/px106/rig/docker-like \
        taskset -c "$CPUS" tests/mpx5-sudo --only auth --images "$PAX_BUILD/mpx5-sudo" < /dev/null ;;
    boot) ctr 1 localhost/px75-ubuntu:2 bash -c 'tests/mpx5-sudo --images "$PAX_BUILD/mpx5-sudo" "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
