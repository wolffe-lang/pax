#!/bin/bash
# px41 on kasumi: tree w5 = d1a9ff3 with the census's file-nr read by the shell, first (user/lobo/steps/load.steps,
# as committed next), images w2's: the load session, release BIOS, both sides, three times; no added load.
L=~/lanes/px41; T=$L/t-w5
if [ ! -d $T ]; then mkdir -p $T $L/ev/w5 && cd $L/pax && git fetch -q origin && git archive d1a9ff3 | tar -x -C $T && cp $L/tmp/load.steps.new $T/user/lobo/steps/load.steps && mkdir $T/build && ln -s $L/t-w2/build/mpx4-lobo $T/build/mpx4-lobo; fi
for i in 1 2 3; do
  $L/st/suite.sh w5 lobo-load-$i 0 - mpx4-lobo --round 30 --sessions load --tier release --firmware bios
  cp $T/build/mpx4-lobo-release-bios-load/console.log $L/ev/w5/lobo-load-$i.console.log
done
echo done > $L/ev/w5/done
