#!/bin/bash
# px57 on kasumi: the first build, Linux side and PAX boot of the two new suites, on a worktree of the
# branch: mpx5-aspen (built in px13-ubuntu) and mpx5-lupin (built in the throwaway Rust image, which is
# px13-ubuntu with rustup inside it), native BIOS; builds on cpus 8-15, boots under taskset -c 4-7 (four
# cpus; 0-3 held by the first chain's).   new-suites.sh TAG
L=$HOME/lanes/px57; t=$1; export PX57_TREE=$L/w-$t PX57_BUILD_CPUS=8-15 PX57_CPUS=4-7
bash $PX57_TREE/notes/px57/build.sh mpx5-aspen $t-aspen --only build --tier native \
  && bash $PX57_TREE/notes/px57/boot.sh mpx5-aspen $t-aspen --tier native --firmware bios
echo "== mpx5-aspen: $?"
PX57_BUILD_IMAGE=localhost/px57-rust bash $PX57_TREE/notes/px57/build.sh mpx5-lupin $t-lupin --only build --tier native \
  && bash $PX57_TREE/notes/px57/boot.sh mpx5-lupin $t-lupin --tier native --firmware bios
echo "== mpx5-lupin: $?"
