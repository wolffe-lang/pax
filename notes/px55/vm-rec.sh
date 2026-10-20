#!/bin/bash
# px55 on kasumi: real root's recordings of one of mpx5-jobs' nothing-typed images (fds: fdtab; sigs: sigwolf),
# from a suite build's own archive as is, on kasumi's own kernel image under QEMU (px48's linux-vm.sh) with
# px52's vmjob (notes/px52/vmjob.c: devtmpfs, then /dev/fd and /dev/std* made as a distribution's boot makes
# them; VMJOB.c instead when given: sigs was recorded by px53 with notes/px50/vmjob.c), as root and as
# 1000:1000, twice (OUTDIR/rec1, OUTDIR/rec2), the two compared byte for byte.
#   vm-rec.sh IMAGE ARCHIVE.cpio PROGRAM OUTDIR [VMJOB.c]
L=$HOME/lanes/px55; P=$L/pax; I=$1 A=$2 G=$3 O=$4 J=${5:-$P/notes/px52/vmjob.c}
set -u
mkdir -p $O $L/bin
V=$L/bin/vmjob-$(basename $(dirname $J))
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $V $J && sha256sum $V $J" || exit 1
sha256sum $A
: > $O/none.keys
for r in rec1 rec2; do
  rm -rf $O/$r; mkdir -p $O/$r
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "$G" $O/$r $I > $O/$r/$I.vm.out 2>&1 & a=$!
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "/bin/as 1000 1000 $G" $O/$r $I-user > $O/$r/$I-user.vm.out 2>&1 & b=$!
  wait $a; echo "$r root: $?"; wait $b; echo "$r user: $?"
done
for f in $I.tty $I.tty.rc $I-user.tty $I-user.tty.rc; do
  cmp -s $O/rec1/$f $O/rec2/$f && echo "same: $f $(sha256sum < $O/rec1/$f | cut -c1-16) $(wc -l < $O/rec1/$f) lines" || echo "DIFFER: $f"
done
cat $O/rec1/vm-$I.meta $O/rec1/vm-$I-user.meta
