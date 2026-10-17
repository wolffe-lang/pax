#!/bin/bash
# px50 on kasumi: the fds image (a build's own archive) on trunk d0a48be's kmain_session, native, BIOS: what PAX
# answered before this lane.   trunk-fds.sh BUILDTAG
L=$HOME/lanes/px50
T=$L/trunk
O=$L/build/trunk-fds
rm -rf $T $O && mkdir -p $T $O && git -C $L/pax archive d0a48be | tar -x -C $T
podman run --rm -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
  cd $T && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tools/build-kernel --src kernel/kmain_session.lu $O/k >/dev/null 2>&1 && tools/fetch-limine >/dev/null && tools/mkimage --conf boot/limine-initramfs.conf --add $L/build/$1/mpx5-jobs/fds.cpio initramfs.cpio $O/k/kmain_session.elf $O/fds.iso >/dev/null && sha256sum $O/fds.iso $O/k/kmain_session.elf $L/build/$1/mpx5-jobs/fds.cpio" || exit 1
mkdir -p $O/native && cp $O/k/kmain_session.elf $O/native/ && cp $O/fds.iso $O/native/fds.iso
$L/pax/notes/px50/pax-boot.sh $O native fds kmain_session $O/boot
cd $L/pax && . tools/lib.sh
for n in 1 2; do r=fds; [ $n = 2 ] && r=fds-user
  serial_norm tests/mpx5-jobs.d/linux/$r.tty > $O/$r.rec.cmp
  echo "== trunk $r: $(diff $O/$r.rec.cmp $O/boot/run$n.session | grep -c '^<') of $(grep -c . $O/$r.rec.cmp) lines differ"
done
