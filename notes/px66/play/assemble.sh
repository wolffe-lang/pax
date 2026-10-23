#!/bin/bash
# px66, kasumi: the playground as one disk, pax-disk.img, from build.sh's
# output: px63's assembly (notes/px63/play/assemble.sh) made lane-local,
# with the initramfs's /etc/fstab the disk's (user/fstab-disk: /home is
# partition 2, /dev/vda2) and, in place of the ISO and pax-home.img,
# `tools/mkdisk --gpt`: an EFI system partition with Limine, the kernel
# and the initramfs (boot/limine-initramfs-quiet.conf, as the ISO had),
# partition 2 the ext2 /home (`--home`'s: /home/pax is pax's), and
# Limine's BIOS stage in partition 3. Made on the host (tools/mkdisk runs
# its tools in their pinned containers; the epoch the head commit's, so
# one commit makes one disk). The binaries are stripped copies (a
# tinkering image, not a suite's evidence).
#
#   PX66_HEAD=<sha> PX66_EPOCH=<commit time> assemble.sh [SIZE [ESP]]
set -u
size=${1:-512M}; esp=${2:-192M}
L=$HOME/lanes/px66/play
P=$HOME/lanes/px66/pax
printf '%s\n' $$ > "$L/assemble.pid"
HEAD=${PX66_HEAD:-unknown}
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$P:$P:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e L="$L" -e P="$P" -e HEAD="$HEAD" localhost/px13-ubuntu bash -c '
set -u; cd $P; W=$L/w; S=$W/strip
rm -rf $S; mkdir -p $S
for f in $W/bore/*; do case $f in *.txt) continue ;; esac; strip -o $S/${f##*/} $f || echo "strip failed $f"; done
strip -o $S/pelt $W/pelt/pelt; strip -o $S/lope $W/lope/lope; strip -o $S/aspen $W/aspen/aspen; strip -o $S/yew $W/yew/yew; strip -o $S/lupin $W/lupin/lupin; strip -o $S/su $W/su/su; strip -o $S/play $W/play/play; cp $W/bin/as $S/as; cp $W/probe/reboot $S/reboot
printf "root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\nlobo:x:990:990:lobo:/srv/lobo:/bin/false\n" > $W/passwd
printf "root:x:0:\npax:x:1000:\nlobo:x:990:\n" > $W/group
cat > $W/motd <<MOTD
PAX playground: pax px66 $HEAD, wolf 0.2.34, pelt 57ffef9, boreutils 12de639, lope bc38867,
aspen 476edee, lupin 0.1.55 (static musl). pelt is pid 1 with job control (sh -i -m).
Try: ls -l /bin, jobs, Ctrl-Z, bg, fg, kill %1, timeout, su pax, play mambo.
lope jumps (its hook in /etc/shrc): cd /etc, cd /bin, then etc alone, g -, gi.
aspen is tree(1) in wolf: aspen /, aspen -a -L 2 /home/pax, aspen -J /bin, aspen --du /usr.
lupin runs wolf programs: cd /usr/share/lupin; lupin run hello.lu (or write one: cat > x.lu).
yew is the editor (77c1083), on this screen as on a Linux VT: yew notes.txt; i types, Esc, :w saves, :q quits, C-z and fg.
This machine booted from its disk, pax-disk.img: Limine and the kernel on its partition 1,
/home on partition 2 (ext2, /dev/vda2 by /etc/fstab): the shell starts there. cat /proc/partitions.
What you write in /home stays: cat > notes.txt (Ctrl-D ends it), reboot, cat notes.txt.
Everything else is in memory, gone at the next boot. exit (or Ctrl-D) halts and marks /home clean;
closing QEMU without exit is a power cut (the next boot says "not cleanly unmounted").
MOTD
{ cat user/shrc; printf "\n# px63, the playground: start at home (/home/pax, on the disk).\ncd\n"; } > $W/shrc
printf "/bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m\n" > $W/play.run
args=(/tmp/:1777 /home/pax/:755:1000:1000 /etc/passwd=$W/passwd:644 /etc/group=$W/group:644 /etc/localtime=$W/localtime:644 /etc/motd=$W/motd:644 /etc/shrc=$W/shrc:644 /etc/fstab=user/fstab-disk:644)
for f in $S/*; do n=${f##*/}; case $n in pelt) args+=(/bin/pelt=$f:755 /bin/sh=$f:755) ;; *) args+=(/bin/$n=$f:755) ;; esac; done
while IFS= read -r -d "" f; do args+=(/usr/share/wolf/${f#"$W/std/"}=$f:644); done < <(find $W/std/std -type f -print0)
for t in user/tunes/*; do args+=(/usr/share/tunes/${t##*/}=$t:644); done
for t in user/lupin/*.lu; do args+=(/usr/share/lupin/${t##*/}=$t:644); done
tools/mkinitramfs $W/play.cpio "${args[@]}" /etc/pax-run=$W/play.run:644 > $W/play.initramfs.txt; echo "play cpio rc=$?"
'
echo "container part rc=$?"
O=$L/out
rm -rf "$O"; mkdir -p "$O"
cd "$P"
export SOURCE_DATE_EPOCH=${PX66_EPOCH:?set PX66_EPOCH to the head commit time}
PAX_CACHE=$L/cache TMPDIR=$L/tmp taskset -c 0-3 tools/mkdisk --gpt --kernel "$(cat "$L/w/elf.path")" --initramfs "$L/w/play.cpio" \
    --conf boot/limine-initramfs-quiet.conf --esp "$esp" --label pax-playground "$size" "$O/pax-disk.img"
echo "mkdisk --gpt rc=$?"
ls -las "$O"
sha256sum "$O/pax-disk.img"
sha256sum "$O/pax-disk.img"
echo "assemble.sh done $(date -Is)"
