#!/bin/bash
# px51 on kasumi: how many threads boreutils' timeout runs while it waits, on PAX (the groups image of a
# mpx5-jobs build, its two runs: root and 1000:1000) and on real root's guest (1 CPU), read from
# /proc/<pid>/status at pelt's prompt (notes/px51/threads.keys). Not a suite row: the container's count is its host's.
#   threads.sh BUILDTAG OUTDIR
L=$HOME/lanes/px51
W=$L/build/$1/mpx5-jobs; O=$2; P=$L/pax
mkdir -p $O
cat $P/notes/px51/threads.keys $P/notes/px51/threads.keys > $O/keys
cd $P
export PAX_CACHE=$L/cache PAX_BUILD=$O
taskset -c 0-3 tools/qemu-halt --firmware bios --serial $O/serial.log --timeout 600 --qemu -m --qemu 512M --elf $W/native/kmain_console.elf --marker 'halt|PANIC .*' --type $O/keys --prompt '$ ' $W/native/groups.iso > $O/verdict 2>&1
echo "PAX: qemu-halt $?"; . tools/lib.sh; serial_norm $O/serial.log | grep -a 'timeout: Threads\|st=\|refused\|ENOSYS' | sort | uniq -c
taskset -c 4-15 $P/notes/px48/linux-vm.sh $P $L/bin/vmjob51 $W/pjobs.cpio $P/notes/px51/threads.keys "/bin/sh -i -m" $O linux > /dev/null 2>&1
echo "Linux guest (1 CPU):"; tr -d '\r' < $O/linux.tty | grep -a 'timeout: Threads\|st='
