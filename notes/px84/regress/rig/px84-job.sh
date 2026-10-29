#!/usr/bin/env bash
set -euo pipefail
L=/mnt/steamlib/lanes/px84
name=$1; shift
mkdir -p "$L/runs" "$L/tmp" "$L/cache" "$L/build"
printf '%s\n' "$$" > "$L/runs/$name.pid"
{
    printf '%s start %s\n' "$name" "$(date -Is)"
    exec 9>/home/mfwolffe/lanes/kasumi-cores-4-7.lock
    flock 9
    printf '%s locked %s\n' "$name" "$(date -Is)"
    rc=0
    podman run --rm --memory 12g --ulimit core=0:0 \
      -v "$L:$L:Z" -v /usr/lib/modules:/host-modules:ro -e PAX_LOPE_REPO="$L/lope" -e PAX_CACHE="$L/cache" -e PAX_BUILD="$L/build" -e TMPDIR="$L/tmp" \
      -e CARGO_INCREMENTAL=0 -e SOURCE_DATE_EPOCH=1700000000 -e TZ=UTC -e PAX_REQUIRE_UEFI=1 \
      -w "$L/pax" localhost/px80-ubuntu taskset -c 4-7 "$L/px74-in.sh" "$@" 9>&- || rc=$?
    printf '%s exit=%s %s\n' "$name" "$rc" "$(date -Is)"
    printf '%s\n' "$rc" > "$L/runs/$name.exit"
} > "$L/runs/$name.log" 2>&1
exit "$rc"
