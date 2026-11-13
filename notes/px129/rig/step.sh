#!/usr/bin/env bash
# notes/px129/rig/step.sh WHAT [ARGS…] — one step of px129's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the wiring of the new suite's job)
#   conspeed ARGS  tests/mpx3-conspeed ARGS (its own build: the console's drawing at 2560 x 1440,
#                  no COM1, the table read off the screen, the rows), with KVM
#   screen ARGS    tests/mpx3-screen ARGS (the screen pixel for pixel against tools/screen-ref, the
#                  scroll's two ways, no framebuffer read under a watchpoint), with KVM
#   vt ARGS        tests/mpx5-screen ARGS (px59's VT rows), with KVM
#   console ARGS   tests/mpx3-console ARGS (the console's typed sessions), with KVM and SYS_ADMIN
#   games ARGS     tests/mpx6-games ARGS (the games' glyphs and frames), with KVM
#   pointer ARGS   tests/mpx6-pointer ARGS (the arrow drawn over a cell, the reports), with KVM
#   pty ARGS       tests/mpx5-pty ARGS (pseudo-terminals, the probe and pelt's session against Linux's)
#   norms          tests/mpx6-triage --selftest and tests/mpx3-screen --selftest: T2's mask and V4's strip
#                  held to their fixtures (pairs from hosted runs' logs), no boot
#   ptyrate N ACCEL FIRMWARE
#                  pty-rate.sh: mpx5-pty's session image booted N times, each run checked (pax#382)
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx3-conspeed|mpx3-screen|mpx5-screen|mpx3-console|mpx6-games|mpx6-pointer|mpx5-pty): +FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tools/fetch-limine > /dev/null && '; }
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: kvm, engine and image looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    conspeed) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-conspeed "$@"; exit $?' x "$@" ;;
    screen) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-screen "$@"; exit $?' x "$@" ;;
    vt) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx5-screen "$@"; exit $?' x "$@" ;;
    console) CTR_CAPS=SYS_ADMIN lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-console "$@"; exit $?' x "$@" ;;
    games) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx6-games "$@"; exit $?' x "$@" ;;
    pointer) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx6-pointer "$@"; exit $?' x "$@" ;;
    pty) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx5-pty "$@"; exit $?' x "$@" ;;
    norms) lift ctr 0 localhost/px75-ubuntu:2 bash -c 'r=0; tests/mpx6-triage --selftest || r=1; tests/mpx3-screen --selftest || r=1; exit $r' ;;
    ptyrate) ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'bash notes/px129/rig/pty-rate.sh "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
