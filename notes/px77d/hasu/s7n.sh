# px77d s7n: tests/mpx6-nmi on the fixed tree only (KVM), block A.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
rm -rf $L/build-nmi-new/mpx6-nmi/native/bios $L/build-nmi-new/mpx6-nmi/native/uefi
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-nmi --memory 12g --pids-limit 16384 --ulimit core=0:0 --device /dev/kvm \
 -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build-nmi-new -e TMPDIR=$L/tmp \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && time tests/mpx6-nmi' > $L/logs/nmi-new.log 2>&1
echo "nmi new exit $?"
