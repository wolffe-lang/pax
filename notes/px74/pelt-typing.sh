#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px74
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1
cd "$L/pax-final"
printf '%s\n' "$$" > "$L/runs/pelt-typing.pid"
exec > "$L/runs/pelt-typing.log" 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$L/runs/pelt-typing.exit"' EXIT
printf 'pelt typing queued %s\n' "$(date -Is)"
exec 9>/home/mfwolffe/lanes/kasumi-cores-12-15.lock; flock 9
ctr() {
    podman run --rm --memory 12g --ulimit core=0:0 -v "$L:$L:Z" \
        -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e PAX_REQUIRE_UEFI -e SOURCE_DATE_EPOCH=1700000000 \
        -w "$L/pax-final" localhost/px80-ubuntu taskset -c 12-15 "$L/in.sh" "$@" 9>&-
}
printf 'pelt build %s\n' "$(date -Is)"
ctr tests/mpx5-pelt --only build --tier native --firmware both
ctr tests/mpx5-pelt --only friendly --images "$PAX_BUILD/mpx5-pelt" --tier native --firmware both
ctr python3 -I tools/usb-typing mpx5-pelt --tier native --firmware both
printf 'pelt typing complete %s\n' "$(date -Is)"
