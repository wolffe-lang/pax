#!/usr/bin/env bash
# px88: start a chain on hasu, detached, behind both of a block's locks.
#
#   launch.sh BLOCK NAME SCRIPT [ARG...]
#
# BLOCK is A (CPUs 0-5) or B (CPUs 6-11). The chain SCRIPT runs as
# `bash SCRIPT BLOCK ARG...` once BOTH of the block's locks are held, the
# block name outside, each taken by ONE long blocking flock (the lane rules,
# 2026-11-01: never a short-wait retry loop), and holds them for its steps
# alone. Detached (setsid -f): its pid in logs/NAME.pid, its output in
# logs/NAME.log, its exit status in logs/NAME.exit when it ends. The lane
# watches the log from its own shell; nothing here kills anything.
set -euo pipefail
L=/home/mfwolffe/lanes/px88
B=$1 N=$2 S=$3; shift 3
case $B in A|B) ;; *) echo "launch.sh: BLOCK is A or B" >&2; exit 2 ;; esac
mkdir -p "$L/logs"
rm -f "$L/logs/$N.exit"
setsid -f bash -c '
    L=$1 B=$2 N=$3 S=$4; shift 4
    echo $$ > "$L/logs/$N.pid"
    {
        echo "$(date -u +%FT%TZ) px88 $N: waiting for hasu-block-$B.lock, then hasu-$B.lock"
        rc=0
        flock -w 21600 /home/mfwolffe/lanes/hasu-block-$B.lock \
            flock -w 21600 /home/mfwolffe/lanes/hasu-$B.lock \
            bash "$S" "$B" "$@" || rc=$?
        echo "$(date -u +%FT%TZ) px88 $N: released block $B; END $N exit=$rc"
        echo "$rc" > "$L/logs/$N.exit"
    } >> "$L/logs/$N.log" 2>&1
' px88-launch "$L" "$B" "$N" "$S" "$@" < /dev/null > /dev/null 2>&1
n=0
while [ ! -s "$L/logs/$N.pid" ] && [ $n -lt 50 ]; do
    sleep 0.1
    n=$((n + 1))
done
echo "launched $N on block $B: pid $(cat "$L/logs/$N.pid" 2>/dev/null), log $L/logs/$N.log"
