#!/bin/bash
# px55 on kasumi (pax#93, #94): the tree probe (user/elf/tree.c, a suite build's own probes and probes-user
# archives as they are) on real root's guest (kasumi's own kernel image under QEMU, px48's linux-vm.sh, px52's
# vmjob: devtmpfs, /proc, the four /dev links), as root and as 1000:1000, for what Linux's boot answers in the
# probe's `proc:` section: /proc/self/limits and /proc/sys/kernel/core_pattern (its other sections are the
# container's to compare, mpx3-tree T1). The section's lines kept as they are (their blanks too), and od -c of
# the limits rows' ends.
#   vm-tree.sh BUILDDIR OUTDIR
L=$HOME/lanes/px55; P=$L/pax; W=$1/mpx3-tree; O=$2
set -u
mkdir -p $O $L/bin
[ -x $L/bin/vmjob52 ] || podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob52 $P/notes/px52/vmjob.c" || exit 1
sha256sum $L/bin/vmjob52 $W/probes.cpio $W/probes-user.cpio
: > $O/none.keys
taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob52 $W/probes.cpio $O/none.keys "/bin/tree" $O tree > $O/tree.vm.out 2>&1 & a=$!
taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob52 $W/probes-user.cpio $O/none.keys "/bin/as 1000 1000 /bin/tree" $O tree-user > $O/tree-user.vm.out 2>&1 & b=$!
wait $a; echo "root: $?"; wait $b; echo "user: $?"
for n in tree tree-user; do
  tr -d '\r' < $O/$n.tty | grep -a '^~*proc: ' > $O/$n.proc
  echo "== $n ($(wc -l < $O/$n.proc) proc lines; status $(cat $O/$n.tty.rc))"; cat $O/$n.proc
  grep -a '^~proc: limits: ' $O/$n.proc | sed 's/^~proc: limits: //' | awk '{ print length($0) }' | sort | uniq -c
done
grep -a '^~proc: limits: Max nice' $O/tree.proc | od -c | tail -n 4
