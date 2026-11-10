#!/usr/bin/env bash
# px115 on the lane host: one job in the rig container, run as a light job (two CPUs, LIGHT_CPUS, LIGHT_MEM).
# The container: localhost/px97f-ossh:1 (QEMU, OVMF, mtools, e2fsprogs, dnsmasq, OpenSSH 10.6p2 and 10.2p1), KVM,
# /dev/net/tun with NET_ADMIN for a tap, the lane directory at its own path, taskset LIGHT_CPUS inside, LIGHT_MEM.
# Log PX115_DIR/NAME.log, pid NAME.pid, exit marker NAME.exit; START/END lines around the command.
set -uo pipefail
: "${LIGHT_CPUS:?run me through the host's light-slot wrapper}"
L=${PX115_DIR:?the lane directory}
P=${PX115_PODMAN:?podman}
NAME=$1; shift
exec > "$L/$NAME.log" 2>&1 < /dev/null
echo $$ > "$L/$NAME.pid"; rm -f "$L/$NAME.exit"
fin() { echo "$(date -u +%FT%TZ) END $NAME exit=$1"; echo "$1" > "$L/$NAME.exit"; exit "$1"; }
trap 'fin 143' TERM; trap 'fin 130' INT; trap 'fin 129' HUP
avail=$(df -B1G --output=avail /home | tail -1)
[ "$avail" -ge 25 ] || { echo "under 25 GB free ($avail); not started"; fin 3; }
echo "$(date -u +%FT%TZ) START $NAME on cpus $LIGHT_CPUS, $avail GB free, load $(cut -d' ' -f1-3 /proc/loadavg)"
"$P" run --rm --init --memory "${LIGHT_MEM:-6g}" --pids-limit 4096 --ulimit core=0:0 \
    --device /dev/kvm --device /dev/net/tun --cap-add NET_ADMIN --cap-add NET_RAW --security-opt label=disable \
    -v "$L:$L" -w "$L" -e HOME="$L/home" -e TMPDIR="$L/tmp" -e PYTHONUNBUFFERED=1 \
    localhost/px97f-ossh:1 taskset -c "$LIGHT_CPUS" "$@" < /dev/null
fin $?
