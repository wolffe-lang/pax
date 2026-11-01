#!/usr/bin/env bash
# px85 batch 1: trunk 8495bdc0's F8 (release), 5 runs with no load (the
# control), then 20 under the 50/50 load.
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu
"$H/ctr.sh" trunk-control "$L/trunk" -- bash "$H/stall-job.sh" "$L/trunk" "$L/runs/trunk-control" --runs 5 --no-load
"$H/ctr.sh" trunk-load "$L/trunk" -- bash "$H/stall-job.sh" "$L/trunk" "$L/runs/trunk-load" --runs 20 --load 50/50
