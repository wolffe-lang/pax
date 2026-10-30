#!/usr/bin/env bash
# px78b: px77b's build.sh shape: the release pair in px75-ubuntu:2, then the stick on the host; block A held for both.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -n 9; do printf '%s block A held; waiting\n' "$(date -u +%FT%TZ)"; python3 -I -c 'import time; time.sleep(30)'; done
printf '%s block A acquired (stick build)\n' "$(date -u +%FT%TZ)"
rc=0
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px78b-sbuild --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/stick" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash "$L/sbuild-inside.sh" || rc=$?
printf '%s END sbuild-inside exit=%s\n' "$(date -u +%FT%TZ)" "$rc"
if [ "$rc" = 0 ]; then
 export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
 ( cd $L/stick && taskset -c 0-5 bash "$L/sstick.sh" ) || rc=$?
 printf '%s END sstick exit=%s\n' "$(date -u +%FT%TZ)" "$rc"
fi
flock -u 9; exec 9>&-
printf '%s block A RELEASED (stick build) rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
exit $rc
