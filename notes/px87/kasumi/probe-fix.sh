#!/usr/bin/env bash
# px87: before the final runs, in one hold (run by hostchain.sh): tests/mpx6-triage whole at the new head, and the
# stick qualification (the new head's notes/px87/stick/qual.py) against the stick already built at OLD.
#   probe-fix.sh WORKTREE OLD_STICK_DIR OLD_HEAD
set -uo pipefail
W=$1 SO=$2 OLD=$3
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; }
step triage ctr bash "$L/bin/run.sh" "$W" "$L/b/probe-triage" triage tests/mpx6-triage --tier native --firmware both
for leg in serial kasumi; do
    step "qual-$leg" ctr bash -c "cd $W && export PAX_CACHE=$L/cache TMPDIR=$L/tmp && python3 -I notes/px87/stick/qual.py $W $SO/sout/pax-stick-${OLD:0:8}.img $SO/sout/kernel/kmain_console.elf $OLD $L/b/probe-qual-$leg $leg"
done
