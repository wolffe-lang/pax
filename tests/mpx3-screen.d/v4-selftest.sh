#!/usr/bin/env bash
# tests/mpx3-screen.d/v4-selftest.sh — V4's strip (tests/mpx3-screen.d/v4-strip) held to its fixtures (selftest/,
# README.md there): each same-NAME.a and same-NAME.b must strip alike, each differ-NAME.a and differ-NAME.b must
# not. Prints a PASS or FAIL line a pair; exit 0 when every pair holds, 1 otherwise.
set -u
d=$(cd "$(dirname "$0")" && pwd)
fail=0
for a in "$d"/selftest/*.a; do
    b=${a%.a}.b n=$(basename "${a%.a}")
    if cmp -s <("$d/v4-strip" "$a") <("$d/v4-strip" "$b"); then alike=1; else alike=0; fi
    case $n in
        same-*)
            if [ "$alike" = 1 ]; then echo "PASS V4 selftest $n: stripped alike"
            else echo "FAIL V4 selftest $n: stripped apart: $(diff <("$d/v4-strip" "$a") <("$d/v4-strip" "$b") | head -n 6 | tr '\n' '|')"; fail=1; fi ;;
        differ-*)
            if [ "$alike" = 0 ]; then echo "PASS V4 selftest $n: stripped apart"
            else echo "FAIL V4 selftest $n: stripped alike"; fail=1; fi ;;
        *) echo "FAIL V4 selftest $n: neither same- nor differ-"; fail=1 ;;
    esac
done
exit "$fail"
