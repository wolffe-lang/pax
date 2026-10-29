set -euo pipefail
L=/mnt/steamlib/lanes/px84
D=$L/build/r8-mke2fs; rm -rf $D; mkdir -p $D
mke2fs -V 2>&1 | head -1
sed -n '/^\[defaults\]/,/^\[fs_types\]/p;/^\[fs_types\]/,$p' /etc/mke2fs.conf | grep -E '^\[|inode_ratio|^\s+(small|floppy|big|huge|default|ext2)\s*=' 
for s in 536866816 536870912 8589934592 68719476736 500000000000 4000000000000 4398046507008 4398046511104 17592186040320; do
  f=$D/probe.img; rm -f $f; truncate -s $s $f
  line=$(mke2fs -n -F -t ext2 -b 4096 $f 2>&1 | grep -E 'Creating filesystem with')
  echo "mke2fs -n -t ext2 -b 4096 $s: $line"
  rm -f $f
done
