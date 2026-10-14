#!/bin/bash
# px41 on kasumi: pax#45 on trunk's play: no added load, then 12 loops on CPUs 12-15, release then native.
L=~/lanes/px41; T=$L/t-trunk
$L/st/chordloop.sh $T release 10 0 - $L/ev/chord-trunk-release-idle
$L/st/chordloop.sh $T release 10 12 12-15 $L/ev/chord-trunk-release-load12
$L/st/chordloop.sh $T native 5 0 - $L/ev/chord-trunk-native-idle
$L/st/chordloop.sh $T native 5 12 12-15 $L/ev/chord-trunk-native-load12
echo done > $L/ev/chord-trunk.done
