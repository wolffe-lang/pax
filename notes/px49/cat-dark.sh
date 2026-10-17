#!/bin/bash
# px49 on kasumi: boreutils cat (8f0bbb1) asked to append a file to itself, on PAX (mpx3-tree's shell image,
# a build's kernel) and in a throwaway container (the same tree): Linux refuses, PAX copies (no /proc/self/fd links).
#   cat-dark.sh BUILDTAG
L=$HOME/lanes/px49
B=$L/build/$1
O=$L/build/cat-dark
mkdir -p $O
printf '%s\n' 'echo abc > /cf' 'cat /cf >> /cf; echo "status $?"' 'cat /cf' 'exit' > $O/keys
cd $B/pax
export PAX_CACHE=$L/cache PAX_BUILD=$O PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
tools/qemu-halt --firmware bios --serial $O/serial.log --timeout 600 --qemu -m --qemu 512M --elf $B/mpx3-tree/native/kmain_console.elf --marker 'halt|PANIC .*' --type $O/keys --prompt '$ ' $B/mpx3-tree/native/tree-shell.iso > $O/verdict 2>&1
echo "qemu-halt: $?"; tail -1 $O/verdict
. tools/lib.sh; serial_norm $O/serial.log | grep -av '^user: ' | sed -n '/^\$ echo abc/,/^\$ exit/p' > $O/pax.txt
tools/linux-tree --root $B/mpx3-tree/shell/root --keys $O/keys --prompt '$ ' --argv0 /bin/pelt --size 512m $O/linux.tty -- /bin/pelt
serial_norm $O/linux.tty | sed -n '/^\$ echo abc/,/^\$ exit/p' > $O/linux.txt
echo "=== PAX"; cat $O/pax.txt; echo "=== Linux (container)"; cat $O/linux.txt
