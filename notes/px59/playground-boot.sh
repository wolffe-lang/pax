#!/bin/bash
# px59 on kasumi: the rebuilt playground ISO booted once (TCG, BIOS,
# taskset -c 0-3) with the maintainer's session typed at the PS/2
# keyboard (notes/px59/playground.keys through tools/ps2-session and a
# second monitor), each screen taken held to tools/screen-ref's picture
# of the serial bytes (tests/mpx5-screen.d/compare.py ref).
#   playground-boot.sh OUTDIR
L=$HOME/lanes/px59; P=$L/pax; O=$1; W=$HOME/lanes/orch-paxplay
set -u
rm -rf $O; mkdir -p $O
sha256sum $W/out/pax-playground.iso
python3 $P/tools/ps2-session --serial $O/play.log --monitor $O/mon2 --keys $P/notes/px59/playground.keys --out $O --timeout 600 > $O/keys.out 2>&1 &
k=$!
PAX_BUILD=$O PAX_CACHE=$L/cache taskset -c 0-3 $P/tools/qemu-halt --firmware bios --serial $O/play.log --timeout 900 --accel tcg \
  --qemu -m --qemu 512M --qemu -monitor --qemu "unix:$O/mon2,server=on,wait=off" \
  --elf $(cat $W/w/elf.path) --marker 'halt|PANIC .*' $W/out/pax-playground.iso > $O/play.verdict 2>&1
echo "qemu-halt: $?"; tail -n 1 $O/play.verdict
wait $k; echo "ps2-session: $?"
python3 $P/tests/mpx5-screen.d/compare.py ref $O/play.log 'PAX: the console' $O; echo "compare: $?"
tr -d '\r' < $O/play.log | sed 's/\x1b\[[0-9;?]*[A-Za-z]//g' | grep -a -A3 'cat notes.txt'
