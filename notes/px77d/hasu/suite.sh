# px77d: tests/mpx6-triage in the container (ACCEL kvm passes /dev/kvm; tcg does not).
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
dev=(); [ "${ACCEL:-kvm}" = kvm ] && dev=(--device /dev/kvm)
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-suite --memory 12g --pids-limit 16384 --ulimit core=0:0 "${dev[@]}" \
 -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build-suite-${ACCEL:-kvm} -e TMPDIR=$L/tmp \
 -e PAX_TRIAGE_TIER=${TIER:-native} -e PAX_TRIAGE_FIRMWARE=${FW:-both} \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && time tests/mpx6-triage'
echo "mpx6-triage exit $?"
