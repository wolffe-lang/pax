#!/usr/bin/env bash
# px77b: px77a's recipe (px82's container), hasu block A (CPUs 0-5), pax trunk 101e7761.
# The block is held for the build alone and released the moment it ends.
set -uo pipefail
L=/home/mfwolffe/lanes/px77b
printf '%s\n' "$$" > "$L/build.pid"
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
printf '%s px77b acquiring block A\n' "$(date -u +%FT%TZ)"
until flock -n 9; do
 printf '%s block A held by another lane; waiting\n' "$(date -u +%FT%TZ)"
 python3 -I -c 'import time; time.sleep(30)'
done
printf '%s block A acquired\n' "$(date -u +%FT%TZ)"
ctr() {
 /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77b-build --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/pax" \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 "$@"
}
rc=0
ctr bash "$L/build-inside.sh" || rc=$?
echo "$rc" > "$L/build-inside.exit"
printf '%s END build-inside exit=%s\n' "$(date -u +%FT%TZ)" "$rc"
if [ "$rc" = 0 ]; then
 export PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
 cd "$L/pax" || exit 2
 taskset -c 0-5 bash "$L/stick-build.sh" || rc=$?
 echo "$rc" > "$L/stick-build.exit"
 printf '%s END stick-build exit=%s\n' "$(date -u +%FT%TZ)" "$rc"
fi
flock -u 9
exec 9>&-
printf '%s block A RELEASED rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
echo "$rc" > "$L/build.exit"
exit "$rc"
