#!/usr/bin/env bash
# px89: probes/ci-mirror-suites.sh on a block (its image built by
# ci-mirror-run.sh). launch.sh runs it as `ci-mirror-suites-run.sh BLOCK NAME TREE SUITE...`.
set -uo pipefail
L=/home/mfwolffe/lanes/px89
B=$1 N=$2; shift 2
CTR_WD=$L bash "$L/scripts/ctr2.sh" "$B" "$N" localhost/px89-dhcp-ci:1 KVM=1 NET=1 -- bash "$L/scripts/probes/ci-mirror-suites.sh" "$L/build/$N" "$@"
