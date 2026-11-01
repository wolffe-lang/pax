#!/usr/bin/env bash
# px85: F1's clock legs at a tree. tests/mpx6-metal stops at its first red
# leg, so after it each of px85's five words is booted again on both
# firmwares and its verdict printed on its own line (the clock lines, the
# source the kernel chose, the source the leg wants).
#   clock-legs.sh TREE BUILD [native|release]
set -uo pipefail
tree=$1 tier=${3:-native}
export PAX_BUILD=$2
mkdir -p "$PAX_BUILD"
PAX_WOLF=$("$tree/tools/fetch-wolf"); export PAX_WOLF
echo "tree $(git -C "$tree" rev-parse HEAD), tier $tier, wolf: $("$PAX_WOLF" --version | head -n 1)"
rc=0
PAX_METAL_TIER=$tier "$tree/tests/mpx6-metal" > "$PAX_BUILD/mpx6-metal.out" 2>&1 || rc=$?
grep -aE '^(PASS|FAIL) METAL firmware|^clock: |^timer: ' "$PAX_BUILD/mpx6-metal.out" | tr -d '\r'
echo "END tests/mpx6-metal $tier exit=$rc"
w=$PAX_BUILD/mpx6-metal
bad=0
for fw in bios uefi; do
    for word in stall_window stall_edge stall_long hpet_fast hpet_slow; do
        log=$w/leg-$fw-$word.log r=0
        "$tree/tools/qemu-run" --timeout 60 --firmware "$fw" --serial "$log" "$w/$word.iso" || r=$?
        want=HPET; case $word in hpet_*) want=PM;; esac
        lines=$(tr -d '\r' < "$log" | grep -a '^clock: ' | paste -sd'|' -)
        chosen=$(tr -d '\r' < "$log" | grep -a '^clock: ' | tail -n 1 | cut -d' ' -f2)
        verdict=PASS
        [ "$r" = 33 ] && [ "$chosen" = "$want" ] || { verdict=FAIL; bad=1; }
        [ "$want" != HPET ] || case $lines in *'checked against the PM timer'*) ;; *) verdict=FAIL bad=1;; esac
        [ "$want" != PM ] || case $lines in *refused*) ;; *) verdict=FAIL bad=1;; esac
        echo "$verdict LEG $fw $word: qemu $r, wants $want, chose $chosen: $lines"
    done
done
echo "END clock-legs $tier exit=$bad"
exit $bad
