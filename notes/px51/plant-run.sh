#!/bin/bash
# px51 on kasumi: a plant's kernel with the pjobs, pjobs-user and groups images: the plant branch's tree built
# (mpx5-jobs --only build, px13-ubuntu, cpus 4-15), then those three boots alone (PAX_JOBS_BOOTS) by the branch's
# own tests/mpx5-jobs from px51's tree (the same recordings), under taskset -c 0-3.
#   plant-run.sh BRANCH TAG
L=$HOME/lanes/px51
br=$1 T=$2
B=$L/build/$T
rm -rf $B $L/$T && mkdir -p $B
git -C $L/pax fetch -q origin $br && git -C $L/pax worktree add -q --detach $L/$T origin/$br || exit 2
echo "tree: $(git -C $L/$T log --oneline -1)"
podman run --rm --privileged --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/$T && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/mpx5-jobs --only build --tier native" > $B.build.log 2>&1
echo "build: $? ($(tail -n 1 $B.build.log | cut -c1-200))"
cd $L/pax
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
tests/mpx5-jobs --only linux --images $B/mpx5-jobs > $B.linux.log 2>&1; echo "linux: $?"
PAX_JOBS_BOOTS="pjobs:serial pjobs-user:serial groups:serial" taskset -c 0-3 tests/mpx5-jobs --images $B/mpx5-jobs --tier native --firmware bios > $B.boot.log 2>&1
echo "boot: $?"
grep -a 'FAIL' $B.boot.log | cut -c1-300 | sort | uniq -c | sort -rn | head -60
git -C $L/pax worktree remove --force $L/$T
