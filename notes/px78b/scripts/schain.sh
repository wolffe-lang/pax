#!/usr/bin/env bash
# px78b: the test stick after the branch's own leg is green: build, the line, the leg on a copy.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
printf '%s\n' "$$" > $L/schain.pid
while kill -0 "$(cat $L/chain.pid)" 2>/dev/null; do python3 -I -c 'import time; time.sleep(15)'; done
[ "$(cat $L/metal-run.exit 2>/dev/null)" = 0 ] || { printf '%s SCHAIN NOT STARTED: the branch leg is not green\n' "$(date -u +%FT%TZ)"; exit 3; }
for s in sbuild sline sleg; do
 printf '%s START %s\n' "$(date -u +%FT%TZ)" "$s"
 bash $L/$s.sh; rc=$?
 printf '%s STEP %s exit=%s\n' "$(date -u +%FT%TZ)" "$s" "$rc"; echo $rc > $L/$s.exit
 [ $rc = 0 ] || { echo "SCHAIN STOPPED at $s"; exit $rc; }
done
printf '%s SCHAIN DONE\n' "$(date -u +%FT%TZ)"
