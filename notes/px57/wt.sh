#!/bin/bash
# px57 on kasumi: a detached worktree of the branch's head at ~/lanes/px57/w-TAG (fetched first), so a long
# job runs on a tree nothing pulls into.   wt.sh TAG [REV]
L=$HOME/lanes/px57; t=$1; rev=${2:-origin/px57}
cd $L/pax && git fetch -q origin px57 && git worktree add -q --detach $L/w-$t $rev && git -C $L/w-$t log --oneline -1
