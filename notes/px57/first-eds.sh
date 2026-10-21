#!/bin/bash
# px57 on kasumi: PAX's first boot of mpx5-jobs' eds image (edwolf and hostq), the suite built on a worktree
# of the branch (cpus 8-15), its Linux side, then the eds boot alone (PAX_JOBS_BOOTS=eds:serial) under
# taskset -c 4-7 (four cpus; 0-3 held by the first chain's boots).   first-eds.sh TAG
L=$HOME/lanes/px57; t=$1; export PX57_TREE=$L/w-$t PX57_BUILD_CPUS=8-15 PX57_CPUS=4-7 PAX_JOBS_BOOTS=eds:serial
PX57_BUILD_ENV="-e PAX_JOBS_BOOTS=eds:serial" bash $PX57_TREE/notes/px57/build.sh mpx5-jobs $t --only build --tier native
bash $PX57_TREE/notes/px57/boot.sh mpx5-jobs $t --tier native --firmware bios
grep -a -E 'PASS|FAIL' $L/build/$t.boot.log | cut -c1-400
