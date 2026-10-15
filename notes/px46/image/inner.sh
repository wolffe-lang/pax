#!/bin/bash
# px46: the exploration image (pxdemo's recipe) at px46's head: pelt 7dd3304, every boreutils utility at 23ea8dd, su, as.
# Runs inside px13-ubuntu; L=~/lanes/px46 mounted at the same path; cwd the pax tree.
set -euo pipefail
L=/home/mfwolffe/lanes/px46
export PAX_CACHE=$L/cache TMPDIR=$L/tmp CARGO_INCREMENTAL=0 PAX_BUILD=$L/demo/build
mkdir -p $L/tmp $L/demo/out $PAX_BUILD
cd $L/pax
head=$(git -c safe.directory='*' rev-parse --short HEAD); echo "pax $head"
W=$(tools/fetch-wolf | tail -n 1); export PAX_WOLF=$W
tools/fetch-limine
O=$L/demo/out
BORE=$(cd $L/boresrc && for f in src/*.lu; do case $f in *_test.lu) continue;; esac; basename $f .lu; done | tr '\n' ' ')
echo "boreutils: $BORE"
tools/mkpelt $O/pelt > $O/pelt.txt
tools/mkboreutils $O/bore $BORE > $O/bore.txt
tools/mksu $O/su > $O/su.txt
tools/mkcred $O/cred > $O/cred.txt
tools/mkzone $O/localtime > $O/zone.txt
S=$O/stage; rm -rf $S; mkdir -p $S
printf 'root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\nlobo:x:990:990:lobo:/srv/lobo:/bin/false\n' > $S/passwd
printf 'root:x:0:\npax:x:1000:\nlobo:x:990:\n' > $S/group
printf 'ENV_PATH\tPATH=/bin\nENV_SUPATH\tPATH=/bin\n' > $S/login.defs
printf 'PAX trunk + px46 (%s): pelt as pid 1, boreutils in /bin, accounts root, pax and lobo; `su pax` to become pax. Type `exit` to halt.\n' "$head" > $S/motd
echo /bin/pelt > $S/pax-run
printf 'hello from pax\n' > $S/hello.txt
printf 'owners: px42\nchecks: px43-px45\naccounts: px46\n' > $S/todo
printf 'left here by root\n' > $S/from-root
printf '<p>lobo</p>\n' > $S/index.html
printf 'root only: 0600\n' > $S/secret
printf 'anyone may read this: 0644\n' > $S/readme
args=("/bin/pelt=$O/pelt/pelt:755" "/bin/su=$O/su/su:755" "/bin/as=$O/cred/as:755")
for u in $BORE; do args+=("/bin/$u=$O/bore/$u:755"); done
args+=("/etc/passwd=$S/passwd:644" "/etc/group=$S/group:644" "/etc/login.defs=$S/login.defs:644" "/etc/localtime=$O/localtime:644"
  "/etc/motd=$S/motd:644" "/etc/pax-run=$S/pax-run:644"
  "/etc/secret=$S/secret:600" "/etc/readme=$S/readme:644"
  "/tmp/:1777"
  "/root/:700" "/root/secret=$S/secret:600"
  "/home/pax/:755:1000:1000" "/home/pax/hello.txt=$S/hello.txt:644:1000:1000" "/home/pax/notes/:700:1000:1000"
  "/home/pax/notes/todo=$S/todo:600:1000:1000" "/home/pax/shared=$S/hello.txt:664:1000:990" "/home/pax/from-root=$S/from-root:644"
  "/srv/lobo/:750:990:990" "/srv/lobo/index.html=$S/index.html:640:990:990")
tools/mkinitramfs $O/pax-trunk-u6.cpio "${args[@]}" > $O/initramfs.txt
tail -1 $O/initramfs.txt
elf=$(tools/build-kernel --src kernel/kmain_console.lu $O/native 2>$O/build-kernel.log)
echo "elf: $elf $(sha256sum $elf | cut -d' ' -f1)"
tools/mkimage --conf boot/limine-initramfs-quiet.conf --add $O/pax-trunk-u6.cpio initramfs.cpio "$elf" $O/pax-trunk-u6.iso > $O/mkimage.txt
sha256sum $O/pax-trunk-u6.iso
rm -rf $PAX_BUILD
echo INNER-DONE
