#!/usr/bin/env bash
# px80: a batch of suites through notes/px80/run-suite.sh, one at a time, each
# under the CPUs 0-3 block's lock (released between suites, so the block's
# other lane interleaves). The tree is a snapshot taken at the batch's start.
#   batch.sh NAME SUITE...      (results in $L/runs/NAME.out, a done line last)
set -u
L=$HOME/lanes/px80
name=$1; shift
mkdir -p "$L/runs"
printf '%s\n' $$ > "$L/runs/$name.pid"
snap=$L/snap-$name
rm -rf "$snap"; git clone -q "$L/pax" "$snap"
echo "batch $name at $(git -C "$snap" rev-parse HEAD) start $(date -Is)" >> "$L/runs/$name.out"
for s in "$@"; do
    PAX_TREE=$snap flock "$HOME/lanes/kasumi-cores-0-3.lock" bash "$L/pax/notes/px80/run-suite.sh" "$s" "$name-$s" >> "$L/runs/$name.out" 2>&1
done
echo "batch $name done $(date -Is)" >> "$L/runs/$name.out"
