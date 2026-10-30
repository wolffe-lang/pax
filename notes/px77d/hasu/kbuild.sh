#!/usr/bin/env bash
# px77d: build the release kmain_console ELF from the hasu clone (kernel only), in the container.
set -uo pipefail
L=/home/mfwolffe/lanes/px77d
OUT=${1:-$L/kout}
rm -rf "$OUT"; mkdir -p "$OUT"
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-kbuild --memory 12g --pids-limit 16384 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tools/build-kernel --release --src kernel/kmain_console.lu '"$OUT"
