#!/usr/bin/env bash
# notes/px130/rig/step.sh WHAT [ARGS…] — one step of px130's local takes, run by the recorder
# (gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit under
# test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the tap device, the engine, both images, the
#                  dev compiler and its std
#   ci-plan        tests/ci-plan
#   census         tests/census
#   kmsg ARGS      tests/mpx5-kmsg ARGS (the probe against Linux's recording) in the burrowd rig's image
#   burrowd ARGS   tests/mpx5-burrowd ARGS in the burrowd rig's image (its own build: the installed shape
#                  with burrowd, dmesg; B0-B43 against sshd on Linux)
#   suite S ARGS   tests/S ARGS for any other suite (the ones that read the kernel's `killed:` lines from
#                  the serial port, the screen's, the users'), in the burrowd rig's image with its Linux side
#                  in the take's container (ctr sys)
# A suite says a red row as `<suite>: FAIL ROW …` or as the rows' own `FAIL ROW …`; `lift` puts the
# first at column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is
# named in its record) and changes no other line. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx[0-9]-[a-z0-9-]+|census|tour|usb-stick): FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && '; }
img=localhost/px75-ubuntu:2
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -c /dev/net/tun ] || echo "REFUSED no-tun /dev/net/tun is missing"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        for i in $img "$NETIMG"; do "$P" image inspect "$i" > /dev/null 2>&1 || echo "REFUSED no-image $i"; done
        [ -x "$DEVWOLF/wolf" ] || echo "REFUSED no-dev-wolf $DEVWOLF"
        [ -d "$DEVSTD" ] || echo "REFUSED no-dev-std $DEVSTD"
        echo "preflight: kvm, tun, engine, images and the dev compiler looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 $img python3 -I tests/ci-plan ;;
    census) lift ctr 0 $img tests/census ;;
    kmsg) lift ctr 1 "$NETIMG" bash -c "$(wolfed)"'tools/fetch-limine > /dev/null && tests/mpx5-kmsg "$@"; exit $?' x "$@" ;;
    burrowd) lift ctr net "$NETIMG" bash -c "$(wolfed)"'tests/mpx5-burrowd "$@"; exit $?' x "$@" ;;
    suite) s=${1:?a suite}; shift
        lift ctr sys "$NETIMG" bash -c "$(wolfed)"'tools/fetch-limine > /dev/null && s=$1 && shift && tests/$s "$@"; exit $?' x "$s" "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
