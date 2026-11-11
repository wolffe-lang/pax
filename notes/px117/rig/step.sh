#!/usr/bin/env bash
# notes/px117/rig/step.sh WHAT [ARGS…] — one step of px117's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the pointer's lines)
#   build ARGS     tests/mpx6-pointer --only build ARGS (the judge's selftest first), in a container
#   yew-build ARGS tests/mpx5-yew --only build ARGS: yew, pelt and the session image, in a container
#   pointer ARGS   tests/mpx6-pointer --images the build ARGS, in a container with KVM
#   yew ARGS       tests/mpx5-yew --only pointer --images the yew build ARGS (Y9), with KVM
#   usb ARGS       tests/mpx6-usb ARGS (its own build: the keyboards and the mouse session beside the
#                  console's new reader), with KVM
#   screen ARGS    tests/mpx3-screen ARGS (its own build: the screen pixel for pixel, the draw's new
#                  check and RIS's new branch under every class), with KVM
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. tools/pointer-session prints its rows `FAIL ROW …` itself. The
# step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx6-pointer|mpx5-yew|mpx6-usb|mpx3-screen): FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && '; }
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: kvm, engine and image looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    build) lift ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx6-pointer --only build "$@"; exit $?' x "$@" ;;
    yew-build) lift ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx5-yew --only build "$@"; exit $?' x "$@" ;;
    pointer) lift ctr 1 localhost/px75-ubuntu:2 bash -c 'tests/mpx6-pointer --images "$PAX_BUILD/mpx6-pointer" "$@"; exit $?' x "$@" ;;
    yew) lift ctr 1 localhost/px75-ubuntu:2 bash -c 'tests/mpx5-yew --only pointer --images "$PAX_BUILD/mpx5-yew" "$@"; exit $?' x "$@" ;;
    usb) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx6-usb "$@"; exit $?' x "$@" ;;
    screen) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-screen "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
