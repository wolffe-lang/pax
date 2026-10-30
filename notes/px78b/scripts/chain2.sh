#!/usr/bin/env bash
# px78b: inputs, the cancel-words and guided-yes rows, then the kasumi leg under KVM (build on the host, run in
# px78-ubuntu:1). Each step takes and releases block A; a red step stops the chain.
set -uo pipefail
L=/home/mfwolffe/lanes/px78b
printf '%s\n' "$$" > $L/chain.pid
W=$L/w I=$L/w/inputs
step() { local n=$1; shift; printf '%s START %s\n' "$(date -u +%FT%TZ)" "$n"; "$@"; local rc=$?; printf '%s STEP %s exit=%s\n' "$(date -u +%FT%TZ)" "$n" "$rc"; echo $rc > $L/$n.exit; [ $rc = 0 ] || { echo "CHAIN STOPPED at $n"; exit $rc; }; }
# chain2: inputs built by chain.sh (inputs.exit 0); the rows in px78-ubuntu:1 for verify.py's sgdisk
rows='export PAX_WOLF=$(tools/fetch-wolf) SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
D=tests/mpx6-install.d
rm -rf '"$W"'/fault-cancel-words '"$W"'/guided-yes
PAX_INSTALL_FAULT=cancel-words python3 -I $D/install.py $PWD '"$I $W"'/fault-cancel-words no vdb || exit 1
PAX_INSTALL_GUIDED=1 python3 -I $D/install.py $PWD '"$I $W"'/guided-yes no vdb || exit 1
python3 -I $D/verify.py $PWD '"$W"'/guided-yes no vdb || exit 1
echo PASS guided-yes: the guided install with yes, verified'
step rows bash $L/ctr.sh rows localhost/px78-ubuntu:1 0 bash -c "$rows"
hostbuild() {
 exec 8>/home/mfwolffe/lanes/hasu-block-A.lock
 until flock -n 8; do python3 -I -c 'import time; time.sleep(30)'; done
 printf '%s block A acquired (metal build)\n' "$(date -u +%FT%TZ)"
 ( cd $L/pax && export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH \
   PAX_CACHE=$L/cache PAX_BUILD=$L/build TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_METAL_MODE=build \
   && taskset -c 0-5 tests/mpx6-install --only metal --work $W --inputs $I )
 local rc=$?
 flock -u 8; exec 8>&-
 printf '%s block A RELEASED (metal build) rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
 return $rc
}
step metal-build hostbuild
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm" step metal-run bash $L/ctr.sh metal-run localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W --inputs $I"
printf '%s CHAIN DONE\n' "$(date -u +%FT%TZ)"
