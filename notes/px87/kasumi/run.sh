#!/usr/bin/env bash
# px87 on kasumi, inside the container: run commands in a worktree pinned to a commit, with the lane's cache.
#   run.sh WORKTREE BUILD_DIR STEP_NAME CMD [ARGS...] [::: STEP_NAME CMD [ARGS...]]...
# Each step prints `END <step> exit=N`; the first nonzero step stops the run (its status is the run's).
set -uo pipefail
W=$1 B=$2; shift 2
L=/home/mfwolffe/lanes/px87
cd "$W" || exit 2
export PAX_CACHE=$L/cache PAX_BUILD=$B TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0
mkdir -p "$B" "$TMPDIR"
PAX_WOLF=$(tools/fetch-wolf) || exit 2
export PAX_WOLF
printf '%s commit %s (%s)\n' "$(date -u +%FT%TZ)" "$(git rev-parse HEAD)" "$(git status --porcelain --untracked-files=no | wc -l) dirty paths"
while [ $# -gt 0 ]; do
    step=$1; shift
    cmd=()
    while [ $# -gt 0 ] && [ "$1" != ":::" ]; do cmd+=("$1"); shift; done
    [ $# -gt 0 ] && shift
    printf '%s START %s: %s\n' "$(date -u +%FT%TZ)" "$step" "${cmd[*]}"
    start=$SECONDS
    rc=0
    "${cmd[@]}" || rc=$?
    printf '%s END %s exit=%s (%s s)\n' "$(date -u +%FT%TZ)" "$step" "$rc" "$((SECONDS - start))"
    [ "$rc" = 0 ] || exit "$rc"
done
