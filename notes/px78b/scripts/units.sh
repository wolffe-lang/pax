#!/usr/bin/env bash
# px78b: the installer units at the red head (tests only) and the green head.
L=/home/mfwolffe/lanes/px78b
for side in red green; do
 src=$L/pax; [ $side = green ] || src=$L/red
 for u in planner ui; do
  bash $L/ctr.sh units-$side-$u localhost/px75-ubuntu:2 0 bash -c "cd $src && git log --oneline -1 && tests/mpx6-install --only $u --work $L/w-units-$side"
 done
done
