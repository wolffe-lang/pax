#!/bin/bash
# px64: the dev image's builder (px60's recipe as px62 made it lane-local,
# notes/px62/dev-iso/build.sh), lane-local again: the base userspace at
# the pins of the tree in $L/pax (user/*.pin), plus scent
# (tools/mkscent), built in the lane's own Ubuntu 24.04 container
# (localhost/px64-ubuntu, notes/px64/Containerfile) on CPUs 12-15; the
# musl lupin in px57-rust (the recipe's Rust image, used as it is). The
# static wolf, its runtime and the native link stack are NOT rebuilt:
# verify.sh checks px60's retained bytes. No boot here.
set -euo pipefail
L=$HOME/lanes/px64/dev
printf '%s\n' $$ > "$L/build.pid"
U="basename cat chgrp chmod chown cp cut dirname echo env expand false fold groups head id kill ln logname ls mkdir mv nl nproc paste printenv printf pwd readlink rm rmdir seq sleep sort stat tac tail tee timeout touch tr true unexpand uniq wc whoami yes"
mkdir -p "$L/cache" "$L/tmp"
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e U="$U" -e L="$L" localhost/px64-ubuntu bash -c '
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
