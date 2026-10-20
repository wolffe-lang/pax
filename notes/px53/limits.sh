#!/bin/bash
# px53 on kasumi: what core limit and pattern a session's processes run
# under, black-box: on real root's guest (notes/px50/vmjob.c as pid 1,
# the pjobs archive, pelt typing notes/px53/limits.keys as root and as
# 1000:1000) and on PAX (the groups image, the same keys typed at both
# of its shells), before any core row is recorded.
#   limits.sh BUILDTAG OUTDIR
L=$HOME/lanes/px53
W=$L/build/$1/mpx5-jobs; O=$2
P=$L/pax
K=$P/notes/px53/limits.keys
set -u
mkdir -p $O $L/bin
[ -x $L/bin/vmjob51 ] || podman run --rm --network none -v $L:$L:Z localhost/px13-ubuntu bash -c "cc -static -O1 -o $L/bin/vmjob51 $P/notes/px50/vmjob.c" || exit 1
sha256sum $L/bin/vmjob51 $W/pjobs.cpio $W/native/groups.iso $K
taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob51 $W/pjobs.cpio $K "/bin/sh -i -m" $O limits > $O/limits.vm.out 2>&1 &
taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob51 $W/pjobs.cpio $K "/bin/as 1000 1000 /bin/sh -i -m" $O limits-user > $O/limits-user.vm.out 2>&1 &
wait
cat $K $K > $O/pax-limits.keys
export PAX_CACHE=$L/cache PAX_BUILD=$O
taskset -c 0-3 $P/tools/qemu-halt --firmware bios --serial $O/pax-limits.serial --timeout 900 --qemu -m --qemu 512M \
    --elf $W/native/kmain_console.elf --marker 'halt|PANIC .*' --type $O/pax-limits.keys --prompt '$ ' --keyboard serial $W/native/groups.iso > $O/pax-limits.verdict 2>&1
echo "pax: $(tail -n 1 $O/pax-limits.verdict)"
for f in limits limits-user; do echo "== guest $f (status $(cat $O/$f.tty.rc))"; tr -d '\r' < $O/$f.tty; done
echo "== pax"; tr -d '\r' < $O/pax-limits.serial | grep -v '^user: '
