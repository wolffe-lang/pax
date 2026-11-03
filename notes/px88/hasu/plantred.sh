#!/usr/bin/env bash
# px88: the plant red by name. The suite's forks session at the plant's
# commit (px88-plant-fork: a fork's child given its parent's pid), native
# BIOS. Given a nonzero answer the child takes the parent's branch at the
# first fork: it never prints `fork: child`, and its waitpid of the pid it
# was given answers ECHILD, so the session's second line is `fork: child
# status 0` where Linux's are `fork: child` and `fork: child status 7`; both
# then wait as parents and the session never halts (K5). That signature,
# with K1 red, is the plant's red; this step exits 0 when it holds, 1
# otherwise (a green plant, or a red of another kind, is this step's failure).
# The first form (gauntlet2) looked for the `what fork answered the child:`
# row, which the plant's hang means is never reached.
#   plantred.sh BLOCK RUN SHA             run the session at SHA, then match
#   plantred.sh --match SESSION BOOTLOG   the match alone (its own proof)
set -uo pipefail
match() { # session bootlog -> 0 when the plant's red, by name
    local out=$1 log=$2
    grep -q 'FAIL K1 native bios forks: the output differs' "$log" || { echo "match: K1 not red"; return 1; }
    [ "$(sed -n 2p "$out")" = 'fork: child status 0' ] || { echo "match: line 2 is '$(sed -n 2p "$out")', not 'fork: child status 0'"; return 1; }
    ! grep -qx 'fork: child' "$out" || { echo "match: the child printed 'fork: child'"; return 1; }
    echo "match: K1 red; line 2 'fork: child status 0'; no 'fork: child': the child took the parent's branch"
}
if [ "${1:-}" = --match ]; then match "$2" "$3"; exit $?; fi
B=$1 RUN=$2 SHA=$3
S=/home/mfwolffe/lanes/px88/scripts
L=/home/mfwolffe/lanes/px88
bash "$S/suite.sh" "$B" "$RUN" "$SHA" native bios:native:forks
src=$?
log="$L/build/$RUN/$RUN-boot-bios-native-forks.log"
out="$L/build/$RUN/mpx5-forks-native-bios-forks.session"
rc=0
[ "$src" != 0 ] || { echo "the suite was green at the plant"; rc=1; }
match "$out" "$log" || rc=1
grep -E 'FAIL K[0-9]' "$log" | cut -c1-200
echo "$(date -u +%FT%TZ) END $RUN-red exit=$rc (the suite's own exit $src)"
exit "$rc"
