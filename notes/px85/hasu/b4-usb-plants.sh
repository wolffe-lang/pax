#!/usr/bin/env bash
# px85 batch 4: pax#261's three faults planted in the guest, one at a time,
# each in a scratch worktree at the branch commit S (never committed), F8
# run once with no load: the repeat row must fail by the fault's name.
#   lost   kernel/xhci's software repeat stops after its first report
#   wrong  the repeat sends the next scancode (0x1f, `s`) for `a`
#   stuck  the repeat presses Left Shift first and nothing releases it
L=/home/mfwolffe/lanes/px85 H=$L/pax/notes/px85/hasu S=$1
call='console.key_event(usb_keys.code(usage), true, true)'
for p in lost wrong stuck; do
    T=$L/plant-$p
    git -C "$L/pax" worktree remove --force "$T" 2>/dev/null
    git -C "$L/pax" worktree add -q --detach "$T" "$S"
    case $p in
        lost) new="$call; put(d, REPEAT, 0)";;
        wrong) new='console.key_event(usb_keys.code(usage) + 1, true, true)';;
        stuck) new="console.key_event(0x2a, true, true); $call";;
    esac
    python3 -I - "$T/kernel/xhci/xhci.lu" "$call" "$new" <<'PY'
import sys
p, old, new = sys.argv[1:]
s = open(p).read()
assert s.count(old) == 1, 'the repeat call is not unique'
open(p, 'w').write(s.replace(old, new))
PY
    mkdir -p "$L/runs"
    git -C "$T" diff > "$L/runs/plant-$p.diff"
    "$H/ctr.sh" plant-$p "$T" -- bash "$H/stall-job.sh" "$T" "$L/runs/plant-$p" --runs 1 --no-load --cpus 1 --tier release
    grep -a -E 'RuntimeError|FAIL' "$L/runs/plant-$p/run-01/leg.log" | sed "s/^/plant $p: /"
done
