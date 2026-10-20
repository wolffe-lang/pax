#!/bin/bash
# px53 on kasumi: the suites beside mpx5-jobs at the head, one after
# another (chain-suites.sh: built in px13-ubuntu on cpus 4-15, booted
# native BIOS under taskset -c 0-3), then tests/mkw and tests/tour
# (mkw.sh), then the kernel's cost against trunk (cost.sh).
L=$HOME/lanes/px53
P=$L/pax
git -C $P log --oneline -1
bash $P/notes/px53/chain-suites.sh native mpx3-shell mpx3-tree mpx5-accounts mpx3-boreutils mpx5-users mpx3-speaker mpx3-console mpx3-screen mpx3-threads
echo "== mkw, tour"
bash $P/notes/px53/mkw.sh
echo "== cost"
bash $P/notes/px53/cost.sh > $L/ev/kasumi-kernel-cost.txt 2>&1
cat $L/ev/kasumi-kernel-cost.txt
echo rest-done
