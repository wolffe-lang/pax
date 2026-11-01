#!/usr/bin/env bash
# px85: start a detached job on hasu with a pid file, a log and an exit marker.
#   launch.sh NAME CMD...    -> /home/mfwolffe/lanes/px85/logs/NAME.{pid,log,exit}
L=/home/mfwolffe/lanes/px85
N=$1; shift
rm -f "$L/logs/$N.exit" "$L/logs/$N.pid"
setsid -f bash -c 'echo $$ > "$1.pid"; shift; "$@" > "${0}.log" 2>&1; echo $? > "${0}.exit"' \
    "$L/logs/$N" "$L/logs/$N" "$@" < /dev/null
for _ in 1 2 3 4 5 6 7 8 9 10; do [ -s "$L/logs/$N.pid" ] && break; sleep 1; done
echo "launched $N pid $(cat "$L/logs/$N.pid" 2>/dev/null)"
