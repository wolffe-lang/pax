#!/usr/bin/env bash
# px85 batch 2: F1's clock legs at the rows commit 8223a994 (base + the
# test words + the legs, before the fix): predicted red on all five.
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu T=$L/wt-8223a994
[ -d "$T" ] || git -C "$L/pax" worktree add -q --detach "$T" 8223a994
"$H/ctr.sh" clock-red "$T" -- bash "$H/clock-legs.sh" "$T" "$L/build/clock-red" native
