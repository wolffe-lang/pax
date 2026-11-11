#!/usr/bin/env bash
# notes/px120/rig/step.sh WHAT [ARGS…] — one step of px120's local gauntlet, run by the recorder
# (gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit under
# test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the hot-plug session's lines)
#   build-once     tests/mpx6-usb.d/build-once.py (the CI job's first step: every session a leg, the
#                  hot-plug one's included) and the hot-plug judge's selftest
#   usb ARGS       tests/mpx6-usb ARGS (its own build: the invariants, the three keyboard topologies
#                  against Linux's rows, the mouse session and the hot-plug session), with KVM
#   hotplug ARGS   tests/mpx6-usb --topology hotplug ARGS (the invariants, then the hot-plug session
#                  alone), with KVM
#   frames ARGS    tests/mpx2-frames ARGS (its own build: the allocator's exercise, F9 alloc_below's)
#   pointer ARGS   tests/mpx6-pointer ARGS (its own build: the console's pointer over kernel/xhci)
#   console ARGS   tests/mpx3-console ARGS (its own build: typing over USB keyboards and the stick)
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. tools/hotplug-session prints its rows `FAIL ROW …` itself. The
# step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx6-usb|mpx6-usbcheck|mpx2-frames|mpx6-pointer|mpx3-console): FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && '; }
img=localhost/px75-ubuntu:2
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect $img > /dev/null 2>&1 || echo "REFUSED no-image $img"
        echo "preflight: kvm, engine and image looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 $img python3 -I tests/ci-plan ;;
    build-once) ctr 0 $img bash -c 'python3 -I tests/mpx6-usb.d/build-once.py && python3 -I tests/mpx6-usb.d/hotplug-judge-selftest; exit $?' ;;
    usb) lift ctr 1 $img bash -c "$(wolfed)"'tests/mpx6-usb "$@"; exit $?' x "$@" ;;
    hotplug) lift ctr 1 $img bash -c "$(wolfed)"'tests/mpx6-usb --topology hotplug "$@"; exit $?' x "$@" ;;
    frames) lift ctr 1 $img bash -c "$(wolfed)"'tests/mpx2-frames "$@"; exit $?' x "$@" ;;
    pointer) lift ctr 1 $img bash -c "$(wolfed)"'tests/mpx6-pointer "$@"; exit $?' x "$@" ;;
    console) lift ctr 1 $img bash -c "$(wolfed)"'tests/mpx3-console "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
