#!/bin/bash
# px64, kasumi: tools/mkscent in the lane's own Ubuntu container, CPUs 12-15.
set -u
L=$HOME/lanes/px64
O=${1:-$L/scent-out}
printf '%s\n' $$ > "$L/mkscent.pid"
mkdir -p "$L/cache" "$L/tmp"
rm -rf "$O"
uptime
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e O="$O" -e L="$L" \
    localhost/px64-ubuntu bash -c 'cd $L/pax && time tools/mkscent $O; echo "mkscent rc=$?"'
ls -la "$O"
echo "mkscent-run.sh done $(date -Is)"
