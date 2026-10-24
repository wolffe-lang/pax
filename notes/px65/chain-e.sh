#!/bin/bash
# px65, kasumi: the fifth chain, after the rebase onto trunk f0617320
# (px66): the kernel's cost against the new trunk (every kernel on the
# native tier, kmain_console and kmain_session on the release tier), then
# the dev ISO (dev-all.sh) and the playground, its ISO and since px66 its
# disk (play-all.sh), at one commit. The scripts are read from the w-e
# worktree, so a reset of the clone does not move them.   chain-e.sh COMMIT
L=$HOME/lanes/px65; E=$L/w-e; P=$E/notes/px65; C=$1
echo "chain-e: $(git -C "$E" rev-parse HEAD) for $C, $(date -Is)"; uptime
t0=$(date +%s); PX65_TREE=$E bash "$P/cost.sh" native > "$L/out/cost-native-e.txt" 2>&1; echo "cost native rc=$? $(( $(date +%s) - t0 ))s"
t0=$(date +%s); PX65_TREE=$E bash "$P/cost.sh" release kmain_console kmain_session > "$L/out/cost-release-e.txt" 2>&1; echo "cost release rc=$? $(( $(date +%s) - t0 ))s"
t0=$(date +%s); bash "$P/dev-all.sh" "$C" > "$L/out/dev-all-e.txt" 2>&1; echo "dev-all rc=$? $(( $(date +%s) - t0 ))s"
t0=$(date +%s); bash "$P/play-all.sh" "$C" > "$L/out/play-all-e.txt" 2>&1; echo "play-all rc=$? $(( $(date +%s) - t0 ))s"
echo "chain-e: done $(date -Is)"
