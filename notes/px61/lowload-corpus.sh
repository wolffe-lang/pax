#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/lowload-corpus.pid"
ulimit -c 0
O=$L/lowload-corpus
mkdir -p "$O"
for role in root pax; do
    while ! awk '{exit !($1 < 16)}' /proc/loadavg; do
        echo "WAIT corpus $role: load must be below 16"
        uptime
        sleep 60
    done
    uptime
    rc=0
    taskset -c 8-11 "$L/pax/tools/qemu-halt" --firmware bios --accel tcg --serial "$O/$role.log" --timeout 900 \
        --qemu -m --qemu 1024M --elf "$L/build/mpx5-pelt-r2/mpx5-pelt/native/kmain_console.elf" --marker 'halt|PANIC .*' \
        --type "$L/build/mpx5-pelt-r2/mpx5-pelt/keys/corpus-$role.keys" --prompt '$ ' "$L/focused-fork/$role.iso" > "$O/$role.verdict" 2>&1 || rc=$?
    echo "lowload full corpus $role result $rc $(date -Is)"
    uptime
    tail -n 2 "$O/$role.verdict"
done
