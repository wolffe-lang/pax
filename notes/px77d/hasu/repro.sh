#!/usr/bin/env bash
# px77d: one repro.py run under hasu block A; MEMLIM the container's memory for that run.
set -uo pipefail
L=/home/mfwolffe/lanes/px77d
MEMLIM=$1; shift
[ -n "${PX77D_LOCKED:-}" ] || exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77d acquiring block A\n' "$(date -u +%FT%TZ)"
until [ -n "${PX77D_LOCKED:-}" ] || flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(20)'
done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px77d-repro-$1" --memory "$MEMLIM" --pids-limit 16384 --ulimit core=0:0 \
 --device /dev/kvm -e PRE -e MACHINE -e ENTRY -e MENU_AT -v "$L:$L" -w "$L" localhost/px75-ubuntu:2 taskset -c 0-5 python3 -I "$L/repro.py" "$@" || rc=$?
[ -n "${PX77D_LOCKED:-}" ] || { flock -u 9; exec 9>&-; }
printf '%s block A RELEASED rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
exit $rc
