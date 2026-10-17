#!/bin/bash
# px49 on kasumi: gaps and as built in px13-ubuntu (tools/mkjobs, tools/mkas), px49's vmjob, the gaps
# archive, then the probe on real root's guest as root and as 1000:1000.   vm-gaps.sh OUTDIR [PAXDIR]
L=$HOME/lanes/px49
O=$1; P=${2:-$L/pax}
set -u
mkdir -p $L/bin $O
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "
  cd $P && tools/mkjobs $L/bin && tools/mkas $L/bin && cc -static -O1 -o $L/bin/vmjob49 notes/px49/vmjob.c && sha256sum $L/bin/vmjob49" || exit 1
printf 'B: the sendfile reached the terminal\n' > $O/sf
$P/tools/mkinitramfs $O/gaps.cpio /bin/gaps=$L/bin/gaps:755 /bin/as=$L/bin/as:755 /g/:1777 /g/r644=$O/sf:644 /g/r600=$O/sf:600 /g/sf=$O/sf:644 > $O/gaps.cpio.txt || exit 1
tail -n 1 $O/gaps.cpio.txt
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob49 $O/gaps.cpio $P/user/console/gaps.keys "/bin/gaps" $O gaps & a=$!
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob49 $O/gaps.cpio $P/user/console/gaps.keys "/bin/as 1000 1000 /bin/gaps" $O gaps-user & b=$!
wait $a; echo "root: $?"; wait $b; echo "user: $?"
cat $O/vm-gaps.meta $O/vm-gaps-user.meta
for n in gaps gaps-user; do echo "=== $n"; tr -d '\r' < $O/$n.tty; done
