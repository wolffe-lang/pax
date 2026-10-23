#!/bin/bash
# px65: boot the two probes (sigign.c, getattr.c) on PAX (kmain_console, native) in the lane's container.
set -u
D=$HOME/lanes/px65/exp/sigign
P=${PX65_TREE:-$HOME/lanes/px65/w-b}
E=$(ls $HOME/lanes/px65/build/a-mpx5-jobs/mpx5-jobs/native/kmain_console.elf)
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v $HOME/lanes/px65:$HOME/lanes/px65:Z -e PAX_CACHE=$HOME/lanes/px65/cache -e PAX_BUILD=$D/b -e D=$D -e P=$P -e E=$E localhost/px65-ubuntu bash -c '
cd $D; echo "kernel $E"; printf "/bin/sigign\n/bin/getattr\n" > pax-run
$P/tools/mkinitramfs s.cpio /bin/sigign=sigign:755 /bin/getattr=getattr:755 /etc/pax-run=pax-run:644 >/dev/null
$P/tools/mkimage --conf $P/boot/limine-initramfs.conf --add s.cpio initramfs.cpio $E s.iso >/dev/null
cd $P && taskset -c 12-15 tools/qemu-halt --firmware bios --serial $D/serial.log --timeout 120 --elf $E --marker "halt|PANIC .*" $D/s.iso | tail -1
grep -a -E "parent|child|getattr|ENOSYS|refused" $D/serial.log'
