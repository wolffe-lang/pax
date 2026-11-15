#!/bin/pelt
# tests/mpx6-logs.d/guest/ticks.sh CUT — a record `px133-tick CUT N` every 100 ms or so to
# /dev/kmsg at info, until the machine stops (px133's G4: the rig cuts the power under it).
i=0
while :; do
    echo "<6>px133-tick $1 $i" > /dev/kmsg
    i=$((i + 1))
    sleep 0.1
done
