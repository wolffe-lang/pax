#!/usr/bin/env bash
# notes/px126/rig/step.sh WHAT [ARGS…] — one step of px126's local takes, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the head,
# under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the new suite's job and paths)
#   build ARGS     tests/mpx5-slots --only build ARGS, in a container
#   slots ARGS     tests/mpx5-slots --images the build ARGS, in a container with KVM
#   suite S ARGS   tests/S ARGS (it builds and boots), in a container with KVM
# tests/mpx5-slots writes each row's verdict as `PASS ROW …` or `FAIL ROW …` at column 0 of stdout
# (the recorder keeps a `FAIL ` line there, so a plant's row is named in its record); another suite's
# `S: FAIL ROW …` is lifted to `FAIL ROW …`. The step's exit is the suite's.
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
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: kvm, engine and image looked at; the block's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    build) lift ctr 0 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tests/mpx5-slots --only build "$@"; exit $?' x "$@" ;;
    slots) lift ctr 1 localhost/px75-ubuntu:2 bash -c 'tests/mpx5-slots --images "$PAX_BUILD/mpx5-slots" "$@"; exit $?' x "$@" ;;
    suite) s=${1:?a suite}; shift
        lift ctr 1 localhost/px75-ubuntu:2 bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && s=$1 && shift && tests/$s "$@"; exit $?' x "$s" "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
