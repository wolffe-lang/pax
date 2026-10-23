#!/bin/bash
# px65, kasumi: the head's chain (every pin moved): boreutils' new
# utilities first (mpx5-bore: build, the container's sessions, PAX), their
# census by strace from that build's binaries, then each tool's suite
# and the suites the pins reach, against their references.
#   chain-b.sh TAG   (the tree: PX65_TREE)
L=$HOME/lanes/px65; P=$L/pax/notes/px65; T=${1:-b}
bash "$P/regress.sh" "$T" mpx5-bore
mkdir -p "$L/ev"
bash "$P/census.sh" "$L/build/$T-mpx5-bore/mpx5-bore/bore" "$L/ev/census-$T" > "$L/ev/census-$T.out" 2>&1
echo "census rc=$? $(tail -n 2 "$L/ev/census-$T.out" | tr '\n' ' ')"
bash "$P/regress.sh" "$T" mpx5-scent mpx5-aspen mpx5-lope mpx5-lupin mpx3-boreutils mpx5-accounts mpx5-pelt
echo "chain-b: done $(date -Is)"
