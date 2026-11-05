#!/usr/bin/env bash
# px89: a gauntlet record at one commit, detached (pid, log, exit marker):
#   gaunt-launch.sh BLOCK NAME SHA [--plant ROW... --base GREEN] -- SUITE...
# (GAUNTLET=guard-gauntlet.sh in the environment: that script in place of
# gauntlet.sh, the mpx4-ready guard's record.)
# A clean worktree at SHA (records/wt-NAME), then planning's
# gauntlet-record.sh --output records/NAME.log -- bash gauntlet.sh BLOCK SUITE...
set -euo pipefail
L=/home/mfwolffe/lanes/px89
S=$L/scripts
B=$1 N=$2 SHA=$3; shift 3
rec=()
while [ "${1:-}" != -- ]; do rec+=("$1"); shift; done
shift
G="git -c commit.gpgsign=false"
mkdir -p "$L/records" "$L/logs"
flock "$L/git.lock" $G -C "$L/pax" fetch -q origin '+refs/heads/px89*:refs/remotes/origin/px89*'
full=$($G -C "$L/pax" rev-parse "$SHA^{commit}")
WT=$L/records/wt-$N
if [ ! -d "$WT" ]; then
    # No remote branch at SHA (a commit brought by a bundle, not pushed):
    # a detached worktree; grep's empty answer is not an error here.
    branch=$($G -C "$L/pax" branch -r --points-at "$full" | sed -n 's|^ *origin/||p' | { grep '^px89' || true; } | head -n 1)
    if [ -n "$branch" ]; then
        flock "$L/git.lock" $G -C "$L/pax" worktree add -q -B "$branch" "$WT" "$full"
    else
        flock "$L/git.lock" $G -C "$L/pax" worktree add -q --detach "$WT" "$full"
    fi
fi
[ "$($G -C "$WT" rev-parse HEAD)" = "$full" ]
rm -f "$L/logs/$N.exit"
# The scripts as they are now, for this record alone: a bash script is
# read as it runs, so an edit of the shared copies would reach a running
# gauntlet mid-file.
SNAP=$L/records/scripts-$N
rm -rf "$SNAP"; mkdir -p "$SNAP"; cp "$S"/*.sh "$SNAP/"
S=$SNAP
setsid -f bash -c '
    L=$1 S=$2 B=$3 N=$4 WT=$5; shift 5
    echo $$ > "$L/logs/$N.pid"
    cd "$WT"
    rc=0
    python3 --version > /dev/null 2>&1
    bash "$S/gauntlet-record.sh" --output "$L/records/$N.log" "$@" || rc=$?
    echo "$rc" > "$L/logs/$N.exit"
' px89-gaunt "$L" "$S" "$B" "$N" "$WT" ${rec[@]+"${rec[@]}"} -- bash "$S/${GAUNTLET:-gauntlet.sh}" "$B" "$@" < /dev/null > "$L/logs/$N.log" 2>&1
n=0
while [ ! -s "$L/logs/$N.pid" ] && [ $n -lt 50 ]; do sleep 0.1; n=$((n + 1)); done
echo "launched gauntlet $N at $full on block $B: pid $(cat "$L/logs/$N.pid" 2>/dev/null), record $L/records/$N.log, log $L/logs/$N.log"
