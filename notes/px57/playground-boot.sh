#!/bin/bash
# px57 on kasumi: the rebuilt playground ISO booted once (TCG, taskset -c PX57_CPUS, 0-3) with the maintainer's session typed
# at pelt (notes/px57/playground.keys: `g -`, `aspen /`, `lupin run hello.lu`, then `su pax` and greet.sh, aspen and a typed lupin program), the serial log kept.
#   playground-boot.sh OUTDIR
L=$HOME/lanes/px57; P=$L/pax; O=$1; W=$HOME/lanes/orch-paxplay
set -u
mkdir -p $O
sha256sum $W/out/pax-playground.iso
taskset -c ${PX57_CPUS:-0-3} $P/tools/qemu-halt --firmware bios --serial $O/play.log --timeout 900 --accel tcg --qemu -m --qemu 512M \
  --elf $(cat $W/w/elf.path) --marker 'halt|PANIC .*' --type $P/notes/px57/playground.keys --prompt '$ ' --keyboard serial \
  $W/out/pax-playground.iso > $O/play.verdict 2>&1
echo "qemu-halt: $?"; tail -n 1 $O/play.verdict
tr -d '\r' < $O/play.log | sed 's/\x1b\[[0-9;]*[A-Za-z]//g' > $O/play.txt
