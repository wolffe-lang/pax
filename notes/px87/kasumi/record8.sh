#!/usr/bin/env bash
# px87: the same six steps (steps6.sh) under planning's tools/gauntlet-record.sh at the head rebased onto trunk
# b38643a5 (px90), in a new fresh clone of GitHub's pax ($L/r8s) with new build directories ($L/r8), by
# hostchain.sh (one hold of kasumi-cores-0-3.lock). The record is OUT (a new path; the tool refuses an existing one).
#   record8.sh HEAD OUT
set -uo pipefail
HEAD=$1 OUT=$2 S=$L/r8s
[ ! -e "$S" ] && [ ! -e "$L/r8" ] && [ ! -e "$OUT" ] || { echo "$S, $L/r8 or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b record8 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
cd "$S" && PX87_STEPS_BUILD=$L/r8 bash "$L/bin/gauntlet-record.sh" --output "$OUT" -- bash "$L/bin/steps6.sh"
