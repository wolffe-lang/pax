#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
printf '%s\n' $$ > "$L/census2.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/census2.status; exit "$s"' EXIT
podman run --rm --privileged --name px60-census2 --cpuset-cpus 0-3 -v "$L:/work" \
 localhost/px13-ubuntu bash -c 'set -euo pipefail
 r=/work/session-build/mpx5-wolf/root
 mkdir -p "$r/dev" "$r/proc"
 mount --rbind /dev "$r/dev"
 mount -t proc proc "$r/proc"
 python3 -I /work/pax/notes/px60/census.py "$r" /work/census2 /work/pax/notes/px60/chroot-exec.py
 '
