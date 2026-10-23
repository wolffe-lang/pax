#!/bin/bash
# px65: px64's builder (px60's recipe as px62 made it lane-local,
# notes/px62/dev-iso/build.sh), lane-local again: the base userspace at
# the pins of the tree in $L/pax (user/*.pin: pelt, boreutils' 61
# utilities, lope, aspen, yew, scent, su, play), built in the lane's own
# Ubuntu 24.04 container (localhost/px65-ubuntu, notes/px65/Containerfile)
# on CPUs 12-15; the musl lupin by tools/mklupin in px57-rust (the
# recipe's Rust image, used as it is). lope is private: the lane's own
# clone (~/lanes/px65/lope). The static wolf is verify.sh's (this lane's
# mkwolf build), the native link stack px60's. No boot here.
set -euo pipefail
L=$HOME/lanes/px65/dev
printf '%s\n' $$ > "$L/build.pid"
U="base32 base64 basename cat chgrp chmod chown comm cp cut dirname echo env expand false fold groups head id join kill link ln logname ls mkdir mkfifo mktemp mv nl nproc paste printenv printf pwd readlink realpath rm rmdir seq shuf sleep sort stat sync tac tail tee timeout touch tr true truncate tsort tty unexpand uniq unlink wc whoami yes"
mkdir -p "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v $L:$L:Z -v $HOME/lanes/px65/lope:$HOME/lanes/px65/lope:ro -e PAX_LOPE_REPO=$HOME/lanes/px65/lope -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e U="$U" -e L="$L" localhost/px65-ubuntu bash -c '
set -euo pipefail; cd $L/pax; W=$L/w; rm -rf $W; mkdir -p $W
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
elf=$(tools/build-kernel --src kernel/kmain_console.lu $W/native 2>$W/kernel.log); echo "kernel rc=$? elf=$elf"
echo "$elf" > $W/elf.path
cat $W/scent/sums.txt
ls -la $W/pelt $W/lope $W/aspen $W/scent $W/yew $W/bin $W/su $W/play
'
rc=$?
R=${PAX_RUST_IMAGE:-localhost/px57-rust}
podman image exists $R || { echo "missing the recipe's Rust image: $R"; exit 2; }
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v $L:$L:Z -e L="$L" -e CARGO_INCREMENTAL=0 $R bash -c 'cd $L/pax && tools/mklupin $L/w/lupin > $L/w/lupin.txt 2>&1; echo "mklupin rc=$?"; ls -la $L/w/lupin'
echo "build.sh done rc=$rc $(date -Is)"
