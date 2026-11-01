#!/usr/bin/env bash
# px85 batch 3, at a branch commit S: F1's clock legs; F8 at S with no load
# (5 runs), then trunk under the harsher 200/50 load (20), then S under the
# 50/50 load (20) and the 200/50 load (20).
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu S=$1
s=${S:0:8} T=$L/wt-${S:0:8}
[ -d "$T" ] || git -C "$L/pax" worktree add -q --detach "$T" "$S"
I=$L/images/head-$s-release
"$H/ctr.sh" clock-$s "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/clock-$s" native
"$H/ctr.sh" control-$s "$T" -- bash "$H/stall-job.sh" "$T" "$L/runs/head-$s-control" --runs 5 --no-load --images "$I"
"$H/ctr.sh" trunk-200 "$L/trunk" -- bash "$H/stall-job.sh" "$L/trunk" "$L/runs/trunk-load-200-50" --runs 20 --load 200/50 --images "$L/runs/trunk-load/images"
"$H/ctr.sh" load50-$s "$T" -- bash "$H/stall-job.sh" "$T" "$L/runs/head-$s-load-50-50" --runs 20 --load 50/50 --images "$I"
"$H/ctr.sh" load200-$s "$T" -- bash "$H/stall-job.sh" "$T" "$L/runs/head-$s-load-200-50" --runs 20 --load 200/50 --images "$I"
