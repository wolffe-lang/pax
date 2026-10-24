#!/usr/bin/env bash
# px68, kasumi only: a batch of suites, one after another, on CPUs 0-3
# (the caller holds the lock): each by notes/px68/run-suite.sh, its
# summary line into $L/logs/<batch>.sum.
#   batch.sh BATCH SUITE...      (PAX_RECORD=1 records the Linux sides)
set -uo pipefail
L=$HOME/lanes/px68
b=$1; shift
: > "$L/logs/$b.sum"
for s in "$@"; do
    echo "== $s $(date -u +%H:%M:%S)" >> "$L/logs/$b.sum"
    bash "$L/pax/notes/px68/run-suite.sh" "$s" "$b-$s" >> "$L/logs/$b.sum" 2>&1
done
echo "== done $(date -u +%H:%M:%S)" >> "$L/logs/$b.sum"
