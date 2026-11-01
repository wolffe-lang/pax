#!/usr/bin/env bash
# px86: the fix's rows at HEAD (the green clone; the units already green at 3308e975, logs/green-units2.log), then
# the maintainer's stick, all in ONE hold of block A (both names; about 20 minutes of work, never idle):
#   inputs     the red run's inputs copied (disk tools, pelt, lope, probes, games: unchanged by the fix), the
#              installer rebuilt at HEAD into the copy (px75-ubuntu:2)
#   used-rows  I-used-fat32, -ext4, -iso: install, verify, gap, signatures (px78-ubuntu:1, TCG)
#   leg        the kasumi leg on the used 860 (fat32), KVM: the stick built on the host, run in px78-ubuntu:1
#   stick      stick.sh HEAD SERIAL, STICK_HELD=1 (the hold is this chain's)
# A red step stops the chain and releases the block.
#   chain-green.sh HEAD SERIAL
set -uo pipefail
L=/home/mfwolffe/lanes/px86
HEAD=$1 SERIAL=$2
S=$L/green W=$L/w-green I=$L/w-green/inputs
printf '%s\n' "$$" > $L/chain-green.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
P=/home/mfwolffe/lanes/hasu-env/bin/podman
ts() { date -u +%FT%TZ; }
release() { flock -u 8; exec 8>&-; flock -u 9; exec 9>&-; printf '%s block A RELEASED (both names) chain-green\n' "$(ts)"; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; echo $rc > $L/green-$n.exit; [ $rc = 0 ] || { echo "CHAIN-GREEN STOPPED at $n"; release; exit $rc; }; }
ctr() { # NAME IMAGE KVM CMD... (the block is held by this chain)
  local n=$1 img=$2 kvm=$3; shift 3; local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  $P run --rm --name "px86-$n" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$S" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/pbuild -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/inputs/lope-local -e CARGO_INCREMENTAL=0 \
    ${CTR_ENV:-} "$img" taskset -c 0-5 "$@"
}
[ "$(git -C $S rev-parse HEAD)" = "$HEAD" ] && [ "$(git -C $L/stick rev-parse HEAD)" = "$HEAD" ] || { echo "a clone is not at $HEAD"; exit 3; }
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -w 240 9; do printf '%s hasu-block-A.lock held; waiting\n' "$(ts)"; done
exec 8>/home/mfwolffe/lanes/hasu-A.lock
until flock -w 240 8; do printf '%s hasu-A.lock held; waiting\n' "$(ts)"; done
printf '%s block A acquired (both names) chain-green\n' "$(ts)"
inputs() { rm -rf $W && mkdir -p $W && cp -a $L/w-red/inputs $I && ctr green-installer localhost/px75-ubuntu:2 0 bash -c "tools/mkinstall $I/build/install-gate/bin && cat $I/build/install-gate/bin/install.sha256"; }
step inputs inputs
rows='export PAX_WOLF=$(tools/fetch-wolf) SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
set -e
D=tests/mpx6-install.d
for used in fat32 ext4 iso; do
  rm -rf '"$W"'/used-$used
  echo "== I-used-$used"
  PAX_INSTALL_USED=$used python3 -I $D/install.py $PWD '"$I $W"'/used-$used no vdb
  python3 -I $D/verify.py $PWD '"$W"'/used-$used no vdb
  python3 -I $D/gap.py '"$W"'/used-$used '"$I"'/build/disktools/limine/limine
  tools/used-disk check '"$W"'/used-$used/target.img I-used-signatures-$used
  grep -E "phase zero-|Limine changed-byte|ISOHYBRID|Converting" '"$W"'/used-$used/install.serial | head -16 || true
done'
step used-rows ctr green-used-rows localhost/px78-ubuntu:1 0 bash -c "$rows"
hostbuild() { ( cd $S && export PAX_CACHE=$L/cache PAX_BUILD=$L/pbuild-host TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_METAL_MODE=build && taskset -c 0-5 tests/mpx6-install --only metal --work $W/leg-used-fat32 --inputs $I ); }
step metal-build-used-fat32 hostbuild
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm -e PAX_METAL_TARGET=860 -e PAX_METAL_USED=fat32" \
  step metal-run-used-fat32 ctr green-metal-used-fat32 localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/leg-used-fat32 --inputs $I"
export STICK_HELD=1
step stick bash $L/scripts/stick.sh "$HEAD" "$SERIAL"
release
printf '%s CHAIN-GREEN DONE\n' "$(ts)"
