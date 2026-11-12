#!/usr/bin/env bash
# notes/px125/rig/step.sh WHAT [ARGS…] — one step of px125's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the suite's lines)
#   build ARGS     tests/mpx7-mux --only build ARGS (the checkers' selftests first), in a container
#   linux          tests/mpx7-mux --only linux: both probes as pid 1 on a pseudo-terminal in throwaway
#                  Ubuntu containers (the host's engine, ENGINE), each row held to the committed
#                  references
#   boot ARGS      tests/mpx7-mux --images the build ARGS, in a container with KVM
#   screen ARGS    tests/mpx3-screen ARGS (its own build: the screen pixel for pixel against
#                  tools/screen-ref, which reads the font's new rows), with KVM
#   vt ARGS        tests/mpx5-screen ARGS (its own build: px59's VT rows), with KVM
#   console ARGS   tests/mpx3-console ARGS (its own build: the console's typed sessions), with KVM and
#                  SYS_ADMIN for its Linux side
#   games ARGS     tests/mpx6-games ARGS (its own build: the games' glyph probes and frames), with KVM
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx7-mux|mpx3-screen|mpx5-screen|mpx3-console|mpx6-games): +FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && '; }
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        [ -x "$ENGINE" ] || echo "REFUSED no-engine-wrapper $ENGINE"
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: kvm, engine and image looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    build) lift ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx7-mux --only build "$@"; exit $?' x "$@" ;;
    linux) lift env PAX_ENGINE="$ENGINE" ENGINE_CPUS="$CPUS" tests/mpx7-mux --only linux --images "$PAX_BUILD/mpx7-mux" ;;
    boot) lift ctr 1 localhost/px75-ubuntu:2 bash -c 'tests/mpx7-mux --images "$PAX_BUILD/mpx7-mux" "$@"; exit $?' x "$@" ;;
    screen) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-screen "$@"; exit $?' x "$@" ;;
    vt) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx5-screen "$@"; exit $?' x "$@" ;;
    console) CTR_CAPS=SYS_ADMIN lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-console "$@"; exit $?' x "$@" ;;
    games) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx6-games "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
