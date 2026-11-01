#!/usr/bin/env bash
# px85 batch 6: F8 under the freeze load (freeze.sh: the container frozen
# 300 ms of every second by the cgroup freezer), trunk 8495bdc0 then the
# branch commit S, 20 runs each, five at once.
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu S=$1
s=${S:0:8} T=$L/wt-${S:0:8}
[ -d "$T" ] || git -C "$L/pax" worktree add -q --detach "$T" "$S"
desc='the whole container frozen 300 ms (370-530 ms measured) then run 700 ms, again, by podman pause/unpause (notes/px85/hasu/freeze.sh)'
for side in trunk head; do
    if [ $side = trunk ]; then tree=$L/trunk name=trunk-freeze imgs=$L/runs/trunk-load/images
    else tree=$T name=freeze-$s imgs=$L/images/head-$s-release; fi
    out=$L/runs/$name
    rm -rf "$out"; mkdir -p "$out"
    "$H/freeze.sh" "$name" "$out" 300 700 > "$L/logs/$name.freeze.log" 2>&1 &
    fz=$!
    "$H/ctr.sh" "$name" "$tree" -- bash "$H/stall-job.sh" "$tree" "$out" --runs 20 --external "$desc" --images "$imgs"
    touch "$out/rounds.done"
    wait "$fz"
    cat "$L/logs/$name.freeze.log"
done
