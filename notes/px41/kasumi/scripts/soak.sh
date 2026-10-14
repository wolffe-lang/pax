#!/bin/bash
# px41 on kasumi: the 10,000-echo soak of tests/mpx4-net (native BIOS, every leg) under a ladder of loads:
# 0, 4, 8, 12 and 24 busy loops on CPUs 12-15, the suite on the same four. One run a rung, after w5.
L=~/lanes/px41
while [ ! -f $L/ev/w5/done ]; do sleep 20; done
for k in 0 4 8 12 24; do
  $L/st/suite.sh w2 net-load$k $k 12-15 mpx4-net --firmware bios --tier native
  { echo "== $k loops"; grep -a -h 'N6 \|NOT HALTED\|deadline' $L/ev/w2/net-load$k.out | cut -c1-200; } >> $L/ev/w2/soak.txt
done
echo done > $L/ev/w2/soak.done
