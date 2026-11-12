#!/usr/bin/env bash
# notes/px131/rig/step.sh WHAT [ARGS…] — one step of px131's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   suite NAME ARGS
#                  tests/NAME ARGS in the px75-ubuntu image with KVM (NAME one of the suites this
#                  lane's change can reach: mpx6-latency, mpx2-interrupts, mpx2-sched, mpx3-user,
#                  mpx3-maps, mpx3-tree, mpx5-trace, mpx5-users, mpx5-rates, mpx6-part,
#                  mpx3-boreutils, mpx4-udp, mpx3-console)
#   ci-plan        tests/ci-plan (the tiers map, the wiring of the new suite's job)
# The suites with a Linux side reach a container engine through engine-ns (lib.sh's `ctr sys`, px123's).
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx[0-9]-[a-z0-9-]+): +FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
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
    suite)
        name=${1:?a suite}; shift
        case $name in
            mpx6-latency|mpx2-interrupts|mpx2-sched|mpx3-user|mpx3-maps|mpx3-tree|mpx5-trace|mpx5-users|mpx5-rates|mpx6-part|mpx3-boreutils|mpx4-udp|mpx3-console) ;;
            *) echo "step.sh: no suite $name in this rig"; exit 2 ;;
        esac
        # the suites with a Linux side run with engine-ns (sys); the guard needs only KVM
        kind=sys; [ "$name" = mpx6-latency ] && kind=1
        lift ctr $kind localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/'"$name"' "$@"; exit $?' x "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
