#!/usr/bin/env bash
# px87 on kasumi: a runner detached (setsid -f), with runs/NAME.pid, runs/NAME.log and runs/NAME.exit.
#   [RUNNER=ctr|hostchain] [CTR_ROOT=1] launch.sh NAME SCRIPT [ARGS...]
set -uo pipefail
L=/home/mfwolffe/lanes/px87
name=$1; shift
runner=${RUNNER:-ctr}
[ ! -e "$L/runs/$name.log" ] || { echo "runs/$name.log exists: pick a new name"; exit 2; }
CTR_ROOT=${CTR_ROOT:-0} CTR_CAPS=${CTR_CAPS:-0} setsid -f bash -c 'echo $$ > "$0.pid"; r=$1; shift; bash "/home/mfwolffe/lanes/px87/bin/$r.sh" "$@" > "$0.log" 2>&1; echo $? > "$0.exit"' \
    "$L/runs/$name" "$runner" "$name" "$@" < /dev/null > /dev/null 2>&1
for _ in 1 2 3 4 5 6 7 8 9 10; do [ -s "$L/runs/$name.pid" ] && break; sleep 0.2; done
printf 'launched %s (%s): pid %s, log %s\n' "$name" "$runner" "$(cat "$L/runs/$name.pid" 2>/dev/null)" "$L/runs/$name.log"
