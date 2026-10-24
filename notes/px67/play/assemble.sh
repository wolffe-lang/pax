#!/bin/bash
# px67, kasumi: the playground as one disk whose partition 2 is `/`,
# pax-disk.img, from build.sh's output: px66's assembly
# (notes/px66/play/assemble.sh) with three changes. The image's
# /etc/fstab is user/fstab-root (`/dev/vda2 / ext2 rw 0 1`, a tmpfs
# /tmp: R-px67-1); the archive holds /root (0700, Linux's) and
# /etc/mtab (a link to ../proc/self/mounts); and the disk is
# `tools/mkdisk --gpt --root`: the archive's tree installed onto
# partition 2 by mkdisk --from with the --attrs file it generates from
# the archive's headers, the ESP holding Limine and the kernel only
# (R-px67-2: Limine loads no initramfs; the entry's command line gains
# `root=PARTUUID=<partition 2> rw`), /home a directory of `/`
# (R-px67-3), Limine's BIOS stage in partition 3. Made on the host
# (tools/mkdisk runs its tools in their pinned containers; the epoch the
# head commit's, so one commit makes one disk). The binaries are
# stripped copies (a tinkering image, not a suite's evidence), but for
# scent, as px64's dev image has it.
#
#   PX67_HEAD=<sha> PX67_EPOCH=<commit time> P=<tree> assemble.sh [SIZE]
set -u
size=${1:-512M}
L=$HOME/lanes/px67/play
P=${P:-$HOME/lanes/px67/pax}
printf '%s\n' $$ > "$L/assemble.pid"
HEAD=${PX67_HEAD:-unknown}
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$P:$P:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e L="$L" -e P="$P" -e HEAD="$HEAD" localhost/px13-ubuntu bash -c '
set -u; cd $P; W=$L/w; S=$W/strip
rm -rf $S; mkdir -p $S
for f in $W/bore/*; do case $f in *.txt) continue ;; esac; strip -o $S/${f##*/} $f || echo "strip failed $f"; done
strip -o $S/pelt $W/pelt/pelt; strip -o $S/lope $W/lope/lope; strip -o $S/aspen $W/aspen/aspen; strip -o $S/yew $W/yew/yew; strip -o $S/lupin $W/lupin/lupin; strip -o $S/su $W/su/su; strip -o $S/play $W/play/play; cp $W/bin/as $S/as; cp $W/probe/reboot $S/reboot
cp $W/scent/scent $W/scent/egrep $W/scent/fgrep $S/
printf "root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\nlobo:x:990:990:lobo:/srv/lobo:/bin/false\n" > $W/passwd
printf "root:x:0:\npax:x:1000:\nlobo:x:990:\n" > $W/group
cat > $W/motd <<MOTD
PAX playground: pax px67 $HEAD, wolf 0.2.35, pelt 70eec14, boreutils 575dc7b (61 tools), lope e6f623c,
aspen 3692cf5, scent b6f63a4 (grep), lupin 0.1.56 (static musl). pelt is pid 1 with job control (sh -i -m).
Try: ls -l /bin, jobs, Ctrl-Z, bg, fg, kill %1, timeout, su pax, play mambo.
lope jumps (its hook in /etc/shrc): cd /etc, cd /bin, then etc alone, g -, gi; lope add DIR, lope list.
aspen is tree(1) in wolf: aspen /, aspen -a -L 2 /home/pax, aspen -J /bin, aspen --du /usr.
scent is grep(1) in wolf (/bin/grep links to it; egrep, fgrep): grep -n pax /etc/passwd.
lupin runs wolf programs: cd /usr/share/lupin; lupin run hello.lu (or write one: cat > x.lu).
yew is the editor (77c1083), on this screen as on a Linux VT: yew notes.txt; i types, Esc, :w saves, :q quits, C-z and fg.
This machine booted from its disk, pax-disk.img, and / is on it: partition 2 (ext2, /dev/vda2),
installed from the image at build time; Limine and the kernel are on partition 1. cat /proc/self/mounts.
Everything you write stays (/etc, /root, /home/pax, /bin), but /tmp, which is memory.
Try: echo hello > /etc/motd; lope add /usr/share/tunes; cat > notes.txt (Ctrl-D ends it); reboot.
exit (or Ctrl-D) ends every process, writes / and marks it clean, then halts;
closing QEMU without exit is a power cut (the next boot says "not cleanly unmounted").
MOTD
{ cat user/shrc; printf "\n# px63, the playground: start at home (/home/pax, on the disk).\ncd\n"; } > $W/shrc
printf "/bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m\n" > $W/play.run
args=(/tmp/:1777 /root/:700 /mnt/:755 /home/pax/:755:1000:1000 /etc/passwd=$W/passwd:644 /etc/group=$W/group:644 /etc/localtime=$W/localtime:644 /etc/motd=$W/motd:644 /etc/shrc=$W/shrc:644 /etc/fstab=user/fstab-root:644 /etc/mtab-\>../proc/self/mounts /bin/grep-\>scent)
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
export SOURCE_DATE_EPOCH=${PX67_EPOCH:?set PX67_EPOCH to the head commit time}
PAX_CACHE=$L/cache TMPDIR=$L/tmp taskset -c 0-3 tools/mkdisk --gpt --kernel "$(cat "$L/w/elf.path")" --root "$L/w/play.cpio" \
    --conf boot/limine-initramfs-quiet.conf --label pax-playground "$size" "$O/pax-disk.img"
echo "mkdisk --gpt --root rc=$?"
ls -las "$O"
sha256sum "$O/pax-disk.img"
sha256sum "$O/pax-disk.img"
echo "assemble.sh done $(date -Is)"
