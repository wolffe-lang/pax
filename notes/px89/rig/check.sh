#!/usr/bin/env bash
# px89: the kernel's compile errors only (warnings left out), for one kmain:
#   check.sh KMAIN  (inside the container, in a worktree)
set -uo pipefail
k=${1:-kmain_sockets}
w=$(tools/fetch-wolf | tail -n 1)
out=$(mktemp -d "$TMPDIR/px89-check.XXXXXX")
cd kernel && "$w" build "$k.lu" --target x86_64-unknown-none --emit=obj -o "$out/k.o" --error-limit=0 2>&1 | awk '/^error/ { on = 1 } /^warning/ { on = 0 } on' | head -120
rc=${PIPESTATUS[0]}
rm -rf "$out"
echo "  check $k: wolf exit $rc"
exit $rc
