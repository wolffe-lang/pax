#!/usr/bin/env bash
# px89: build localhost/px89-dhcp:1 (Containerfile beside this script).
set -uo pipefail
L=/home/mfwolffe/lanes/px89
P=/home/mfwolffe/lanes/hasu-env/bin/podman
B=$1
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; esac
taskset -c "$cpus" "$P" build --build-arg CPUS="$cpus" -t localhost/px89-dhcp:1 -f "$L/scripts/Containerfile" "$L/scripts" 2>&1 | tail -n 15
rc=${PIPESTATUS[0]}
"$P" run --rm localhost/px89-dhcp:1 cat /etc/px89-packages.txt
exit $rc
