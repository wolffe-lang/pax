#!/usr/bin/env bash
# px89: the CI mirror (probes/ci-mirror.sh) on a block, its image built
# first when missing. launch.sh runs it as `ci-mirror-run.sh BLOCK IMGTREE TREE...`.
set -uo pipefail
L=/home/mfwolffe/lanes/px89
P=/home/mfwolffe/lanes/hasu-env/bin/podman
B=$1; shift
case $B in A) cpus=0-5 ;; B) cpus=6-11 ;; C) cpus=12-17 ;; esac
if ! "$P" image exists localhost/px89-dhcp-ci:1; then
    echo "  $(date -u +%FT%TZ) building localhost/px89-dhcp-ci:1"
    taskset -c "$cpus" "$P" build --build-arg CPUS="$cpus" -t localhost/px89-dhcp-ci:1 -f "$L/scripts/Containerfile.ci" "$L/scripts" 2>&1 | tail -n 5
    "$P" image exists localhost/px89-dhcp-ci:1 || { echo "  the image did not build"; exit 1; }
fi
CTR_WD=$L bash "$L/scripts/ctr2.sh" "$B" cimirror localhost/px89-dhcp-ci:1 KVM=1 NET=1 -- bash "$L/scripts/probes/ci-mirror.sh" "$L/build/cimirror" "$@"
