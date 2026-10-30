#!/usr/bin/env bash
# px78b: the kasumi leg (the branch's metal.py, run mode, through make-variant.py: the target an ide-hd with
# kasumi's model and serial, no append) on a COPY of the staged stick, under KVM in px78-ubuntu:1, block A held.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
k=$L/sout/pax-install-kasumi-197330ad.img
W=$L/leg-K I=$L/leg-inputs
[ ! -e "$W" ] || { echo "leg-K exists"; exit 2; }
mkdir -p "$W/metal" "$I/build/disktools/bin"
printf '%s\n' "$L/sout/kernel/kmain_console.elf" > "$I/build/disktools/native.elf.path"
cp "$L/sout/disktools/paxfat" "$I/build/disktools/bin/paxfat"
cp --sparse=always "$k" "$W/metal/stick.img"
chmod 644 "$W/metal/stick.img"
sha256sum "$W/metal/stick.img" | tee "$W/stick-at-start.sha256"
python3 -I $L/make-variant.py $L/stick/tests/mpx6-install.d/metal.py $L/metal-kasumi860.py 'Samsung SSD 860 EVO 500GB' 'Samsung SSD 860' <kasumi-serial>
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -n 9; do python3 -I -c 'import time; time.sleep(30)'; done
printf '%s block A acquired (leg K)\n' "$(date -u +%FT%TZ)"
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px78b-leg-K --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 --device /dev/kvm -v "$L:$L" -w "$L/stick" \
 -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/sb -e TMPDIR=$L/tmp -e PAX_METAL_ACCEL=kvm -e SOURCE_DATE_EPOCH=1700000000 \
 localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "time python3 -I $L/metal-kasumi860.py $L/stick $I $W/metal run" || rc=$?
flock -u 9; exec 9>&-
printf '%s block A RELEASED (leg K) rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
echo $rc > $L/leg-K.exit
printf '%s END leg K exit=%s\n' "$(date -u +%FT%TZ)" "$rc"
exit $rc
