#!/bin/bash
# px49 on kasumi: mpx3-tree's probes-user image (a build's own archive) on trunk 6d4072c's kmain_console, native, BIOS.
#   trunk-tree.sh BUILDTAG
L=$HOME/lanes/px49
T=$L/trunk
O=$L/build/trunk-tree
mkdir -p $O
[ -d $T/kernel ] || { mkdir -p $T && git -C $L/pax-git archive 6d4072c | tar -x -C $T; }
podman run --rm -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
  cd $T && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tools/build-kernel --src kernel/kmain_console.lu $O/k >/dev/null 2>&1 && tools/fetch-limine >/dev/null && tools/mkimage --conf boot/limine-initramfs.conf --add $L/build/$1/mpx3-tree/probes-user.cpio initramfs.cpio $O/k/kmain_console.elf $O/probes-user.iso >/dev/null && sha256sum $O/probes-user.iso $O/k/kmain_console.elf $L/build/$1/mpx3-tree/probes-user.cpio" || exit 1
cd $T
export PAX_CACHE=$L/cache PAX_BUILD=$O
: > $O/none.keys
tools/qemu-halt --firmware bios --serial $O/serial.log --timeout 900 --qemu -m --qemu 512M --elf $O/k/kmain_console.elf --marker 'halt|PANIC .*' $O/probes-user.iso > $O/verdict 2>&1
echo "qemu-halt: $?"; tail -1 $O/verdict
grep -a 'unlink of /dev\|unlink of a directory' $O/serial.log
