#!/bin/bash
# px57 on kasumi: real root's recordings of mpx5-jobs' eds image, from a suite build's own archive as is, on
# kasumi's own kernel image under QEMU (px48's linux-vm.sh) with px52's vmjob (notes/px52/vmjob.c, unchanged):
# edwolf and hostq as root and as 1000:1000 (nothing typed), twice (OUTDIR/rec1, OUTDIR/rec2), the two
# compared byte for byte.   vm-rec.sh ARCHIVE.cpio OUTDIR [rec1 rec2 …]   (the tree: PX57_TREE)
L=$HOME/lanes/px57; P=${PX57_TREE:-$L/pax}; A=$1 O=$2; shift 2
RECS=${*:-rec1 rec2}
set -u
mkdir -p $O $L/bin
J=$P/notes/px52/vmjob.c
V=$L/bin/vmjob-px52
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $V $J && sha256sum $V $J" || exit 1
sha256sum $A
: > $O/none.keys
for r in $RECS; do
  rm -rf $O/$r; mkdir -p $O/$r
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "/bin/edwolf" $O/$r eds > $O/$r/eds.vm.out 2>&1 & a=$!
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "/bin/as 1000 1000 /bin/edwolf" $O/$r eds-user > $O/$r/eds-user.vm.out 2>&1 & b=$!
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "/bin/hostq" $O/$r hostq > $O/$r/hostq.vm.out 2>&1 & c=$!
  taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $V $A $O/none.keys "/bin/as 1000 1000 /bin/hostq" $O/$r hostq-user > $O/$r/hostq-user.vm.out 2>&1 & d=$!
  wait $a; echo "$r eds: $?"; wait $b; echo "$r eds-user: $?"; wait $c; echo "$r hostq: $?"; wait $d; echo "$r hostq-user: $?"
done
set -- $RECS
if [ $# -ge 2 ]; then
  for f in eds.tty eds.tty.rc eds-user.tty eds-user.tty.rc hostq.tty hostq.tty.rc hostq-user.tty hostq-user.tty.rc; do
    cmp -s $O/$1/$f $O/$2/$f && echo "same: $f $(sha256sum < $O/$1/$f | cut -c1-16) $(wc -l < $O/$1/$f) lines" || echo "DIFFER: $f"
  done
fi
cat $O/$1/vm-eds.meta $O/$1/vm-eds-user.meta $O/$1/vm-hostq.meta $O/$1/vm-hostq-user.meta
