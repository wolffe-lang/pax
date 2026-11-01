#!/usr/bin/env bash
# px86: the one gauntlet at the final head HEAD, a fresh clone ($L/gaunt), fresh work directories, in one hold of
# block A (both names). It stops at the first nonzero step and prints every step's `END <step> exit=N`.
#   1 ci-plan        python3 tests/ci-plan (the planner's proofs; tools/used-disk derived to the install suites)
#   2 ci-budgets     python3 tests/ci-budgets.py
#   3 mpx6-install   tests/mpx6-install --rows smoke --tier native --firmware bios: the units, the inventory, the
#                    no/yes installs and their sessions, I-root-nvme, every fault row, and the used rows (fat32,
#                    ext4, iso), TCG, in px78-ubuntu:1 (verify.py's sgdisk)
#   4 kasumi-build   the two legs' sticks on the host (tools/mkdisk runs the disk tools in podman)
#   5 kasumi-870     the leg as CI runs it first: the blank 870 target, KVM, in px78-ubuntu:1
#   6 kasumi-860     the leg as CI runs it second: the used 860 (fat32), KVM
#   7 kasumi-860-ext4  the used 860 (ext4), KVM (local only)
#   8 mpx6-ahci      tests/mpx6-ahci --tier native --firmware bios --rows pr (the plan selects it for these paths)
#   gauntlet.sh HEAD
set -uo pipefail
L=/home/mfwolffe/lanes/px86
HEAD=$1
S=$L/gaunt W=$L/w-gaunt
printf '%s\n' "$$" > $L/gauntlet.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
P=/home/mfwolffe/lanes/hasu-env/bin/podman
ts() { date -u +%FT%TZ; }
release() { flock -u 8; exec 8>&-; flock -u 9; exec 9>&-; printf '%s block A RELEASED (both names) gauntlet\n' "$(ts)"; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; [ $rc = 0 ] || { echo "GAUNTLET STOPPED at $n"; release; exit $rc; }; }
ctr() { # NAME IMAGE KVM CMD...
  local n=$1 img=$2 kvm=$3; shift 3; local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  $P run --rm --name "px86-g-$n" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$S" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/gbuild -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/inputs/lope-local -e CARGO_INCREMENTAL=0 \
    ${CTR_ENV:-} "$img" taskset -c 0-5 "$@"
}
rm -rf $S $W $L/gbuild && git clone -q https://github.com/wolffe-lang/pax.git $S && git -C $S checkout -q -b gauntlet "$HEAD" || exit 3
[ "$(git -C $S rev-parse HEAD)" = "$HEAD" ] || exit 3
mkdir -p $W
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -w 240 9; do printf '%s hasu-block-A.lock held; waiting\n' "$(ts)"; done
exec 8>/home/mfwolffe/lanes/hasu-A.lock
until flock -w 240 8; do printf '%s hasu-A.lock held; waiting\n' "$(ts)"; done
printf '%s block A acquired (both names) gauntlet at %s\n' "$(ts)" "$HEAD"
step ci-plan ctr ci-plan localhost/px75-ubuntu:2 0 python3 -I tests/ci-plan
step ci-budgets ctr ci-budgets localhost/px75-ubuntu:2 0 python3 -I tests/ci-budgets.py
step mpx6-install ctr mpx6-install localhost/px78-ubuntu:1 0 bash -c "tests/mpx6-install --rows smoke --tier native --firmware bios --work $W/install"
kbuild() {
  ( cd $S && export PAX_CACHE=$L/cache PAX_BUILD=$L/gbuild-host TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_METAL_MODE=build \
    && taskset -c 0-5 tests/mpx6-install --only metal --work $W/kasumi --inputs $W/install/inputs \
    && taskset -c 0-5 tests/mpx6-install --only metal --work $W/kasumi/metal/used-fat32 --inputs $W/install/inputs \
    && taskset -c 0-5 tests/mpx6-install --only metal --work $W/kasumi-ext4 --inputs $W/install/inputs )
}
step kasumi-build kbuild
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm" \
  step kasumi-870 ctr kasumi-870 localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/kasumi --inputs $W/install/inputs"
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm -e PAX_METAL_TARGET=860 -e PAX_METAL_USED=fat32" \
  step kasumi-860 ctr kasumi-860 localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/kasumi/metal/used-fat32 --inputs $W/install/inputs"
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm -e PAX_METAL_TARGET=860 -e PAX_METAL_USED=ext4" \
  step kasumi-860-ext4 ctr kasumi-860-ext4 localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/kasumi-ext4 --inputs $W/install/inputs"
step mpx6-ahci ctr mpx6-ahci localhost/px78-ubuntu:1 1 bash -c "export PAX_WOLF=\$(tools/fetch-wolf); tests/mpx6-ahci --tier native --firmware bios --rows pr"
release
printf '%s GAUNTLET GREEN at %s\n' "$(ts)" "$HEAD"
