#!/usr/bin/env bash
# px87: the same six steps (steps6.sh) under planning's tools/gauntlet-record.sh at the head with the scroll's
# two ways (R-px87-17), in a new fresh clone of GitHub's pax ($L/r9s) with new build directories ($L/r9), by
# hostchain.sh (one hold of the slot's lock, PX87_SLOT=4-7). The record is OUT (a new path; the tool refuses an
# existing one).
#   record9.sh HEAD OUT
set -uo pipefail
HEAD=$1 OUT=$2 S=$L/r9s
[ ! -e "$S" ] && [ ! -e "$L/r9" ] && [ ! -e "$OUT" ] || { echo "$S, $L/r9 or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b record9 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
cd "$S" && PX87_STEPS_BUILD=$L/r9 bash "$L/bin/gauntlet-record.sh" --output "$OUT" -- bash "$L/bin/steps6.sh"
