#!/usr/bin/env bash
# notes/px130/rig/take.sh CHECKOUT MANIFEST OUTPUT [RECORDER ARGS…] — one record of MANIFEST (a file
# beside this one) at CHECKOUT's head (a clean worktree of the commit under test, never a live
# tree): the host file's LOCKS taken in its order, one long flock each (none for a light take, which
# runs under the host's light-slot helper and its lock), then the recorder (REC) in steps mode with
# --keep-going and --preflight. PAX_BUILD is the lane's pb-<sha8>-<manifest>. (px123's shape.)
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
here=$(cd "$(dirname "$0")" && pwd)
: "${PX130_HOST:?PX130_HOST names the host file}"
# shellcheck disable=SC1090
. "$PX130_HOST"
: "${L:?}" "${P:?}" "${LOCKS?}" "${REC:?}"
co=${1:?a checkout} man=${2:?a manifest} out=${3:?the record}; shift 3
cd "$co" || exit 2
PAX_BUILD=$L/pb-$(git rev-parse --short=8 HEAD)-$(basename "$man" .manifest)
PATH=$(dirname "$P"):$PATH
export PAX_BUILD PX130_HOST PATH
wrap=()
for lock in $LOCKS; do wrap+=(flock -w 21600 "$lock"); done
echo "take: $(git rev-parse HEAD) $man -> $out; waiting on ${LOCKS:-no lock (light)} at $(date -u +%FT%TZ)"
"${wrap[@]}" bash "$REC" --output "$out" --steps "$here/$man" --keep-going \
    --preflight "bash $here/step.sh preflight" "$@"
rc=$?
echo "take: exit $rc at $(date -u +%FT%TZ)"
exit "$rc"
