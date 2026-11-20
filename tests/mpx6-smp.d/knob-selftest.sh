#!/usr/bin/env bash
# tests/mpx6-smp.d/knob-selftest.sh — PAX_SMP=N, the harness's processor count (no QEMU: a stand-in that
# says what it was asked). Every boot a suite makes through tools/qemu-run (and so tools/qemu-halt), and
# tools/tour's own two QEMU starts, run at N processors when PAX_SMP=N, unless the caller's own QEMU
# arguments name -smp; unset, nothing changes. Stage 2's record reruns existing suites this way.
#
#   bash tests/mpx6-smp.d/knob-selftest.sh
#
# Rows (each `PASS KNOB-…` or `FAIL KNOB-…`; exit 1 if any failed):
#   KNOB-RUN        qemu-run with PAX_SMP=4 asks QEMU for `-smp 4`, and its .meta says so
#   KNOB-CALLER     the caller's own `-smp 2` wins, and PAX_SMP adds no second -smp
#   KNOB-UNSET      PAX_SMP unset: no -smp at all
#   KNOB-REFUSED    PAX_SMP=0 or a word is refused by name (exit 2), QEMU never started
#   KNOB-TOUR-TIME  tools/tour time with PAX_SMP=4 asks QEMU for `-smp 4` (its .meta's cmd too)
#   KNOB-TOUR-BOOT  tools/tour boot with PAX_SMP=4 asks QEMU for `-smp 4`
set -uo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
t=$(mktemp -d "${TMPDIR:-/tmp}/knob.XXXXXX")
trap 'rm -rf "$t"' EXIT
# The stand-in: `--version` answers as QEMU would; otherwise it writes its arguments, one a line, to
# $KNOB_ARGS, prints them and a PANIC line (tools/tour time stops at one), and exits 0.
cat > "$t/qemu" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = --version ]; then echo 'QEMU emulator version 0.0.0 (stand-in)'; exit 0; fi
printf '%s\n' "$@" > "${KNOB_ARGS:?}"
printf 'STUB-ARGS %s\n' "$*"
echo 'PANIC stand-in'
exit 0
STUB
chmod +x "$t/qemu"
: > "$t/image.iso"
bad=0
row() { if [ "$2" = 0 ]; then echo "PASS $1: $3"; else echo "FAIL $1: $3"; bad=1; fi; }
asked() { # FILE N: the arguments hold `-smp N` (adjacent lines)
    awk -v n="$2" 'p && $0 == n { f = 1 } { p = ($0 == "-smp") } END { exit !f }' "$1"
}
smps() { grep -cx -- -smp "$1" 2>/dev/null || true; }
run() { # ENV... -- QEMU-RUN ARGS...
    local e=()
    while [ "$1" != -- ]; do e+=("$1"); shift; done; shift
    : > "$t/args"
    env -u PAX_SMP ${e[@]+"${e[@]}"} PAX_QEMU="$t/qemu" KNOB_ARGS="$t/args" PAX_BUILD="$t/build" TMPDIR="$t" \
        "$root/tools/qemu-run" --timeout 20 --serial "$t/serial.log" "$t/image.iso" "$@" > "$t/out" 2>&1
}
run PAX_SMP=4 --; rc=$?
asked "$t/args" 4 && grep -q '^smp: 4 (PAX_SMP)$' "$t/serial.log.meta" 2>/dev/null
row KNOB-RUN $(( rc != 0 || $? != 0 )) "exit $rc, -smp lines $(smps "$t/args"), meta: $(grep '^smp:' "$t/serial.log.meta" 2>/dev/null || echo none)"
run PAX_SMP=4 -- -- -smp 2; rc=$?
asked "$t/args" 2 && [ "$(smps "$t/args")" = 1 ]
row KNOB-CALLER $(( rc != 0 || $? != 0 )) "exit $rc, -smp lines $(smps "$t/args") (want one, 2)"
run --; rc=$?
[ "$(smps "$t/args")" = 0 ] && [ -s "$t/args" ]
row KNOB-UNSET $(( rc != 0 || $? != 0 )) "exit $rc, -smp lines $(smps "$t/args") (want none)"
r0=0; r1=0
run PAX_SMP=0 --; r0=$?; s0=$(wc -c < "$t/args" | tr -d ' ')
run PAX_SMP=four --; r1=$?; s1=$(wc -c < "$t/args" | tr -d ' ')
[ "$r0" = 2 ] && [ "$r1" = 2 ] && [ "$s0" = 0 ] && [ "$s1" = 0 ] && grep -q 'PAX_SMP' "$t/out"
row KNOB-REFUSED $? "PAX_SMP=0 exit $r0, PAX_SMP=four exit $r1 (want 2 and 2, QEMU not started: $s0 $s1 bytes of arguments)"
: > "$t/args"
env PAX_SMP=4 PAX_QEMU="$t/qemu" KNOB_ARGS="$t/args" PAX_BUILD="$t/build" TMPDIR="$t" \
    "$root/tools/tour" time --firmware bios "$t/image.iso" "$t/tour.log" > "$t/out" 2>&1; rc=$?
asked "$t/args" 4 && grep -q -- '-smp 4' "$t/tour.log.meta" 2>/dev/null
row KNOB-TOUR-TIME $(( rc != 0 || $? != 0 )) "exit $rc, -smp lines $(smps "$t/args"), meta cmd: $(grep -c -- '-smp 4' "$t/tour.log.meta" 2>/dev/null || true)"
: > "$t/args"
env PAX_SMP=4 PAX_QEMU="$t/qemu" KNOB_ARGS="$t/args" PAX_BUILD="$t/build" TMPDIR="$t" \
    "$root/tools/tour" boot --firmware bios "$t/image.iso" > "$t/out" 2>&1; rc=$?
asked "$t/args" 4
row KNOB-TOUR-BOOT $(( rc != 0 || $? != 0 )) "exit $rc, -smp lines $(smps "$t/args")"
exit "$bad"
