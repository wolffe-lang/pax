#!/usr/bin/env bash
# px87: the same six steps (steps6.sh) under planning's tools/gauntlet-record.sh at the head with the scroll's
# two ways and the warmed five-sample probe (R-px87-17), in a new fresh clone of GitHub's pax ($L/r10s) with new
# build directories ($L/r10), by
# hostchain.sh (one hold of the slot's lock, PX87_SLOT=4-7). The record is OUT (a new path; the tool refuses an
# existing one).
#   record10.sh HEAD OUT
set -uo pipefail
HEAD=$1 OUT=$2 S=$L/r10s
[ ! -e "$S" ] && [ ! -e "$L/r10" ] && [ ! -e "$OUT" ] || { echo "$S, $L/r10 or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b record10 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
cd "$S" && PX87_STEPS_BUILD=$L/r10 bash "$L/bin/gauntlet-record.sh" --output "$OUT" -- bash "$L/bin/steps6.sh"
