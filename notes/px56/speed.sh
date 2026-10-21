#!/bin/bash
# px56 on kasumi (P5): the archive's contiguous read (pax trunk 241b322's loader) against the tree's (this
# branch's), for an archive program: one image a kernel, the same archive (the probe, boreutils' 14 MB `true`,
# its run list `execs time N PATH` lines), booted ROUNDS times each, interleaved, TCG, taskset -c 0-3.
#   speed.sh TRUNK.elf BRANCH.elf EXECS TRUE OUTDIR [ROUNDS]
L=$HOME/lanes/px56; P=$L/pax
T=$1 B=$2 X=$3 U=$4 O=$5 R=${6:-3}
set -u
mkdir -p $O
printf '%s\n' '/bin/execs time 100 /bin/execs' '/bin/execs time 30 /bin/true' '/bin/execs time 100 /bin/execs' '/bin/execs time 30 /bin/true' > $O/speed.run
# the archive and the two images in px13-ubuntu (the suites' tools), the boots on kasumi
podman run --rm --network none -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
  cd $P && tools/mkinitramfs $O/speed.cpio /bin/execs=$X:755 /bin/true=$U:755 /etc/pax-run=$O/speed.run:644 > $O/speed.cpio.txt &&
  tools/mkimage --conf boot/limine-initramfs.conf --add $O/speed.cpio initramfs.cpio $T $O/trunk.iso > /dev/null &&
  tools/mkimage --conf boot/limine-initramfs.conf --add $O/speed.cpio initramfs.cpio $B $O/branch.iso > /dev/null" || exit 2
for k in trunk branch; do
  e=$T; [ $k = branch ] && e=$B
  echo "$k: elf $(sha256sum < $e | cut -c1-16) iso $(sha256sum < $O/$k.iso | cut -c1-16)"
done
echo "archive $(sha256sum < $O/speed.cpio | cut -c1-16); load $(cut -d' ' -f1-3 /proc/loadavg)"
for r in $(seq 1 $R); do
  for k in trunk branch; do
    e=$T; [ $k = branch ] && e=$B
    taskset -c 0-3 $P/tools/qemu-halt --firmware bios --serial $O/$k-$r.log --timeout 1800 --accel tcg --qemu -m --qemu 512M \
      --elf $e --marker 'halt|PANIC .*' $O/$k.iso > $O/$k-$r.verdict 2>&1
    echo "round $r $k: halt $? load $(cut -d' ' -f1-3 /proc/loadavg)"
    tr -d '\r' < $O/$k-$r.log | grep -a '^time: ' | sed "s/^/  $k $r /"
  done
done
