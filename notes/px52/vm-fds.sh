#!/bin/bash
# px52 on kasumi: px52's vmjob (built in px13-ubuntu), a suite build's own fds archive as is, then fdtab on real
# root's guest (kasumi's own kernel image under QEMU, px48's linux-vm.sh) as root and as 1000:1000.
#   vm-fds.sh OUTDIR ARCHIVE.cpio
L=$HOME/lanes/px52; O=$1; P=$L/pax; A=$2
set -u
mkdir -p $O
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob52 $P/notes/px52/vmjob.c && sha256sum $L/bin/vmjob52 $P/notes/px52/vmjob.c" || exit 1
: > $O/fds.keys
sha256sum $A
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob52 $A $O/fds.keys "/bin/fdtab" $O fds & a=$!
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob52 $A $O/fds.keys "/bin/as 1000 1000 /bin/fdtab" $O fds-user & b=$!
wait $a; echo "root: $?"; wait $b; echo "user: $?"
cat $O/vm-fds.meta $O/vm-fds-user.meta
