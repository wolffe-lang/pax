#!/usr/bin/env bash
# px88: the gauntlet at the final head, behind both of a block's locks
# (launch.sh). Each step's output goes to its own log; every step prints
# `END <step> exit=N`, and the first nonzero step stops the gauntlet.
#   gauntlet.sh BLOCK HEAD HANG PLANT [FROM [UNTIL]]
# FROM names the step to start at (the steps before it ran 0 in an earlier
# gauntlet at the same head, which its log names); they print SKIP. An
# empty FROM starts at the first step. UNTIL names the last step to run:
# the gauntlet ends there and says the rest were not run.
set -uo pipefail
B=$1 HEAD=$2 HANG=$3 PLANT=$4 FROM=${5:-} UNTIL=${6:-}
started=0; [ -n "$FROM" ] || started=1
L=/home/mfwolffe/lanes/px88
S=$L/scripts
export PATH=/home/mfwolffe/lanes/hasu-env/bin:$PATH
G="flock $L/git.lock git"
$G -C "$L/pax" fetch -q origin '+refs/heads/px88*:refs/remotes/origin/px88*' || { echo "END fetch exit=1"; exit 1; }
WT=$L/wt-${HEAD:0:8}
[ -d "$WT" ] || $G -C "$L/pax" worktree add -q --detach "$WT" "$HEAD" || { echo "END worktree exit=1"; exit 1; }
[ "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$L/pax" rev-parse "$HEAD^{commit}")" ] || { echo "END worktree exit=1"; exit 1; }
# The step logs' directory is this run's own (gauntlet3, a run from FROM,
# cleared gauntlet2's when they shared one): the head and this script's pid.
R=$L/build/gauntlet-${HEAD:0:8}-$$
mkdir -p "$R"
echo "gauntlet: head $(git -C "$WT" rev-parse HEAD), hang check $HANG, plant $PLANT, block $B, step logs $R"
step() {
    local name=$1; shift
    [ "$started" = 1 ] || [ "$name" = "$FROM" ] || { echo "SKIP $name (before '$FROM': 0 in the earlier gauntlet)"; return 0; }
    started=1
    local f; f=$R/$(printf '%s' "$name" | tr -c 'A-Za-z0-9._-' '_').log
    "$@" > "$f" 2>&1
    local rc=$?
    grep -E 'PASS|FAIL|END ' "$f" | tail -n 4 | cut -c1-260
    echo "$(date -u +%FT%TZ) END $name exit=$rc"
    if [ "$rc" != 0 ]; then echo "gauntlet: stopped at $name"; exit "$rc"; fi
    if [ "$name" = "$UNTIL" ]; then echo "gauntlet: every step run exit=0, through '$UNTIL' (UNTIL: the steps after it not run) at $HEAD"; exit 0; fi
}
ctr() { local name=$1; shift; CTR_WD=$WT bash "$S/ctr.sh" "$B" "g-$name" localhost/px88-ubuntu:1 "$@"; }
step tests/ci-plan ctr ci-plan -- tests/ci-plan
step "python3 -I tests/ci-retry.py" ctr ci-retry -- python3 -I tests/ci-retry.py
step "python3 -I tests/mpx2-heap.d/budget.py" ctr heap-budget -- python3 -I tests/mpx2-heap.d/budget.py
step "python3 -I tests/ci-budgets.py" ctr ci-budgets -- python3 -I tests/ci-budgets.py
step tests/fetch-retry-selftest ctr fetch-retry -- tests/fetch-retry-selftest
step "python3 -I tests/usb-session-selftest" ctr usb-session -- python3 -I tests/usb-session-selftest
step "python3 -I tests/pipe-shape-selftest" ctr pipe-shape -- python3 -I tests/pipe-shape-selftest
step tests/expect-serial-selftest ctr expect-serial -- tests/expect-serial-selftest
step tests/census ctr census -- sh tests/census
step "tests/mpx5-forks all four legs" bash "$S/suite.sh" "$B" "g-forks-${HEAD:0:8}" "$HEAD" both bios:native:all uefi:native:all bios:release:all uefi:release:all
step "mpx5-forks usage ends on a kernel without fork" bash "$S/hang.sh" "$B" "g-hang-${HANG:0:8}" "$HANG"
step "the plant red by name" bash "$S/plantred.sh" "$B" "g-plant-${PLANT:0:8}" "$PLANT"
step "mpx6-install I-peak" bash "$S/inst.sh" "$B" "g-peak-${HEAD:0:8}" "$HEAD"
step "tests/mpx2-sched all four legs" ctr mpx2-sched KVM=1 -- env PAX_BUILD="$R/mpx2-sched" bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); tests/mpx2-sched'
step "tests/mpx3-user all four legs" ctr mpx3-user KVM=1 -- env PAX_BUILD="$R/mpx3-user" bash -c 'export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); tests/mpx3-user'
echo "gauntlet: every step exit=0 at $HEAD"
