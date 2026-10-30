#!/usr/bin/env bash
# px77c: px78's kasumi leg (tests/mpx6-install --only metal, PAX_METAL_MODE=run) pointed at a COPY of
# the exact install stick, under hasu block A, released the moment the leg's container ends.
#   leg.sh NAME STICK-COPY tcg|kvm [VARIANT.py]
# NAME's work is $L/leg-NAME; the copy is moved in as its metal/stick.img (it is the leg's to write:
# the allow-list line, the install log). The inputs directory holds what run mode reads: the kernel
# the stick boots (its symbols: the screen's cells) and the paxfat built with it. With VARIANT.py the
# leg is that lane-local copy of metal.py, run as tests/mpx6-install runs metal.py.
# The container is localhost/px78-ubuntu:1 (px75-ubuntu:2 plus gdisk, fdisk, strace: px78's image for
# this leg), since M10's `sgdisk -v` is not in px75-ubuntu:2.
set -uo pipefail
L=/home/mfwolffe/lanes/px77c
N=$1 STICK=$2 ACC=$3 VAR=${4:-}
W=$L/leg-$N I=$L/leg-inputs
printf '%s\n' "$$" > "$L/leg-$N.pid"
[ ! -e "$W" ] || { echo "leg-$N exists"; exit 2; }
mkdir -p "$W/metal" "$I/build/disktools/bin"
printf '%s\n' "$L/out/kernel/kmain_console.elf" > "$I/build/disktools/native.elf.path"
cp "$L/out/disktools/paxfat" "$I/build/disktools/bin/paxfat"
mv "$STICK" "$W/metal/stick.img"
sha256sum "$W/metal/stick.img" > "$W/stick-at-start.sha256"
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77c leg %s acquiring block A\n' "$(date -u +%FT%TZ)" "$N"
until flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(30)'
done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
dev=(); [ "$ACC" = kvm ] && dev=(--device /dev/kvm)
if [ -n "$VAR" ]; then
 inner="python3 -I $VAR $L/pax $I $W/metal run"
else
 inner="tests/mpx6-install --only metal --work $W --inputs $I"
fi
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name "px77c-leg-$N" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 "${dev[@]}" -v "$L:$L" -w "$L/pax" \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build -e TMPDIR=$L/tmp -e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=$ACC \
 localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "time $inner" || rc=$?
flock -u 9
exec 9>&-
printf '%s block A RELEASED leg %s rc=%s\n' "$(date -u +%FT%TZ)" "$N" "$rc"
echo "$rc" > "$L/leg-$N.exit"
printf '%s END leg %s exit=%s\n' "$(date -u +%FT%TZ)" "$N" "$rc"
exit "$rc"
