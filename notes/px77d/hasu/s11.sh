# px77d s11: tests/mpx6-triage at the head (T1 after the fix), KVM, both firmwares.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
cd $L/pax && git fetch -q origin px77d && git checkout -q -f FETCH_HEAD && git clean -fdq tests && git rev-parse HEAD
rm -rf $L/build-triage-head
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-suite --memory 12g --pids-limit 16384 --ulimit core=0:0 --device /dev/kvm \
 -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build-triage-head -e TMPDIR=$L/tmp \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && time tests/mpx6-triage && time tests/mpx6-nmi' > $L/logs/head-suites.log 2>&1
echo "head suites exit $?"
