#!/bin/bash
# px65, kasumi: the third chain, at the head after the first two: mpx5-bore
# again (its keys within the console's columns), mpx5-wolf with the
# lane's two-build dev compiler (PAX_DEV_WOLF_DIR, never rebuilt here:
# user/wolf.sums holds its bytes, verify-bins checks them), then
# mpx5-jobs built at the head and px57's recordings redone on real
# root's guest twice, each compared with the committed one.
#   chain-c.sh TAG   (the tree: PX65_TREE)
L=$HOME/lanes/px65; P=$L/pax/notes/px65; T=${1:-c}
bash "$P/regress.sh" "$T" mpx5-bore
PX65_BUILD_ENV="-e PAX_DEV_WOLF_DIR=$L/wolf-out" bash "$P/regress.sh" "$T" mpx5-wolf
bash "$P/build.sh" mpx5-jobs "$T-mpx5-jobs" --only build --tier native
bash "$P/rec-twice.sh" "$T-mpx5-jobs" > "$L/ev/rec-twice-$T.out" 2>&1
echo "rec-twice rc=$?"; grep -c twice-same "$L/ev/rec-twice-$T.out"; grep -E "DIFFER|MISSING" "$L/ev/rec-twice-$T.out" | head -40
echo "chain-c: done $(date -Is)"
