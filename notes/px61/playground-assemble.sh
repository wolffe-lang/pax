#!/bin/bash
# orch-paxplay: assemble the playground and smoke archives and ISOs from
# build.sh's output. The playground's binaries are stripped copies (a
# tinkering image, not a suite's evidence: the suites' binaries are
# unmodified).
set -eu
L=$HOME/lanes/px61
podman run --rm --privileged --cpuset-cpus 10-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e L="$L" localhost/px13-ubuntu bash -c '
set -eu; cd $L/pax; W=$L/w; S=$W/strip; O=$L/out
rm -rf $S $O; mkdir -p $S $O
for f in $W/bore/*; do case $f in *.txt) continue ;; esac; strip -o $S/${f##*/} $f || echo "strip failed $f"; done
strip -o $S/pelt $W/pelt/pelt; strip -o $S/lope $W/lope/lope; strip -o $S/aspen $W/aspen/aspen; strip -o $S/yew $W/yew/yew; strip -o $S/lupin $W/lupin/lupin; strip -o $S/su $W/su/su; strip -o $S/play $W/play/play; cp $W/bin/as $S/as
printf "root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\nlobo:x:990:990:lobo:/srv/lobo:/bin/false\n" > $W/passwd
printf "root:x:0:\npax:x:1000:\nlobo:x:990:\n" > $W/group
cat > $W/motd <<MOTD
PAX playground: pax px61, wolf 0.2.34, pelt 57ffef9, boreutils 12de639, lope bc38867,
aspen 476edee, lupin 0.1.55 (static musl). pelt is pid 1 with job control (sh -i -m).
Try: ls -l /bin, jobs, Ctrl-Z, bg, fg, kill %1, timeout, su pax, play mambo.
lope jumps (its hook in /etc/shrc): cd /etc, cd /bin, then etc alone, g -, gi.
aspen is tree(1) in wolf: aspen /, aspen -a -L 2 /home/pax, aspen -J /bin, aspen --du /usr.
lupin runs wolf programs: cd /usr/share/lupin; lupin run hello.lu (or write one: cat > x.lu).
yew is the editor (77c1083), on this screen as on a Linux VT: yew notes.txt; i types, Esc, :w saves, :q quits, C-z and fg.
Files and the lope store are in memory, gone at the next boot. exit (or Ctrl-D) halts.
MOTD
printf "/bin/env ENV=/etc/shrc /bin/sh -i -m\n" > $W/play.run
cat > $W/smoke.sh <<SMOKE
echo smoke: start
for u in \$(ls /usr/share/smoke-list); do :; done
n=0; for u in \$(cat /etc/smoke-list); do if [ -x /bin/\$u ]; then n=\$((n+1)); else echo "smoke: missing \$u"; fi; done; echo "smoke: present \$n"
cat /etc/motd
ls /bin | wc -l
seq 5 | sort -r | tr "\n" " "; echo
printf "%s\n" b a c a | sort | uniq | nl
id; whoami; groups; nproc
stat -c "%n %s %U" /etc/motd
basename /a/b/c.txt .txt; dirname /a/b/c.txt
echo hello | tee /tmp/t | wc -c; cat /tmp/t; rm /tmp/t
mkdir -p /tmp/d/e; touch /tmp/d/e/f; ls -R /tmp/d; rm -r /tmp/d
sleep 1 & echo "smoke: bg \$!"; wait; echo "smoke: wait rc=\$?"
timeout 1 sleep 5; echo "smoke: timeout rc=\$?"
as 1000 1000 /bin/id
play | head -3
echo smoke: end
SMOKE
printf "%s\n" basename cat chgrp chmod chown cp cut dirname echo env expand false fold groups head id kill ln logname ls mkdir mv nl nproc paste printenv printf pwd readlink rm rmdir seq sleep sort stat tac tail tee timeout touch tr true unexpand uniq wc whoami yes > $W/smoke-list
printf "/bin/sh /etc/smoke.sh\n" > $W/smoke.run
args=(/tmp/:1777 /home/pax/:755:1000:1000 /etc/passwd=$W/passwd:644 /etc/group=$W/group:644 /etc/localtime=$W/localtime:644 /etc/motd=$W/motd:644 /etc/shrc=user/shrc:644)
for f in $S/*; do n=${f##*/}; case $n in pelt) args+=(/bin/pelt=$f:755 /bin/sh=$f:755) ;; *) args+=(/bin/$n=$f:755) ;; esac; done
while IFS= read -r -d "" f; do args+=(/usr/share/wolf/${f#"$W/std/"}=$f:644); done < <(find $W/std/std -type f -print0)
for t in user/tunes/*; do args+=(/usr/share/tunes/${t##*/}=$t:644); done
for t in user/lupin/*.lu; do args+=(/usr/share/lupin/${t##*/}=$t:644); done
tools/mkinitramfs $W/play.cpio "${args[@]}" /etc/pax-run=$W/play.run:644 > $W/play.initramfs.txt; echo "play cpio rc=$?"
tools/mkinitramfs $W/smoke.cpio "${args[@]}" /etc/smoke.sh=$W/smoke.sh:644 /etc/smoke-list=$W/smoke-list:644 /etc/pax-run=$W/smoke.run:644 > $W/smoke.initramfs.txt; echo "smoke cpio rc=$?"
elf=$(cat $W/elf.path)
tools/mkimage --conf boot/limine-initramfs-quiet.conf --add $W/play.cpio initramfs.cpio $elf $O/pax-playground.iso >/dev/null; echo "play iso rc=$?"
tools/mkimage --conf boot/limine-initramfs-quiet.conf --add $W/smoke.cpio initramfs.cpio $elf $O/pax-smoke.iso >/dev/null; echo "smoke iso rc=$?"
ls -la $W/*.cpio $O; sha256sum $O/*.iso
'
echo "assemble.sh done rc=$?"
