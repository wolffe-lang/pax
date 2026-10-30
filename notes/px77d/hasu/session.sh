#!/usr/bin/env bash
# px77d: run a command under hasu block A's lock (shared with px77c), released when it ends.
set -uo pipefail
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77d acquiring block A\n' "$(date -u +%FT%TZ)"
until flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(20)'
done
printf '%s block A acquired: %s\n' "$(date -u +%FT%TZ)" "$*"
rc=0
bash -c "$*" || rc=$?
flock -u 9
exec 9>&-
printf '%s block A RELEASED rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
exit $rc
