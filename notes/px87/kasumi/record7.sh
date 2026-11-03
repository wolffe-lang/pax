#!/usr/bin/env bash
# px87: record6.sh again after kasumi's reset at 08:03:12Z killed record6 inside mpx6-install (no marker, not
# evidence): the same steps (steps6.sh) under planning's tools/gauntlet-record.sh, at HEAD in a new fresh clone of
# GitHub's pax ($L/r7s) with new build directories ($L/r7), by hostchain.sh (one hold of kasumi-cores-0-3.lock).
# The record is OUT (a new path; the tool refuses an existing one).
#   record7.sh HEAD OUT
set -uo pipefail
HEAD=$1 OUT=$2 S=$L/r7s
[ ! -e "$S" ] && [ ! -e "$L/r7" ] && [ ! -e "$OUT" ] || { echo "$S, $L/r7 or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b record7 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
cd "$S" && PX87_STEPS_BUILD=$L/r7 bash "$L/bin/gauntlet-record.sh" --output "$OUT" -- bash "$L/bin/steps6.sh"
