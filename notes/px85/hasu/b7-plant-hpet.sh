#!/usr/bin/env bash
# px85 batch 7: the plant px85-plant-hpet (commit P), locally: F1's legs,
# native, both firmwares; predicted red by name at the first HPET leg.
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu P=$1
T=$L/wt-plant-hpet
git -C "$L/pax" fetch -q origin px85-plant-hpet
git -C "$L/pax" worktree remove --force "$T" 2>/dev/null
git -C "$L/pax" worktree add -q --detach "$T" "$P"
"$H/ctr.sh" plant-hpet "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/plant-hpet" native
