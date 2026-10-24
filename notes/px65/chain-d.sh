#!/bin/bash
# px65, kasumi: the fourth chain, at the head with every fix: mpx5-jobs
# booted (every image) against the recordings as they now stand,
# mpx5-bore and mpx5-scent with their rows corrected, and the suites
# whose builds run their Linux side in a chroot (privileged container):
# mpx3-boreutils, mpx3-shell, mpx3-tree.   chain-d.sh TAG   (PX65_TREE)
L=$HOME/lanes/px65; P=$L/pax/notes/px65; T=${1:-d}
bash "$P/regress.sh" "$T" mpx5-bore mpx5-scent mpx5-jobs
PX65_BUILD_FLAGS=--privileged bash "$P/regress.sh" "$T" mpx3-boreutils mpx3-shell mpx3-tree
echo "chain-d: done $(date -Is)"
