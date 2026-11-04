#!/usr/bin/env bash
# px89: check.sh for each kmain named; wolf's keyword list once.
set -uo pipefail
w=$(tools/fetch-wolf | tail -n 1)
"$w" --explain E0008 2>&1 | grep -i -A12 'keyword' | head -30
rc=0
for k in "$@"; do bash /home/mfwolffe/lanes/px89/scripts/check.sh "$k" || rc=1; done
exit $rc
