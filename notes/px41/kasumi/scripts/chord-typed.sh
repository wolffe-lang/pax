#!/bin/bash
# px41 on kasumi: pax#45 with every play typed (200 a boot, a three-step chord), so each starts at its
# own phase of a tick, as the suite's `play chords` does: trunk's play, then the absolute sleep (w1);
# release, no added load, 5 boots each.
L=~/lanes/px41
$L/st/chordloop.sh $L/t-trunk release 5 0 - $L/ev/chord-typed-trunk-release $L/st/chordtyped.keys
$L/st/chordloop.sh $L/t-w1 release 5 0 - $L/ev/chord-typed-w1-release $L/st/chordtyped.keys
echo done > $L/ev/chord-typed.done
