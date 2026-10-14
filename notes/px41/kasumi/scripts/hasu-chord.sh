#!/usr/bin/env bash
# px41 on hasu (KVM): pax#45, trunk's play then the absolute sleep, 10 boots of 60 plays each, no added load.
L=~/lanes/px41; export ACCEL=kvm
bash $L/st/chordloop.sh $L/t-trunk release 10 0 - $L/ev/hasu-chord-trunk-release-kvm $L/st/chordloop.keys
bash $L/st/chordloop.sh $L/t-w1 release 10 0 - $L/ev/hasu-chord-w1-release-kvm $L/st/chordloop.keys
echo done > $L/ev/hasu-chord.done
