#!/bin/bash
# px54 on kasumi: how long gi's menu takes to ask on PAX under TCG: the
# lope image booted with the menu's digit typed after shorter pauses
# (qemu-halt's PAX_TYPE_PAUSE; the first sweep, at the suite's first
# text, set it through the suite's PAX_LOPE_PAUSE, since removed), each boot's L1 read: a digit typed before `read`
# starts is echoed where the container's is not, and L1 goes red. Native
# BIOS, taskset -c 0-3.   pause-sweep.sh TAG PAUSE...
L=$HOME/lanes/px54
T=$1; shift
B=$L/build/$T
cd $L/pax
for p in "$@"; do
  export PAX_CACHE=$L/cache PAX_BUILD=$B-p$p
  mkdir -p $PAX_BUILD
  PAX_TYPE_PAUSE=$p taskset -c 0-3 tests/mpx5-lope --images $B/mpx5-lope --tier native --firmware bios > $PAX_BUILD/boot.log 2>&1
  echo "pause $p: rc $? $(grep -c 'PASS L1' $PAX_BUILD/boot.log) L1 PASS, $(grep -c 'FAIL L1' $PAX_BUILD/boot.log) L1 FAIL; load $(cut -d' ' -f1-3 /proc/loadavg)"
  grep -a 'FAIL L1' $PAX_BUILD/boot.log | cut -c1-400
done
