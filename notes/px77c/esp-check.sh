#!/usr/bin/env bash
# px77c: an edited copy's ESP, read on hasu: fsck.fat -n over it, every entry mtools lists (macOS's own
# among them), and /pax/install-targets by the stick's own paxfat. Under block A.
#   esp-check.sh COPY OUT
set -uo pipefail
L=/home/mfwolffe/lanes/px77c
C=$1 O=$2
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -n 9; do printf '%s block A held; waiting\n' "$(date -u +%FT%TZ)"; python3 -I -c 'import time; time.sleep(30)'; done
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --memory 12g -v "$L:$L" localhost/px75-ubuntu:2 taskset -c 0-5 bash -c '
 C=$1 O=$2 L=$3
 off=$(python3 -I "$L/old/extract.py" "$C")
 sha256sum "$C"
 echo "esp at $off"
 dd if="$C" of="$O.esp" bs=1M skip=$((off / 1048576)) count=756 status=none
 fsck.fat -n "$O.esp"; echo "fsck.fat exit $?"
 rm "$O.esp"
 mdir -/ -a -i "$C@@$off" ::
 "$L/out/disktools/paxfat" --offset "$off" cat "$C" /pax/install-targets | grep -v "^#"
 echo "entries: $("$L/out/disktools/paxfat" --offset "$off" cat "$C" /pax/install-targets | grep -c "^model=")"
' _ "$C" "$O" "$L" > "$O" 2>&1 || rc=$?
flock -u 9
echo "esp-check $C rc=$rc"
