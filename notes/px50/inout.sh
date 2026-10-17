#!/bin/bash
# px50 on kasumi: boreutils' cat with its input its output — mpx3-tree's shell-inout and shell-inout-user
# sessions on PAX (a build's images and kernel) and in a throwaway container, compared as T1 compares them.
#   inout.sh BUILDDIR(mpx3-tree's work dir) OUTDIR [KEYSDIR]
L=$HOME/lanes/px50
B=$1 O=$2 K=${3:-$L/pax/user/console}
mkdir -p $O
cd $L/pax
export PAX_CACHE=$L/cache PAX_BUILD=$O PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
. tools/lib.sh
for s in shell-inout shell-inout-user; do
  p=shell; own=(); case $s in *-user) p=shell-user; own=(--owners $B/shell-user.owners) ;; esac
  tools/qemu-halt --firmware bios --serial $O/$s.serial.log --timeout 300 --qemu -m --qemu 512M --elf $B/native/kmain_console.elf \
      --marker 'halt|PANIC .*' --type $K/$s.keys --prompt '$ ' $B/native/tree-$p.iso > $O/$s.verdict 2>&1
  echo "$s qemu-halt: $?; $(tail -1 $O/$s.verdict)"
  serial_norm $O/$s.serial.log > $O/$s.norm
  awk '/^user: exec pid 1 / { if (!on) { on = 1; next } } on && /^user: [^ ]+ pid 1 (exit_group|exit) [0-9]+ after / { exit }
       on { i = index($0, "user: "); if (i == 1) next; if (i > 1) { printf "%s", substr($0, 1, i - 1); next } print }' $O/$s.norm | grep -v '^~' > $O/$s.pax
  tools/linux-tree --root $B/$p/root --keys $K/$s.keys --prompt '$ ' --argv0 /bin/pelt --size 512m ${own[@]+"${own[@]}"} $O/$s.tty -- /bin/pelt
  serial_norm $O/$s.tty | grep -v '^~' > $O/$s.linux
  [ -z "$(tail -c 1 $O/$s.linux)" ] || printf '\n' >> $O/$s.linux
  if cmp -s $O/$s.linux $O/$s.pax; then echo "$s: SAME, $(wc -l < $O/$s.pax) lines, $(grep -c 'input file is output file' $O/$s.pax) refusals"
  else echo "$s: DIFFER"; diff $O/$s.linux $O/$s.pax | head -40; fi
  grep -a 'refused\|ENOSYS\|PANIC\|killed' $O/$s.norm | sed -E 's/pid [0-9]+/pid N/' | sort | uniq -c
done
