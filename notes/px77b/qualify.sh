#!/usr/bin/env bash
# px77b: one qualify boot (machine a or b) under hasu block A, released the moment QEMU's container ends.
set -uo pipefail
L=/home/mfwolffe/lanes/px77b
M=$1
printf '%s\n' "$$" > "$L/qualify-$M.pid"
export PATH=/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77b qualify %s acquiring block A\n' "$(date -u +%FT%TZ)" "$M"
until flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(30)'
done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px77b-qualify-$M" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 -v "$L:$L" -w "$L" localhost/px75-ubuntu:2 taskset -c 0-5 python3 -I "$L/qualify.py" "$M" || rc=$?
flock -u 9
exec 9>&-
printf '%s block A RELEASED qualify %s rc=%s\n' "$(date -u +%FT%TZ)" "$M" "$rc"
echo "$rc" > "$L/qualify-$M.exit"
python3 -I "$L/frames.py" "$L/qualify-$M" > "$L/logs/frames-$M.log" 2>&1 || printf 'frames %s rc=%s\n' "$M" "$?"
printf '%s END qualify %s rc=%s\n' "$(date -u +%FT%TZ)" "$M" "$rc"
exit "$rc"
