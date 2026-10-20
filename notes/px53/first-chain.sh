#!/bin/bash
# px53: the first boot at the pins (the build from e2906fb's tree), booted
# by that tree's own suite and keys; and the core limits first.
L=$HOME/lanes/px53
bash $L/pax/notes/px53/limits.sh first $L/ev/limits
echo limits-done
[ -d $L/pax-first ] || git -C $L/pax worktree add -q $L/pax-first e2906fb
git -C $L/pax-first log --oneline -1
cd $L/pax-first
export PAX_CACHE=$L/cache PAX_BUILD=$L/build/first PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
W=$L/build/first/mpx5-jobs
tests/mpx5-jobs --only linux --images $W > $L/build/first.linux.log 2>&1
echo "linux: $? ($(tail -n 1 $L/build/first.linux.log))"
taskset -c 0-3 tests/mpx5-jobs --images $W --tier native --firmware bios > $L/build/first.boot.log 2>&1
echo "boot: $?"
grep -a 'FAIL' $L/build/first.boot.log | cut -c1-600 | head -40
tail -n 1 $L/build/first.boot.log
