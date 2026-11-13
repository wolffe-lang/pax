#!/usr/bin/env bash
# tests/mpx6-triage.d/selftest.sh — T2's mask (tests/mpx6-triage.d/mask) held to its fixtures (selftest/, README.md
# there): each same-NAME.a and same-NAME.b must mask alike, each differ-NAME.a and differ-NAME.b must not.
# Prints a PASS or FAIL line a pair; exit 0 when every pair holds, 1 otherwise.
set -u
d=$(cd "$(dirname "$0")" && pwd)
fail=0
for a in "$d"/selftest/*.a; do
    b=${a%.a}.b n=$(basename "${a%.a}")
    if cmp -s <("$d/mask" "$a") <("$d/mask" "$b"); then alike=1; else alike=0; fi
    case $n in
        same-*)
            if [ "$alike" = 1 ]; then echo "PASS T2 selftest $n: masked alike"
            else echo "FAIL T2 selftest $n: masked apart: $(diff <("$d/mask" "$a") <("$d/mask" "$b") | head -n 6 | tr '\n' '|')"; fail=1; fi ;;
        differ-*)
            if [ "$alike" = 0 ]; then echo "PASS T2 selftest $n: masked apart"
            else echo "FAIL T2 selftest $n: masked alike"; fail=1; fi ;;
        *) echo "FAIL T2 selftest $n: neither same- nor differ-"; fail=1 ;;
    esac
done
exit "$fail"
