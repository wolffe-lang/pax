#!/usr/bin/env bash
# notes/dw02/rig/step.sh WHAT [ARGS…] — one step of dw02's local gauntlet, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight      the host has what the steps use: KVM, the engine, the image
#   ci-plan        tests/ci-plan (the tiers map, the wiring of the new suite's job)
#   suite NAME ARGS
#                  tests/NAME ARGS in the px75-ubuntu image with KVM (NAME one of the suites this
#                  lane's change can reach, listed below)
#   again NAME ARGS
#                  the same with `--images $PAX_BUILD/NAME`: the boots of what an earlier step of
#                  the same take built (mpx6-entropy's TCG leg after its KVM leg)
#   kernels TIER K…  tools/build-kernel for kernel/K.lu at TIER (native, release), each
# The suites with a Linux side reach a container engine through engine-ns (lib.sh's `ctr sys`).
# A suite says a red row as `<suite>: FAIL ROW …` (tools/lib.sh's `say`); `lift` puts such a line at
# column 0 as `FAIL ROW …` (the recorder keeps a `FAIL ` line there, so a plant's row is named in its
# record) and changes no other line. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
lift() { "$@" 2>&1 | sed -u -E 's/^(mpx[0-9]-[a-z0-9-]+|kernel-as): +FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && tools/fetch-limine > /dev/null && '; }
SUITES="mpx6-entropy mpx3-user mpx3-loader mpx4-ready mpx6-latency mpx5-users mpx3-boreutils mpx2-interrupts mpx3-console kernel-as mpx5-burrowd"
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: kvm, engine and image looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-plan ;;
    kernels)
        tier=${1:?a tier}; shift
        lift ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'t=$1; shift; r=(); [ "$t" = release ] && r=(--release); rc=0
            for k in "$@"; do
                o=$PAX_BUILD/kernels-$t/$k; mkdir -p "$o"
                if tools/build-kernel ${r[@]+"${r[@]}"} --src "kernel/$k.lu" "$o" > "$o.txt" 2>&1; then echo "kernels: ok $t $k"
                else echo "kernels: FAIL $t $k"; tail -n 5 "$o.txt"; rc=1; fi
            done; exit $rc' x "$tier" "$@" ;;
    suite|again)
        name=${1:?a suite}; shift
        case " $SUITES " in *" $name "*) ;; *) echo "step.sh: no suite $name in this rig"; exit 2 ;; esac
        kind=sys; [ "$name" = mpx6-entropy ] || [ "$name" = mpx6-latency ] || [ "$name" = kernel-as ] && kind=1
        img=()
        [ "$what" = again ] && img=(--images "$PAX_BUILD/$name")
        lift ctr $kind localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/'"$name"' "$@"; exit $?' x ${img[@]+"${img[@]}"} "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
