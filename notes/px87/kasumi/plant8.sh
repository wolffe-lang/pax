#!/usr/bin/env bash
# px87: the plant's local record (planning's tools/gauntlet-record.sh --plant V7), by hostchain.sh: a fresh clone of
# GitHub's pax on the plant branch PLANT (one commit, one hunk, on the main head BASE), one step that runs
# tests/mpx3-screen's native BIOS leg there and must fail V7 by name. The suite prints its rows as
# `mpx3-screen: FAIL V7 ...`; the step prints each of its FAIL lines again without that prefix, so the record holds
# the literal `FAIL V7 ...` line the tool asks for (the suite's whole output is in the step too, indented).
#   plant8.sh PLANT BASE OUT
set -uo pipefail
PLANT=$1 BASE=$2 OUT=$3 S=$L/p8s B=$L/p8
[ ! -e "$S" ] && [ ! -e "$B" ] && [ ! -e "$OUT" ] || { echo "$S, $B or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q "$PLANT" || exit 3
[ "$(git -C "$S" rev-parse HEAD^)" = "$BASE" ] || { echo "the plant is not on $BASE"; exit 3; }
mkdir -p "$B"
cat > "$B/steps.sh" <<STEPS
set -uo pipefail
. "$L/bin/gauntlet-record.sh"
screen() {
    ctr bash "$L/bin/run.sh" "$S" "$B/mpx3-screen" mpx3-screen tests/mpx3-screen --tier native --firmware bios > "$B/mpx3-screen.out" 2>&1
    local rc=\$?
    sed 's/^/  /' "$B/mpx3-screen.out"
    sed -n 's/^mpx3-screen: \(FAIL [A-Z][0-9]* .*\)\$/\1/p' "$B/mpx3-screen.out"
    return \$rc
}
gauntlet_step mpx3-screen-plant screen
STEPS
cd "$S" && bash "$L/bin/gauntlet-record.sh" --output "$OUT" --base "$BASE" --plant V7 -- bash "$B/steps.sh"
