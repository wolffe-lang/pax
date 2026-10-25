#!/bin/bash
# px80 (px65's build.sh, lane-local): the base userspace at the tree's pins
# (unchanged since px65: pelt 70eec14, boreutils 575dc7b, lope e6f623c,
# aspen 3692cf5, yew 77c1083, scent b6f63a4, su, play), built in px65's
# container (localhost/px80-ubuntu, notes/px65/Containerfile) on CPUs 0-3;
# the musl lupin by tools/mklupin in px57-rust. lope is private: a clone made
# from a bundle on kasumi ($HOME/lanes/px80/lope). The console kernel is
# linked by the bundle's own ld.lld 18.1.8 through notes/px80/lld-wrap, which
# links it again with the container's lld 18.1.3 and compares the two
# ($L/w/lld.log). No boot here.
set -euo pipefail
L=$HOME/lanes/px80/dev
P=$HOME/lanes/px80
printf '%s\n' $$ > "$L/build.pid"
U="base32 base64 basename cat chgrp chmod chown comm cp cut dirname echo env expand false fold groups head id join kill link ln logname ls mkdir mkfifo mktemp mv nl nproc paste printenv printf pwd readlink realpath rm rmdir seq shuf sleep sort stat sync tac tail tee timeout touch tr true truncate tsort tty unexpand uniq unlink wc whoami yes"
mkdir -p "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v $L:$L:Z -v $P/lope:$P/lope:ro -v $P/lld-out:/opt/px80:ro \
    -e PAX_LOPE_REPO=$P/lope -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e U="$U" -e L="$L" localhost/px80-ubuntu bash -c '
set -euo pipefail; cd $L/pax; W=$L/w; rm -rf $W; mkdir -p $W
git config --global --add safe.directory "*"
export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); echo "wolf: $PAX_WOLF $($PAX_WOLF --version | head -n 1)"
tools/fetch-limine >/dev/null; echo "limine rc=$?"
tools/mkpelt $W/pelt > $W/pelt.txt 2>&1; echo "mkpelt rc=$?"
tools/mklope $W/lope > $W/lope.txt 2>&1; echo "mklope rc=$?"
tools/mkaspen $W/aspen > $W/aspen.txt 2>&1; echo "mkaspen rc=$?"
tools/mkscent $W/scent > $W/scent.txt 2>&1; echo "mkscent rc=$?"
tools/mkyew $W/yew > $W/yew.txt 2>&1; echo "mkyew rc=$?"
tools/mkboreutils $W/bore $U > $W/bore.txt 2>&1; echo "mkboreutils rc=$?"
tools/mkas $W/bin > $W/as.txt 2>&1; echo "mkas rc=$?"
tools/mksu $W/su > $W/su.txt 2>&1; echo "mksu rc=$?"
tools/mkplay $W/play > $W/play.txt 2>&1; echo "mkplay rc=$?"
tools/mkzone $W/localtime > $W/zone.txt 2>&1; echo "mkzone rc=$?"
mkdir -p $W/native
echo "the console kernel links with: $(PATH=$L/pax/notes/px80/lld-wrap:$PATH PX80_LLD=/opt/px80/ld.lld /opt/px80/ld.lld --version)"
elf=$(PATH=$L/pax/notes/px80/lld-wrap:$PATH PX80_LLD=/opt/px80/ld.lld PX80_LLD_LOG=$W/lld.log \
    tools/build-kernel --src kernel/kmain_console.lu $W/native 2>$W/kernel.log); echo "kernel rc=$? elf=$elf"
cat $W/lld.log
echo "$elf" > $W/elf.path
cat $W/scent/sums.txt
ls -la $W/pelt $W/lope $W/aspen $W/scent $W/yew $W/bin $W/su $W/play
'
rc=$?
R=${PAX_RUST_IMAGE:-localhost/px57-rust}
podman image exists $R || { echo "missing the recipe's Rust image: $R"; exit 2; }
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v $L:$L:Z -e L="$L" -e CARGO_INCREMENTAL=0 $R bash -c 'cd $L/pax && tools/mklupin $L/w/lupin > $L/w/lupin.txt 2>&1; echo "mklupin rc=$?"; ls -la $L/w/lupin'
echo "build.sh done rc=$rc $(date -Is)"
