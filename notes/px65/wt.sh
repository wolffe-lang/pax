#!/bin/bash
# px65, kasumi: a detached worktree of a branch commit at ~/lanes/px65/w-TAG
# (fetched first), so a long job runs on a tree nothing pulls into.
#   wt.sh TAG REV
L=$HOME/lanes/px65; t=$1; rev=$2
cd "$L/pax" && git fetch -q origin px65 && git worktree add -q --detach "$L/w-$t" "$rev" && git -C "$L/w-$t" log --oneline -1
