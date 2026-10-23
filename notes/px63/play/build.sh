#!/bin/bash
# px63, kasumi: the playground's programs and kernel, px61's recipe
# (notes/px61/playground-build.sh, the orchestrator's orch-paxplay
# build.sh before it) made lane-local: the head's pins, CPUs 0-3, plus
# /bin/reboot (tools/mkdiskprobe). The shared recipes are not edited; no
# boot here.
set -u
L=$HOME/lanes/px63/play
P=$HOME/lanes/px63/pax
LOPE=$HOME/lanes/px61/lope   # a clone holding user/lope.pin's commit (lope is private), read only
printf '%s\n' $$ > "$L/build.pid"
U="basename cat chgrp chmod chown cp cut dirname echo env expand false fold groups head id kill ln logname ls mkdir mv nl nproc paste printenv printf pwd readlink rm rmdir seq sleep sort stat tac tail tee timeout touch tr true unexpand uniq wc whoami yes"
mkdir -p "$L/cache" "$L/tmp"
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$P:$P:Z" -v "$LOPE:$LOPE:ro" \
    -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$LOPE -e CARGO_INCREMENTAL=0 -e U="$U" -e L="$L" -e P="$P" localhost/px13-ubuntu bash -c '
set -u; cd $P; W=$L/w; rm -rf $W; mkdir -p $W
export PAX_WOLF=$(tools/fetch-wolf | tail -n 1); echo "wolf: $PAX_WOLF $($PAX_WOLF --version | head -n 1)"
tools/fetch-limine >/dev/null; echo "limine rc=$?"
tools/mkpelt $W/pelt > $W/pelt.txt 2>&1; echo "mkpelt rc=$?"
tools/mklope $W/lope > $W/lope.txt 2>&1; echo "mklope rc=$?"
tools/mkaspen $W/aspen > $W/aspen.txt 2>&1; echo "mkaspen rc=$?"
tools/fetch-std $W/std > $W/std.txt 2>&1; echo "std rc=$?"
tools/mkyew $W/yew > $W/yew.txt 2>&1; echo "mkyew rc=$?"
tools/mkboreutils $W/bore $U > $W/bore.txt 2>&1; echo "mkboreutils rc=$?"
tools/mkas $W/bin > $W/as.txt 2>&1; echo "mkas rc=$?"
tools/mksu $W/su > $W/su.txt 2>&1; echo "mksu rc=$?"
tools/mkplay $W/play > $W/play.txt 2>&1; echo "mkplay rc=$?"
tools/mkzone $W/localtime > $W/zone.txt 2>&1; echo "mkzone rc=$?"
tools/mkdiskprobe $W/probe > $W/probe.txt 2>&1; echo "mkdiskprobe rc=$?"
mkdir -p $W/native
elf=$(tools/build-kernel --src kernel/kmain_console.lu $W/native 2>$W/kernel.log); echo "kernel rc=$? elf=$elf"
echo "$elf" > $W/elf.path
ls -la $W/pelt $W/lope $W/aspen $W/yew $W/bin $W/su $W/play $W/probe | head -60
'
rc=$?
# px57: the musl lupin, built in the throwaway Rust image (px13-ubuntu with rustup inside it).
R=${PAX_RUST_IMAGE:-localhost/px57-rust}
podman image exists $R || { echo "missing existing Rust image: $R"; exit 2; }
podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$P:$P:Z" -e L="$L" -e P="$P" -e CARGO_INCREMENTAL=0 $R bash -c 'cd $P && tools/mklupin $L/w/lupin > $L/w/lupin.txt 2>&1; echo "mklupin rc=$?"; ls -la $L/w/lupin'
echo "build.sh done rc=$rc $(date -Is)"
