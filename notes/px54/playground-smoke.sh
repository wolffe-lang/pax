#!/bin/bash
# px54 on kasumi: the refreshed playground ISO booted once (native BIOS,
# TCG, taskset -c 0-3) with notes/px54/playground.keys typed at its
# console: root's jumps, gi's menu, then `su pax` (HOME=/home/pax, ENV
# kept: the hook in pax's shell too, its own store), back, halt. The
# serial log normalised, printed.   playground-smoke.sh KEYS
L=$HOME/lanes/px54 O=$HOME/lanes/orch-paxplay
K=$1
export PAX_BUILD=$L/build/playground PAX_CACHE=$L/cache
mkdir -p $PAX_BUILD
cd $L/pax
taskset -c 0-3 tools/qemu-halt --firmware bios --serial $PAX_BUILD/smoke.serial.log --timeout 600 --qemu -m --qemu 512M \
    --elf $(cat $O/w/elf.path) --marker 'halt|PANIC .*' --type "$K" --prompt '$ ' $O/out/pax-playground.iso > $PAX_BUILD/smoke.verdict 2>&1
echo "qemu-halt: $? ($(tail -n 1 $PAX_BUILD/smoke.verdict))"
. tools/lib.sh
serial_norm $PAX_BUILD/smoke.serial.log
