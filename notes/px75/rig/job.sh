#!/usr/bin/env bash
# job.sh NAME 'CMD' — CMD in the rig, detached: logs/NAME.log, logs/NAME.rc when done.
mkdir -p /home/mfwolffe/lanes/px75/logs
/home/mfwolffe/lanes/px75/rig/run.sh "$2" > /home/mfwolffe/lanes/px75/logs/$1.log 2>&1
echo $? > /home/mfwolffe/lanes/px75/logs/$1.rc
