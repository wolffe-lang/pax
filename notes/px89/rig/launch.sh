#!/usr/bin/env bash
# px89: start a job on the lane host, detached, behind both of a block's locks (by
# copy of px88's launch.sh).
#
#   launch.sh BLOCK NAME SCRIPT [ARG...]
#
# SCRIPT runs as `bash SCRIPT BLOCK ARG...` once BOTH of the block's locks
# are held, the block name outside, each taken by ONE long blocking flock,
# and holds them for its steps alone. Detached (setsid -f): its pid in
# logs/NAME.pid, its output in logs/NAME.log, its exit status in
# logs/NAME.exit when it ends. Nothing here kills anything.
set -euo pipefail
L=/home/mfwolffe/lanes/px89
B=$1 N=$2 S=$3; shift 3
case $B in A|B|C) ;; *) echo "launch.sh: BLOCK is A, B or C" >&2; exit 2 ;; esac
mkdir -p "$L/logs"
rm -f "$L/logs/$N.exit"
setsid -f bash -c '
    L=$1 B=$2 N=$3 S=$4; shift 4
    echo $$ > "$L/logs/$N.pid"
    {
        echo "$(date -u +%FT%TZ) px89 $N: waiting for rig-block-$B.lock, then rig-$B.lock"
        rc=0
        flock -w 21600 /home/mfwolffe/lanes/rig-block-$B.lock \
            flock -w 21600 /home/mfwolffe/lanes/rig-$B.lock \
            bash "$S" "$B" "$@" || rc=$?
        echo "$(date -u +%FT%TZ) px89 $N: released block $B; END $N exit=$rc"
        echo "$rc" > "$L/logs/$N.exit"
    } >> "$L/logs/$N.log" 2>&1
' px89-launch "$L" "$B" "$N" "$S" "$@" < /dev/null > /dev/null 2>&1
n=0
while [ ! -s "$L/logs/$N.pid" ] && [ $n -lt 50 ]; do
    sleep 0.1
    n=$((n + 1))
done
echo "launched $N on block $B: pid $(cat "$L/logs/$N.pid" 2>/dev/null), log $L/logs/$N.log"
