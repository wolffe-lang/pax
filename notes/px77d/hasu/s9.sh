# px77d s9: the suites the fix touches, on the fixed tree (hasu clone + the fix, synced), native tier, BIOS,
# KVM where tools/qemu-run finds it; then tests/mpx6-nmi with no /dev/kvm (TCG: N2 runs, N1 skipped by name).
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
B=$L/build-regress
run() { # name kvm|tcg command
  dev=(); [ "$2" = kvm ] && dev=(--device /dev/kvm)
  /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-reg --memory 12g --pids-limit 16384 --ulimit core=0:0 "${dev[@]}" \
   -v "$L:$L" -w "$L/pax" -e PAX_CACHE=$L/cache -e PAX_BUILD=$B/$1 -e TMPDIR=$L/tmp \
   -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
   localhost/px75-ubuntu:2 taskset -c 0-5 bash -c "export PAX_WOLF=\$(tools/fetch-wolf) && $3" > $L/logs/reg-$1.log 2>&1
  echo "BATCH $1 exit $?"
}
run mpx1 kvm 'tests/mpx1 --firmware both --tier native'
run mpx2-interrupts kvm 'tests/mpx2-interrupts --firmware bios --tier native'
run tour kvm 'tests/tour --firmware bios --tier native'
run mpx3-screen kvm 'tests/mpx3-screen --firmware bios --tier native'
run mpx6-triage kvm 'tests/mpx6-triage --firmware both'
run mpx6-nmi-tcg tcg 'PAX_NMI_FIRMWARE=bios tests/mpx6-nmi'
