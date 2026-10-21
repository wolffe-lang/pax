#!/bin/bash
# px57 on kasumi: mpx5-jobs built (--only build, native) on a worktree of the branch, then real root's
# recordings of its eds image twice (vm-rec.sh).   eds-chain.sh TAG   (the tree: ~/lanes/px57/w-TAG)
L=$HOME/lanes/px57; t=$1; export PX57_TREE=$L/w-$t
bash $PX57_TREE/notes/px57/build.sh mpx5-jobs $t-jobs --only build --tier native
bash $PX57_TREE/notes/px57/vm-rec.sh $L/build/$t-jobs/mpx5-jobs/eds.cpio $L/vm/$t
