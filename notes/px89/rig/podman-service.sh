#!/usr/bin/env bash
# px89: the lane's podman service for its containers' engine
# (podman-remote): start | stop. Rootless, rig-env's storage and config
# (the wrapper's), its socket in the lane directory; detached with a pid
# file; stopped by that pid alone.
set -uo pipefail
L=/home/mfwolffe/lanes/px89
case ${1:-} in
    start)
        rm -f "$L/podman.sock"
        setsid -f bash -c 'echo $$ > "$1/logs/podman-service.pid"; exec /home/mfwolffe/lanes/rig-env/bin/podman system service --time=0 "unix://$1/podman.sock"' x "$L" \
            < /dev/null >> "$L/logs/podman-service.log" 2>&1
        n=0; while [ ! -S "$L/podman.sock" ] && [ $n -lt 100 ]; do sleep 0.1; n=$((n + 1)); done
        echo "podman service: pid $(cat "$L/logs/podman-service.pid"), socket $(ls -l "$L/podman.sock" 2>&1)"
        ;;
    stop)
        p=$(cat "$L/logs/podman-service.pid" 2>/dev/null) && kill "$p" && echo "podman service $p stopped"
        ;;
    *) echo "usage: podman-service.sh start|stop" >&2; exit 2 ;;
esac
