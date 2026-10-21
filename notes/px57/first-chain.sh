#!/bin/bash
# px57 on kasumi: the first build and boot at the new pins (the pins alone, before any new probe, suite or
# change): the kernel's cost (trunk ebbef86 at 0.2.33 against the branch at 0.2.34), mkw and tour, then the
# suites one after the other (native, BIOS; builds in px13-ubuntu on cpus 4-15, boots under taskset -c 0-3).
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}; P=$X/notes/px57
cd $X && echo "tree: $(git log --oneline -1) $(git status --short | tr '\n' ' ')"
echo "== cost"; bash $P/cost.sh
echo "== mkw, tour"; bash $P/mkw.sh mkw1
bash $P/regress.sh first mpx5-jobs mpx5-lope mpx5-accounts mpx3-shell mpx3-tree mpx3-boreutils mpx5-users mpx3-speaker mpx3-console mpx3-screen mpx3-threads
echo "first-chain: done"
