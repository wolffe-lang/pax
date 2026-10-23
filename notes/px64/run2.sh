#!/bin/bash
# px64, kasumi: a suite run with the timing poller beside its boot.
set -u
L=$HOME/lanes/px64
run=$1; shift
B=$L/build/$run
( for i in $(seq 1 3000); do [ -f "$B/mpx5-scent-native-bios.serial.log" ] && break; sleep 0.2; done
  taskset -c 12-15 bash "$L/pax/notes/px64/timing.sh" "$B/mpx5-scent-native-bios.serial.log" "$L/timing-$run.txt" ) &
bash "$L/run-suite.sh" mpx5-scent "$run" "$@"
rc=$?
wait
echo "run2 rc=$rc $(date -Is)"
