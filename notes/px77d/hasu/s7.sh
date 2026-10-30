# px77d s7: tests/mpx6-nmi on the tree before the fix (red expected: every row of the old window and
# every machine check resets) and on the fixed tree (green), KVM, block A.
export PX77D_LOCKED=1
L=/home/mfwolffe/lanes/px77d
run() { # tree build-dir log [extra env]
  /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px77d-nmi --memory 12g --pids-limit 16384 --ulimit core=0:0 --device /dev/kvm \
   -v "$L:$L" -w "$1" -e PAX_CACHE=$L/cache -e PAX_BUILD=$2 -e TMPDIR=$L/tmp -e PAX_NMI_FIRMWARE=${FW:-both} \
   -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
   localhost/px75-ubuntu:2 taskset -c 0-5 bash -c "export PAX_WOLF=\$(tools/fetch-wolf) && $4" > "$3" 2>&1
  echo "$3 exit $?"
}
# the old tree: every row, its outcome recorded, nothing dies early
FW=uefi run $L/old-tree $L/build-nmi-old $L/logs/nmi-old.log 'set -e; . tools/lib.sh; w=$PAX_BUILD/mpx6-nmi/native; mkdir -p $w; tools/fetch-limine; elf=$(tools/build-kernel --src kernel/kmain_console.lu $w); printf "# none\n" > $w/pax-run; tools/mkinitramfs $w/nmi.cpio /etc/pax-run=$w/pax-run >/dev/null; tools/mkimage --conf boot/limine-initramfs.conf --add $w/nmi.cpio initramfs.cpio $elf $w/nmi.iso >/dev/null; for k in nmi:serial.init nmi:frames.start nmi:paging.switch_to nmi:fb.start nmi:initramfs.report nmi:apic.start nmi:pci.scan mce:frames.start mce:initramfs.report mce:pci.scan; do python3 -I tests/mpx6-nmi.d/inject.py --image $w/nmi.iso --elf $elf --output $w/uefi/${k%%:*}-${k#*:} --firmware uefi --kind ${k%%:*} --at ${k#*:} --expect survive || true; done'
run $L/pax $L/build-nmi-new $L/logs/nmi-new.log 'time tests/mpx6-nmi'
