# px77d: px76's x2APIC hand leg (R-px76-7) under KVM: tests/mpx6-metal with PAX_METAL_X2APIC=1 on UEFI.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
cd $L/pax && git fetch -q origin px77d && git checkout -q -f FETCH_HEAD && git rev-parse HEAD
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-x2 --memory 12g --pids-limit 16384 --ulimit core=0:0 --device /dev/kvm \
 -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/build-x2 -e TMPDIR=$L/tmp \
 -e PAX_METAL_X2APIC=1 -e PAX_METAL_FIRMWARE=uefi \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c 'export PAX_WOLF=$(tools/fetch-wolf) && tests/mpx6-metal'
echo "mpx6-metal x2apic exit $?"
