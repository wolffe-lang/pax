#!/usr/bin/env bash
# px87: steps6.sh under planning's tools/gauntlet-record.sh (a copy, $L/bin/gauntlet-record.sh, from wolf's
# tools/ at 862387f), at HEAD in a fresh clone of GitHub's pax ($L/r6s), by hostchain.sh (one hold of
# kasumi-cores-0-3.lock). The record is OUT (a new path; the tool refuses an existing one).
#   record6.sh HEAD OUT
set -uo pipefail
HEAD=$1 OUT=$2 S=$L/r6s
[ ! -e "$S" ] && [ ! -e "$L/r6" ] && [ ! -e "$OUT" ] || { echo "$S, $L/r6 or $OUT exists"; exit 3; }
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b record6 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
cd "$S" && bash "$L/bin/gauntlet-record.sh" --output "$OUT" -- bash "$L/bin/steps6.sh"
