#!/bin/bash
# orch-paxplay: a PAX playground image (pelt as an interactive job-control
# shell, boreutils, su, as, play, lope, aspen, lupin, yew) from pax trunk, built in px13-ubuntu
# (baseline glibc), as the suites build theirs. No boot here.
set -euo pipefail
L=$HOME/lanes/px60
U="basename cat chgrp chmod chown cp cut dirname echo env expand false fold groups head id kill ln logname ls mkdir mv nl nproc paste printenv printf pwd readlink rm rmdir seq sleep sort stat tac tail tee timeout touch tr true unexpand uniq wc whoami yes"
podman run --rm --privileged --cpuset-cpus 10-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e U="$U" -e L="$L" localhost/px13-ubuntu bash -c '
set -euo pipefail; cd $L/pax; W=$L/w; mkdir -p $W
export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); echo "wolf: $PAX_WOLF $($PAX_WOLF --version | head -n 1)"
tools/fetch-limine >/dev/null; echo "limine rc=$?"
tools/mkpelt $W/pelt > $W/pelt.txt 2>&1; echo "mkpelt rc=$?"
tools/mklope $W/lope > $W/lope.txt 2>&1; echo "mklope rc=$?"
tools/mkaspen $W/aspen > $W/aspen.txt 2>&1; echo "mkaspen rc=$?"
tools/mkyew $W/yew > $W/yew.txt 2>&1; echo "mkyew rc=$?"
tools/mkboreutils $W/bore $U > $W/bore.txt 2>&1; echo "mkboreutils rc=$?"
tools/mkas $W/bin > $W/as.txt 2>&1; echo "mkas rc=$?"
tools/mksu $W/su > $W/su.txt 2>&1; echo "mksu rc=$?"
tools/mkplay $W/play > $W/play.txt 2>&1; echo "mkplay rc=$?"
tools/mkzone $W/localtime > $W/zone.txt 2>&1; echo "mkzone rc=$?"
mkdir -p $W/native
elf=$(tools/build-kernel --src kernel/kmain_console.lu $W/native 2>$W/kernel.log); echo "kernel rc=$? elf=$elf"
echo "$elf" > $W/elf.path
ls -la $W/pelt $W/lope $W/aspen $W/yew $W/bore $W/bin $W/su $W/play
'
rc=$?
# px57: the musl lupin, built in the throwaway Rust image (px13-ubuntu with rustup inside it).
R=${PAX_RUST_IMAGE:-localhost/px57-rust}
podman image exists $R || podman build -t $R -f $L/pax/notes/px57/rust/Containerfile $L/pax/notes/px57/rust
podman run --rm --cpuset-cpus 10-15 -v $L:$L:Z -e L="$L" $R bash -c 'cd $L/pax && tools/mklupin $L/w/lupin > $L/w/lupin.txt 2>&1; echo "mklupin rc=$?"; ls -la $L/w/lupin'
echo "build.sh done rc=$rc"

# The dev inputs are built separately by tools/mkwolf and tools/mkwolf-std
# in the pinned Rust image; tools/mkdev adds them without changing base.
# No automatic deletion: this lane retains its build inputs for inspection.

podman run --rm -v "$L:$L" -e L="$L" -w "$L/pax" "$R" bash -c '
set -euo pipefail
tools/mkwolf "$L/final-out"
tools/mkwolf-std "$L/std"
tests/mpx5-wolf.d/verify-bins "$L/final-out"
'

bash "$L/pax/notes/px60/build-m2.sh"
