#!/bin/bash
# px53: PAX's first boot of the new images (head1's groups and sigs, the
# suite's own keys and qemu-halt line), before any recording of them.
L=$HOME/lanes/px53
P=$L/pax
W=$L/build/head1/mpx5-jobs
O=$L/ev/first-new
mkdir -p $O
export PAX_CACHE=$L/cache PAX_BUILD=$O
cat $P/user/console/groups.keys $P/user/console/groups.keys > $O/groups.keys
: > $O/sigs.keys
for im in groups sigs; do
  taskset -c 0-3 $P/tools/qemu-halt --firmware bios --serial $O/$im.serial.log --timeout 900 --qemu -m --qemu 512M \
    --elf $W/native/kmain_console.elf --marker 'halt|PANIC .*' --type $O/$im.keys --prompt '$ ' --keyboard serial $W/native/$im.iso > $O/$im.verdict 2>&1
  echo "$im: $? $(tail -n 1 $O/$im.verdict)"
  sha256sum $W/native/$im.iso $W/$im.cpio $W/native/kmain_console.elf $O/$im.serial.log
done
