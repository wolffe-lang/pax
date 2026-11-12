#!/usr/bin/env bash
# notes/px130/rig/measure.sh — px130's measurement (item 1), inside the burrowd rig's container (lib.sh's `ctr
# net`), from a clean checkout of the commit under test: tests/mpx5-burrowd's tree built (--no-boot, the native
# kernel), the extra boreutils the work needs (head, seq, yes, ...), then measure.py booted with and without
# `quiet`. Everything under PAX_BUILD.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
PAX_WOLF=$(tools/fetch-wolf | tail -n 1) || exit 2
export PAX_WOLF
echo "measure: P0 at $(git rev-parse HEAD) $(date -u +%FT%TZ)"
tests/mpx5-burrowd --no-boot --tier native 2>&1 | sed -u 's/^/  /'
[ "${PIPESTATUS[0]}" = 0 ] || { echo "measure: P0 red"; exit 1; }
extra=$PAX_BUILD/px130-bore
if [ ! -f "$extra/sums.txt" ]; then
    tools/mkboreutils "$extra" head tail seq yes wc sort uniq tr true false printf cut tee date uname pwd 2>&1 | sed -u 's/^/  /'
    [ "${PIPESTATUS[0]}" = 0 ] || { echo "measure: mkboreutils red"; exit 1; }
fi
rc=0
for c in ${PX130_CONFS:-plain quiet}; do
    echo "measure: boot $c $(date -u +%FT%TZ)"
    python3 -I notes/px130/rig/measure.py --images "$PAX_BUILD/mpx5-burrowd" \
        --elf "$PAX_BUILD/mpx5-burrowd/native/kmain_console.elf" --extra "$extra" --conf "$c" --accel kvm \
        --out "$PAX_BUILD/measure-$c" 2>&1 | sed -u 's/^/  /'
    r=${PIPESTATUS[0]}
    echo "END measure-$c exit=$r"
    [ "$r" = 0 ] || rc=1
done
exit $rc
