#!/bin/bash
# px29 on kasumi: a probe image (not pax's): kmain_console (native) from TREE's
# build, pelt, PLAY, the probe tunes; usage: mkprobe.sh TAG TREE PLAY TUNEDIR
set -u
L=~/lanes/px29; tag=$1; tree=$2; play=$3; tunes=$4; out=$L/img-$tag
rm -rf $out; mkdir -p $out/root/bin $out/root/etc $out/root/usr/share/tunes
cp $L/progs/pelt/pelt $out/root/bin/pelt; cp $play $out/root/bin/play; cp $tunes/* $out/root/usr/share/tunes/
echo /bin/pelt > $out/root/etc/pax-run
cd $tree; export PAX_CACHE=$L/cache TMPDIR=$L/tmp
pairs=(); for f in $(cd $out/root && find . -type f | sort); do f=${f#./}; m=644; [ -x $out/root/$f ] && m=755; pairs+=("/$f=$out/root/$f:$m"); done
{ tools/mkinitramfs $out/p.cpio "${pairs[@]}" && tools/mkimage --conf boot/limine-initramfs.conf --add $out/p.cpio initramfs.cpio $tree/build/mpx3-speaker/native/kmain_console.elf $out/p.iso
  cp $tree/build/mpx3-speaker/native/kmain_console.elf $out/k.elf
  nm $out/k.elf | awk '$3=="pax_spk_ring"||$3=="pax_spk_state"{print $3, $1}' > $out/syms
  sha256sum $out/p.iso $out/k.elf $out/root/bin/play; } > $out/build.log 2>&1
echo "rc $?" >> $out/build.log
