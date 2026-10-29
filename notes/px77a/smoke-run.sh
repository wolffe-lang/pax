#!/usr/bin/env bash
set -euo pipefail
L=/home/mfwolffe/lanes/px77a
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
mv "$L/out" "$L/out-trunk"
git -C "$L/pax" fetch "$L/smoke.bundle" px77a-smoke
git -C "$L/pax" checkout --detach FETCH_HEAD
[ "$(git -C "$L/pax" rev-parse --short=8 HEAD)" = f8a3292b ]
printf '%s build smoke f8a3292b = trunk + f1f8137b only\n' "$(date -u +%FT%TZ)"
ctr() {
 /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77a-smoke --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/pax" \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 6-11 "$@"
}
ctr bash "$L/build-smoke-inside.sh"
export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
cd "$L/pax"
taskset -c 6-11 bash "$L/stick-smoke-build.sh"
ctr python3 -I "$L/qualify-smoke.py"
