#!/usr/bin/env bash
# px88: the usage probe ends, never hangs, on a kernel that cannot fork: the
# suite's usage session at SHA (base 3df2ae18's kernel, fork and getrusage
# -ENOSYS, with the head's user/elf/usage.c: branch px88-hangcheck, a lane-only
# commit), native BIOS. Its rows are red there by design; this step holds only
# that the session ran to its end (K5 PASS, no NOT HALTED), and exits 0 then.
# At 3df2ae18's own probe the same session was NOT HALTED within 600 s (r2-B2).
#   hang.sh BLOCK RUN SHA
set -uo pipefail
B=$1 RUN=$2 SHA=$3
S=/home/mfwolffe/lanes/px88/scripts
L=/home/mfwolffe/lanes/px88
bash "$S/suite.sh" "$B" "$RUN" "$SHA" native bios:native:usage
src=$?
log="$L/build/$RUN/$RUN-boot-bios-native-usage.log"
rc=0
grep -q 'PASS K5 native bios usage: init ended' "$log" || rc=1
! grep -q 'NOT HALTED' "$log" || rc=1
grep -E 'K1|K5' "$log" | cut -c1-200
echo "$(date -u +%FT%TZ) END $RUN-ends exit=$rc (the suite's own exit $src: its rows are red at this kernel by design)"
exit "$rc"
