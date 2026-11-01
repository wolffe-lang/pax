#!/usr/bin/env bash
# px85: one stall batch inside the block-A container (run by ctr.sh).
#   stall-job.sh TREE OUT STALL-ARGS...
# wolf from the tree's own pin (tools/fetch-wolf, the lane's cache), then
# the branch's harness against TREE.
set -euo pipefail
tree=$1 out=$2; shift 2
PAX_WOLF=$("$tree/tools/fetch-wolf")
export PAX_WOLF
echo "wolf: $("$PAX_WOLF" --version | head -n 1)"
exec bash /home/mfwolffe/lanes/px85/pax/tests/mpx6-firmware.d/stall --tree "$tree" --out "$out" "$@"
