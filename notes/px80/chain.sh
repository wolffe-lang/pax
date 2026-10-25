#!/usr/bin/env bash
# px80: the lane's kasumi work after the lld build, in order, detached: the
# dev ISO end to end, the Linux link rows, the bundle staged, the boot batch,
# then every kernel's identity pass (last: the longest, and the one the block
# can spare first). Each step under the CPUs 0-3 block's lock (released
# between steps; dev-all and the batch take it per step themselves).
#   chain.sh COMMIT SUITE...     log $L/logs/chain.log, exit marker $L/chain.exit
set -u
L=$HOME/lanes/px80
C=$1; shift
LOCK=$HOME/lanes/kasumi-cores-0-3.lock
printf '%s\n' $$ > "$L/chain.pid"
rm -f "$L/chain.exit"
step() { local n=$1; shift; local t0; t0=$(date +%s); "$@" > "$L/logs/$n.log" 2>&1; local rc=$?; echo "$n rc=$rc $(( $(date +%s) - t0 ))s $(date -Is)"; tail -n 6 "$L/logs/$n.log"; return $rc; }
echo "chain at $C start $(date -Is)"
git -C "$L/pax" fetch -q origin && git -C "$L/pax" checkout -q --detach "$C" || { echo 2 > "$L/chain.exit"; exit 2; }
step dev-all bash "$L/pax/notes/px80/dev-iso/dev-all.sh" "$C"
step m2-linux flock "$LOCK" bash "$L/pax/notes/px80/m2-linux.sh"
step stage bash "$L/pax/notes/px80/stage.sh"
step batch bash "$L/pax/notes/px80/batch.sh" b1 "$@"
tail -n $(( $# + 2 )) "$L/runs/b1.out"
step kernels flock "$LOCK" bash "$L/pax/notes/px80/kernels.sh"
echo "chain done $(date -Is)"
echo 0 > "$L/chain.exit"
