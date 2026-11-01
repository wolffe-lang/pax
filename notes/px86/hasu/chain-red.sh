#!/usr/bin/env bash
# px86: the rows red at the tests-only head (59e7eb1b: 8495bdc0's installer and the new rows).
# Each step takes and releases block A (both names) for itself; the chain runs every step whatever the
# last one's exit (each is expected red or green as notes/px86/prediction.txt says) and prints END lines.
set -u
L=/home/mfwolffe/lanes/px86
S=$L/red W=$L/w-red I=$L/w-red/inputs
printf '%s\n' "$$" > $L/chain-red.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
step() { local n=$1; shift; printf '%s START %s\n' "$(date -u +%FT%TZ)" "$n"; "$@"; local rc=$?; printf '%s STEP %s exit=%s\n' "$(date -u +%FT%TZ)" "$n" "$rc"; echo $rc > $L/red-$n.exit; return 0; }
[ "$(git -C $S rev-parse --short=8 HEAD)" = 59e7eb1b ] || { echo "red head moved"; exit 3; }
CTR_DIR=$S step inputs bash $L/scripts/ctr.sh red-inputs localhost/px75-ubuntu:2 0 bash -c "git log --oneline -1 && tests/mpx6-install --only inputs --work $W --inputs $I --tier native --firmware bios"
for u in planner executor; do
  CTR_DIR=$S step unit-$u bash $L/scripts/ctr.sh red-unit-$u localhost/px75-ubuntu:2 0 bash -c "tests/mpx6-install --only $u --work $L/w-red-units"
done
rows='export PAX_WOLF=$(tools/fetch-wolf) SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
D=tests/mpx6-install.d
for used in fat32 ext4 iso; do
  rm -rf '"$W"'/used-$used
  echo "== I-used-$used"
  if PAX_INSTALL_USED=$used python3 -I $D/install.py $PWD '"$I $W"'/used-$used no vdb; then
    python3 -I $D/verify.py $PWD '"$W"'/used-$used no vdb && python3 -I $D/gap.py '"$W"'/used-$used '"$I"'/build/disktools/limine/limine && tools/used-disk check '"$W"'/used-$used/target.img I-used-signatures-$used
    echo "ROW I-used-$used rest exit=$?"
  else echo "ROW I-used-$used install exit=$?"; fi
done'
CTR_DIR=$S step used-rows bash $L/scripts/ctr.sh red-used-rows localhost/px78-ubuntu:1 0 bash -c "$rows"
hostbuild() {
  local w=$1
  exec 9>/home/mfwolffe/lanes/hasu-block-A.lock; until flock -n 9; do printf '%s hasu-block-A.lock held; waiting\n' "$(date -u +%FT%TZ)"; python3 -I -c 'import time; time.sleep(30)'; done
  exec 8>/home/mfwolffe/lanes/hasu-A.lock; until flock -n 8; do printf '%s hasu-A.lock held; waiting\n' "$(date -u +%FT%TZ)"; python3 -I -c 'import time; time.sleep(30)'; done
  printf '%s block A acquired (both names) metal build %s\n' "$(date -u +%FT%TZ)" "$w"
  ( cd $S && export PAX_CACHE=$L/cache PAX_BUILD=$L/pbuild-host TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2 PAX_METAL_MODE=build \
    && taskset -c 0-5 tests/mpx6-install --only metal --work $w --inputs $I )
  local rc=$?
  flock -u 8; exec 8>&-; flock -u 9; exec 9>&-
  printf '%s block A RELEASED (both names) metal build rc=%s\n' "$(date -u +%FT%TZ)" "$rc"
  return $rc
}
for leg in used-fat32:860:fat32 used-ext4:860:ext4 blank-870:870:; do
  n=${leg%%:*}; rest=${leg#*:}; shape=${rest%%:*}; used=${rest#*:}
  step metal-build-$n hostbuild $W/leg-$n
  CTR_DIR=$S CTR_ENV="-e PAX_METAL_MODE=run -e PAX_METAL_ACCEL=kvm -e PAX_METAL_TARGET=$shape -e PAX_METAL_USED=$used" \
    step metal-run-$n bash $L/scripts/ctr.sh red-metal-$n localhost/px78-ubuntu:1 1 bash -c "time tests/mpx6-install --only metal --work $W/leg-$n --inputs $I"
done
printf '%s CHAIN-RED DONE\n' "$(date -u +%FT%TZ)"
