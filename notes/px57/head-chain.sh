#!/bin/bash
# px57 on kasumi: the suites at the head (the code as at the head), on a worktree of the branch, builds on
# cpus 8-15 and boots under taskset -c 4-7 (four cpus) beside the first chain's 0-3: mpx5-jobs (every image,
# eds among them), then mkw and tour, then tests/ci-plan.   head-chain.sh TAG
L=$HOME/lanes/px57; t=$1; export PX57_TREE=$L/w-$t PX57_BUILD_CPUS=8-15 PX57_CPUS=4-7
cd $PX57_TREE && echo "tree: $(git log --oneline -1)"
bash $PX57_TREE/notes/px57/regress.sh $t mpx5-jobs
python3 tests/ci-plan > $L/build/$t-ci-plan.out 2>&1; echo "ci-plan: $? ($(grep -c PASS $L/build/$t-ci-plan.out) PASS)"
