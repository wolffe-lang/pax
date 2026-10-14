#!/bin/bash
# px41 on kasumi: pax#45 with play's absolute sleep (tree w1): 12 loops on CPUs 8-11, then no added load.
L=~/lanes/px41; T=$L/t-w1
$L/st/chordloop.sh $T release 10 12 8-11 $L/ev/chord-w1-release-load12
$L/st/chordloop.sh $T release 10 0 - $L/ev/chord-w1-release-idle
$L/st/chordloop.sh $T native 5 12 8-11 $L/ev/chord-w1-native-load12
$L/st/chordloop.sh $T native 5 0 - $L/ev/chord-w1-native-idle
echo done > $L/ev/chord-w1.done
