#!/bin/bash
# px50 on kasumi: fdtab and as (built in px13-ubuntu), px50's vmjob, the fds archive, then the probe on real
# root's guest as root and as 1000:1000.   vm-fds.sh OUTDIR [ARCHIVE.cpio]
#   (no ARCHIVE: one is made here from ~/lanes/px50/bin; with one, a suite build's own archive is used as is)
L=$HOME/lanes/px50
O=$1; P=$L/pax; A=${2:-}
set -u
mkdir -p $O
podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob50 $P/notes/px50/vmjob.c && sha256sum $L/bin/vmjob50 $P/notes/px50/vmjob.c" || exit 1
: > $O/fds.keys
if [ -z "$A" ]; then
  printf 'root file\n' > $O/r644
  $P/tools/mkinitramfs $O/fds.cpio /bin/fdtab=$L/bin/fdtab:755 /bin/as=$L/bin/as:755 /g/:1777 /g/r644=$O/r644:644 > $O/fds.cpio.txt || exit 1
  A=$O/fds.cpio
fi
sha256sum $A
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob50 $A $O/fds.keys "/bin/fdtab" $O fds & a=$!
$P/notes/px48/linux-vm.sh $P $L/bin/vmjob50 $A $O/fds.keys "/bin/as 1000 1000 /bin/fdtab" $O fds-user & b=$!
wait $a; echo "root: $?"; wait $b; echo "user: $?"
cat $O/vm-fds.meta $O/vm-fds-user.meta
for n in fds fds-user; do echo "=== $n"; tr -d '\r' < $O/$n.tty; done
