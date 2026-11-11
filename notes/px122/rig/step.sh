#!/usr/bin/env bash
# notes/px122/rig/step.sh WHAT [ARGS…] — one step of px122's timing takes, run by the recorder
# (tools/gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit
# under test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
# Every boot is TCG (no /dev/kvm in the container), as on CI's runners.
#   preflight   the host has what the steps use: the engine, the image
#   suite ARGS  tests/mpx3-shell ARGS: CI's step "the shell runs programs" (the build, the Linux
#               side, every leg's boots)
#   irq ARGS    tests/mpx6-firmware.d/typing-irq mpx3-shell ARGS: CI's all-tier step "the same
#               typing rows with the xHCI on MSI only, then INTx only"
#   times       stamped.py's summary of the two steps' rows and the kernel's own boot lines
#   kernel TIER tools/build-kernel for kmain_console alone on TIER (native or release), timed: wall
#               seconds and the compiler's peak resident set (stamped.py timed)
#   ci-plan     tests/ci-plan (the planner's rows)
#   budgets     tests/ci-budgets.py (the long jobs' limits against their measured floors); its rows
#               print `PASS`/`FAIL` at column 0 themselves
#   selftests   the plan job's other checks, as its first step runs them
#   bootlog ARGS tests/mpx6-bootlog ARGS with KVM, its disks' e2fsprogs and disk tools through
#               engine-local (the container has no engine): /proc/pax-boot's text, line for line
# A step's output goes through stamped.py: each line `+SECONDS ` (since the step began) first, a
# `FAIL ` line lifted to column 0 unstamped (the recorder keeps a `FAIL ` line there); a copy goes
# to $PAX_BUILD/WHAT.stamped for the times step. The step's exit is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
stamp() { local w=$1; shift; "$@" 2>&1 | python3 -I "$GAUNTLET_RIG_DIR/stamped.py" stamp "$PAX_BUILD/$w.stamped"; return "${PIPESTATUS[0]}"; }
lift() { "$@" 2>&1 | sed -u 's/^mpx6-bootlog: FAIL /FAIL /'; return "${PIPESTATUS[0]}"; }
wolfed() { printf '%s' 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1) && '; }
what=${1:?}; shift
case $what in
    preflight)
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect localhost/px75-ubuntu:2 > /dev/null 2>&1 || echo "REFUSED no-image localhost/px75-ubuntu:2"
        echo "preflight: engine and image looked at; the take's CPUs $CPUS; every boot TCG"
        exit 0 ;;
    suite) CAPS=SYS_ADMIN stamp suite ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'tests/mpx3-shell "$@"; exit $?' x "$@" ;;
    irq) stamp irq ctr 0 localhost/px75-ubuntu:2 bash -c 'tests/mpx6-firmware.d/typing-irq mpx3-shell "$@"; exit $?' x "$@" ;;
    times) python3 -I "$GAUNTLET_RIG_DIR/stamped.py" times "$PAX_BUILD" ;;
    kernel) t=${1:?native or release}; f=(); [ "$t" = release ] && f=(--release)
        ctr 0 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'python3 -I "$0" timed tools/build-kernel "$@"; exit $?' \
            "$GAUNTLET_RIG_DIR/stamped.py" ${f[@]+"${f[@]}"} --src kernel/kmain_console.lu "$PAX_BUILD/kernel-$t" ;;
    ci-plan) ctr 0 localhost/px75-ubuntu:2 tests/ci-plan ;;
    budgets) ctr 0 localhost/px75-ubuntu:2 python3 -I tests/ci-budgets.py ;;
    selftests) ctr 0 localhost/px75-ubuntu:2 bash -c 'python3 -I tests/ci-retry.py && python3 -I tests/mpx2-heap.d/budget.py &&
        tests/fetch-retry-selftest && python3 -I tests/usb-session-selftest && python3 -I tests/pipe-shape-selftest; exit $?' ;;
    bootlog) lift ctr 1 localhost/px75-ubuntu:2 bash -c "$(wolfed)"'PAX_ENGINE="$0" tests/mpx6-bootlog "$@"; exit $?' "$GAUNTLET_RIG_DIR/engine-local" "$@" ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
