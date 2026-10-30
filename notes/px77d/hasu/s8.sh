# px77d s8: the IDT-less window measured (TSC stamps, measure-tree: the old tree plus stamps, never committed),
# release tier, at kasumi's 2560x1440 with the live stick's 333-entry archive, 32 GiB, 16 CPUs, KVM; plain and triage.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
W=$L/build-measure
/home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-measure --memory 12g --pids-limit 16384 --ulimit core=0:0 \
 -v "$L:$L" -w "$L/measure-tree" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
 -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
 localhost/px75-ubuntu:2 taskset -c 0-5 bash -c '
  set -e; export PAX_WOLF=$(tools/fetch-wolf) PAX_BUILD='"$W"'; . tools/lib.sh; tools/fetch-limine
  mkdir -p '"$W"'; elf=$(tools/build-kernel --release --src kernel/kmain_console.lu '"$W"')
  for v in plain triage; do
    cp boot/limine-initramfs.conf '"$W"'/$v.conf; printf "    resolution: 2560x1440\n" >> '"$W"'/$v.conf
    [ $v = plain ] || printf "    cmdline: triage\n" >> '"$W"'/$v.conf
    tools/mkimage --conf '"$W"'/$v.conf --add '"$L"'/base-out/release.cpio initramfs.cpio $elf '"$W"'/$v.iso > /dev/null
  done' > $L/logs/measure-build.log 2>&1
echo "measure build exit $?"
for v in plain triage; do
  bash $L/repro.sh 36g measure-$v $W/$v.iso kvm none file 32G 16 90 -device VGA,vgamem_mb=64,xres=2560,yres=1440 > $L/logs/run-measure-$v.log 2>&1
  echo "run measure $v exit $?"; grep -a "^window:\|^screen:" $L/runs/measure-$v/serial.log
done
