#!/usr/bin/env bash
# px85: the gauntlet at the final head S. Each step runs in a block-A
# container of its own (ctr.sh: both locks, a blocking wait); the wrapper
# stops at the first step that exits nonzero and prints every step's
# `END <step> exit=N`. A count of runs is never the verdict: each stall
# step's exit is the harness's own (0 only when every run's leg exited 0).
#   gauntlet.sh S
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu S=$1
s=${S:0:8} T=$L/wt-${S:0:8} I=$L/images/final-$s-release
[ -d "$T" ] || git -C "$L/pax" worktree add -q --detach "$T" "$S"
[ "$(git -C "$T" rev-parse HEAD)" = "$S" ] || { echo "END worktree exit=2"; exit 2; }
G=$L/runs/gauntlet-$s
rm -rf "$G"; mkdir -p "$G"
step() { # name cmd...
    local name=$1 rc=0; shift
    "$@" > "$G/$name.log" 2>&1 || rc=$?
    grep -aE '^(PASS|FAIL) [A-Z][A-Za-z0-9-]*( |:)|^ci-plan: (PASS|FAIL)$|stall: [0-9]+ of [0-9]+ green|^END |^pipe-equiv:' "$G/$name.log" | tail -n 40
    echo "END $name exit=$rc"
    [ "$rc" = 0 ] || { echo "gauntlet: stopped at $name"; exit "$rc"; }
}
step selftests "$H/ctr.sh" g-selftests-$s "$T" -- bash -c 'set -o pipefail
for c in "tests/ci-plan" "python3 -I tests/ci-retry.py" "python3 -I tests/mpx2-heap.d/budget.py" "python3 -I tests/ci-budgets.py" \
         "tests/fetch-retry-selftest" "python3 -I tests/usb-session-selftest" "python3 -I tests/pipe-shape-selftest" "tests/expect-serial-selftest"; do
    $c > /tmp/step.log 2>&1; rc=$?; tail -n 3 /tmp/step.log; echo "END $c exit=$rc"; [ $rc = 0 ] || exit $rc
done'
step clock-native "$H/ctr.sh" g-clock-native-$s "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/g-clock-$s-native" native
step clock-release "$H/ctr.sh" g-clock-release-$s "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/g-clock-$s-release" release
step pipe-equiv "$H/ctr.sh" g-pipe-$s "$T" -- bash "$H/pipe-equiv.sh" "$L/build/g-clock-$s-native/mpx6-metal/kmain_metal.elf" "$L/build/g-clock-$s-release/mpx6-metal/kmain_metal.elf"
step f8-control "$H/ctr.sh" g-control-$s "$T" -- bash "$H/stall-job.sh" "$T" "$G/f8-control" --runs 5 --no-load --images "$I"
step f8-load-50-50 "$H/ctr.sh" g-load50-$s "$T" -- bash "$H/stall-job.sh" "$T" "$G/f8-load-50-50" --runs 20 --load 50/50 --images "$I"
step f8-load-200-50 "$H/ctr.sh" g-load200-$s "$T" -- bash "$H/stall-job.sh" "$T" "$G/f8-load-200-50" --runs 20 --load 200/50 --images "$I"
mkdir -p "$G/f8-freeze"
"$H/freeze.sh" "g-freeze-$s" "$G/f8-freeze" 300 700 > "$G/f8-freeze.freeze.log" 2>&1 &
fz=$!
desc='the whole container frozen 300 ms (370-530 ms measured) then run 700 ms, again, by podman pause/unpause (notes/px85/hasu/freeze.sh)'
rc=0
"$H/ctr.sh" "g-freeze-$s" "$T" -- bash "$H/stall-job.sh" "$T" "$G/f8-freeze" --runs 20 --external "$desc" --images "$I" > "$G/f8-freeze.log" 2>&1 || rc=$?
touch "$G/f8-freeze/rounds.done"; wait "$fz"
grep -aE 'stall: [0-9]+ of [0-9]+ green|^END ' "$G/f8-freeze.log" | tail -n 3; cat "$G/f8-freeze.freeze.log" | tail -n 1
echo "END f8-freeze exit=$rc"
[ "$rc" = 0 ] || { echo "gauntlet: stopped at f8-freeze"; exit "$rc"; }
echo "gauntlet: every step exit=0 at $S"
