#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/aspen-root-pax.pid"
ulimit -c 0
uptime
O=$L/aspen-root-pax
mkdir -p "$O"
taskset -c 8-11 "$L/pax/tools/qemu-halt" --firmware bios --accel tcg --serial "$O/pax.log" --timeout 900 \
    --qemu -m --qemu 512M --elf "$(cat "$L/w/elf.path")" --marker 'halt|PANIC .*' \
    --type "$L/pax/notes/px61/aspen-root-pax.keys" --prompt '$ ' "$L/out/pax-playground.iso" > "$O/pax.verdict" 2>&1
tr -d '\r' < "$O/pax.log" > "$O/pax.txt"
grep -qx 'aspen-root-st=0' "$O/pax.txt"
grep -qx 'aspen-pax-st=0' "$O/pax.txt"
uptime
echo 'aspen full root listings: root and pax exit zero; root-listing difference remains pax#113'
