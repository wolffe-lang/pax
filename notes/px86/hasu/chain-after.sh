#!/usr/bin/env bash
# px86: after the stick, in ONE hold of block A (both names; about 15 minutes, never idle), every step run
# whatever the last one's exit (red steps are expected red by name):
#   red2       the used rows at the second tests-only head 50aa4b15 (8495bdc0's installer): red by name
#   coverage   R-px86-1's measurement: what PAX's formatters leave of a used disk (scripts/coverage.py)
#   plant-*    px86-plant-used (PLANT_HEAD: zero-bios logged durable, nothing written), locally (RULES 7):
#              the executor unit, the used rows, the 860 leg (fat32) under KVM: red by name
#   chain-after.sh PLANT_HEAD
set -u
L=/home/mfwolffe/lanes/px86
PH=$1
printf '%s\n' "$$" > $L/chain-after.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
P=/home/mfwolffe/lanes/hasu-env/bin/podman
ts() { date -u +%FT%TZ; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; echo $rc > $L/after-$n.exit; return 0; }
ctr() { # NAME DIR IMAGE KVM CMD... (the block is held by this chain)
  local n=$1 dir=$2 img=$3 kvm=$4; shift 4; local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  $P run --rm --name "px86-$n" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$dir" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/pbuild -e TMPDIR=$L/tmp -e PAX_LOPE_REPO=$L/inputs/lope-local -e CARGO_INCREMENTAL=0 \
    ${CTR_ENV:-} "$img" taskset -c 0-5 "$@"
}
used_rows() { # TAG WORK INPUTS
  local tag=$1 w=$2 i=$3
  printf '%s\n' 'export PAX_WOLF=$(tools/fetch-wolf) SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
git log --oneline -1
D=tests/mpx6-install.d
for used in fat32 ext4 iso; do
  rm -rf '"$w"'/'"$tag"'-$used
  echo "== I-used-$used"
  if PAX_INSTALL_USED=$used python3 -I $D/install.py $PWD '"$i $w"'/'"$tag"'-$used no vdb; then
    python3 -I $D/verify.py $PWD '"$w"'/'"$tag"'-$used no vdb && python3 -I $D/gap.py '"$w"'/'"$tag"'-$used '"$i"'/build/disktools/limine/limine && tools/used-disk check '"$w"'/'"$tag"'-$used/target.img I-used-signatures-$used
    echo "ROW I-used-$used rest exit=$?"
  else echo "ROW I-used-$used install exit=$?"; fi
  tools/used-disk check '"$w"'/'"$tag"'-$used/target.img I-used-signatures-$used-as-left || true
  grep -E "ISOHYBRID|Converting|Cannot convert|phase zero-|phase limine" '"$w"'/'"$tag"'-$used/install.serial | head -12 || true
done'
}
exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
until flock -w 240 9; do printf '%s hasu-block-A.lock held; waiting\n' "$(ts)"; done
exec 8>/home/mfwolffe/lanes/hasu-A.lock
until flock -w 240 8; do printf '%s hasu-A.lock held; waiting\n' "$(ts)"; done
printf '%s block A acquired (both names) chain-after\n' "$(ts)"

# red2: the red clone at 50aa4b15 (user/ as at 59e7eb1b: the red inputs' installer is 8495bdc0's).
red2() {
  git -C $L/red fetch -q origin && git -C $L/red checkout -q 50aa4b15 || return 3
  [ -z "$(git -C $L/red diff --stat 59e7eb1b 50aa4b15 -- user/)" ] || { echo "user/ moved"; return 3; }
  ctr red2-used-rows $L/red localhost/px78-ubuntu:1 0 bash -c "$(used_rows red2 $L/w-red $L/w-red/inputs)"
}
step red2 red2
step coverage ctr coverage $L/green localhost/px75-ubuntu:2 0 python3 -I $L/scripts/coverage.py $L/w-red/inputs/build/disktools/bin $L/w-coverage

S=$L/plant W=$L/w-plant I=$L/w-plant/inputs
plant_inputs() {
  [ "$(git -C $S rev-parse HEAD)" = "$PH" ] || { echo "plant clone not at $PH"; return 3; }
  rm -rf $W && mkdir -p $W && cp -a $L/w-red/inputs $I && \
  ctr plant-installer $S localhost/px75-ubuntu:2 0 bash -c "tools/mkinstall $I/build/install-gate/bin && cat $I/build/install-gate/bin/install.sha256"
}
step plant-inputs plant_inputs
step plant-unit-executor ctr plant-unit-executor $S localhost/px75-ubuntu:2 0 bash -c "tests/mpx6-install --only executor --work $L/w-plant-units"
step plant-used-rows ctr plant-used-rows $S localhost/px78-ubuntu:1 0 bash -c "$(used_rows plant $W $I)"
plant_build() { ( cd $S && export PAX_CACHE=$L/cache PAX_BUILD=$L/pbuild-host TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_METAL_MODE=build && taskset -c 0-5 tests/mpx6-install --only metal --work $W/leg-used-fat32 --inputs $I ); }
step plant-metal-build plant_build
CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm -e PAX_METAL_TARGET=860 -e PAX_METAL_USED=fat32" \
  step plant-metal-run ctr plant-metal-run $S localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/leg-used-fat32 --inputs $I"
flock -u 8; exec 8>&-; flock -u 9; exec 9>&-
printf '%s block A RELEASED (both names) chain-after\n' "$(ts)"
printf '%s CHAIN-AFTER DONE\n' "$(ts)"
