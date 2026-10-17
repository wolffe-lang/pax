#!/bin/bash
# px49 on kasumi: the gaps image (a build's own archive) on trunk 6d4072c's kmain_session, native, BIOS: what PAX answered before this lane.
#   trunk-gaps.sh BUILDTAG
L=$HOME/lanes/px49
T=$L/trunk
O=$L/build/trunk-gaps
rm -rf $T && mkdir -p $T $O && git -C $L/pax-git archive 6d4072c | tar -x -C $T
podman run --rm -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
  cd $T && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tools/build-kernel --src kernel/kmain_session.lu $O/k >/dev/null 2>&1 && tools/fetch-limine >/dev/null && tools/mkimage --conf boot/limine-initramfs.conf --add $L/build/$1/mpx5-jobs/gaps.cpio initramfs.cpio $O/k/kmain_session.elf $O/gaps.iso >/dev/null && sha256sum $O/gaps.iso $O/k/kmain_session.elf $L/build/$1/mpx5-jobs/gaps.cpio" || exit 1
cd $T
cat $L/pax/user/console/gaps.keys $L/pax/user/console/gaps.keys > $O/keys
export PAX_CACHE=$L/cache PAX_BUILD=$O
tools/qemu-halt --firmware bios --serial $O/serial.log --timeout 900 --qemu -m --qemu 512M --elf $O/k/kmain_session.elf --marker 'halt|PANIC .*' --type $O/keys --prompt '$ ' $O/gaps.iso > $O/verdict 2>&1
echo "qemu-halt: $?"; tail -2 $O/verdict
. tools/lib.sh; serial_norm $O/serial.log > $O/serial.norm
for k in 1 2; do
  awk -v k="$k" '$0 ~ "^run " k ": " { on = 1; next } on && /^run [0-9]+: |^run: [0-9]+ commands$|^user: frames free / { exit } on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' $O/serial.norm > $O/run$k.session
done
grep -a 'refused\|ENOSYS\|PANIC' $O/serial.norm | sed -E 's/pid [0-9]+/pid N/' | sort | uniq -c
