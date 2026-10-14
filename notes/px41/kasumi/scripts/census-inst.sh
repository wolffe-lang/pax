#!/bin/bash
# px41 on kasumi: pax#47 with the scratch kernel, 30 s rounds as CI runs them, ten censuses a boot:
# no added load, then 12 loops on CPUs 4-7.
L=~/lanes/px41
while [ ! -f $L/ev/census-inst-release-sweep/done ]; do sleep 20; done
$L/st/censusloop.sh $L/t-inst release 4 0 - $L/ev/census-inst-release-r30-idle 30 2 $L/st/censusloop10.steps
$L/st/censusloop.sh $L/t-inst release 4 12 4-7 $L/ev/census-inst-release-r30-load12 30 2 $L/st/censusloop10.steps
echo done > $L/ev/census-inst.done
