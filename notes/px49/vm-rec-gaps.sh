#!/bin/bash
# px49 on kasumi: real root's recordings of mpx5-jobs' gaps runs, from a suite build's own archive.
#   vm-rec-gaps.sh TAG OUTDIR
L=$HOME/lanes/px49
B=$L/build/$1/mpx5-jobs
O=$2
P=$L/build/$1/pax
mkdir -p $O
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob49 $P/notes/px49/vmjob.c && sha256sum $L/bin/vmjob49 $P/notes/px49/vmjob.c" || exit 1
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob49 $B/gaps.cpio $P/user/console/gaps.keys "/bin/gaps" $O gaps '$ ' & a=$!
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob49 $B/gaps.cpio $P/user/console/gaps.keys "/bin/as 1000 1000 /bin/gaps" $O gaps-user '$ ' & b=$!
wait $a; echo "gaps: $?"; wait $b; echo "gaps-user: $?"
cat $O/vm-gaps*.meta
