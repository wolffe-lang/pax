#!/usr/bin/env bash
# px87: the lane's rebase onto trunk, commit by commit. For each pre-rebase commit OLD (BASE..OLDHEAD) and
# its rebased commit NEW (TRUNK..NEWHEAD), in order: the subjects equal, the patches equal (git patch-id
# --stable; or, where the rebase resolved a conflict and so moved a hunk's context, the same added and removed
# lines, marked `context`), and the trees differ exactly by trunk's own paths since BASE; any other difference
# stops the script. Prints the table: old8 new8 old new [context] subject.
#   map.sh BASE OLDHEAD TRUNK NEWHEAD
set -euo pipefail
base=$1 oldhead=$2 trunk=$3 newhead=$4
old=($(git rev-list --reverse "$base..$oldhead"))
new=($(git rev-list --reverse "$trunk..$newhead"))
[ "${#old[@]}" = "${#new[@]}" ] || { echo "map.sh: ${#old[@]} old commits, ${#new[@]} new" >&2; exit 1; }
trunk_paths=$(git diff --name-only "$base" "$trunk" | sort)
printf '# trunk since %s: %s\n' "${base:0:8}" "$(echo $trunk_paths)"
for i in "${!old[@]}"; do
    o=${old[$i]} n=${new[$i]}
    so=$(git log -1 --format=%s "$o") sn=$(git log -1 --format=%s "$n")
    [ "$so" = "$sn" ] || { echo "map.sh: subject differs at $o" >&2; exit 1; }
    po=$(git show "$o" | git patch-id --stable | cut -d' ' -f1)
    pn=$(git show "$n" | git patch-id --stable | cut -d' ' -f1)
    mark=
    if [ "$po" != "$pn" ]; then
        lo=$(git show --format= "$o" | grep -E '^[-+]' | grep -vE '^(\+\+\+|---) ' | sort)
        ln=$(git show --format= "$n" | grep -E '^[-+]' | grep -vE '^(\+\+\+|---) ' | sort)
        [ "$lo" = "$ln" ] || { echo "map.sh: patch differs at $o" >&2; exit 1; }
        mark='context '
    fi
    d=$(git diff --name-only "$o" "$n" | sort)
    [ "$d" = "$trunk_paths" ] || { echo "map.sh: tree of $n differs from $o beyond trunk's paths: $d" >&2; exit 1; }
    printf '%s %s %s %s %s%s\n' "${o:0:8}" "${n:0:8}" "$o" "$n" "$mark" "$so"
done
