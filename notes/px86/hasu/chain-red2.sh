#!/usr/bin/env bash
# px86: the used rows red at the second tests-only head (50aa4b15: the token from --dry-run), 8495bdc0's
# installer (the red run's inputs: user/install unchanged between 59e7eb1b and 50aa4b15). Expected red by name:
# I-used-fat32 and I-used-ext4 at Limine's refusal; I-used-iso past the install, at gap.py or the signatures.
set -u
L=/home/mfwolffe/lanes/px86
S=$L/red W=$L/w-red I=$L/w-red/inputs
printf '%s\n' "$$" > $L/chain-red2.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
ts() { date -u +%FT%TZ; }
git -C $S fetch -q origin && git -C $S checkout -q 50aa4b15 || exit 3
[ -z "$(git -C $S diff --stat 59e7eb1b 50aa4b15 -- user/)" ] || { echo "user/ moved"; exit 3; }
rows='export PAX_WOLF=$(tools/fetch-wolf) SOURCE_DATE_EPOCH=1700000000 PAX_INSTALL_TIER=native
git log --oneline -1
D=tests/mpx6-install.d
for used in fat32 ext4 iso; do
  rm -rf '"$W"'/used2-$used
  echo "== I-used-$used"
  if PAX_INSTALL_USED=$used python3 -I $D/install.py $PWD '"$I $W"'/used2-$used no vdb; then
    python3 -I $D/verify.py $PWD '"$W"'/used2-$used no vdb && python3 -I $D/gap.py '"$W"'/used2-$used '"$I"'/build/disktools/limine/limine && tools/used-disk check '"$W"'/used2-$used/target.img I-used-signatures-$used
    echo "ROW I-used-$used rest exit=$?"
  else echo "ROW I-used-$used install exit=$?"; fi
  tools/used-disk check '"$W"'/used2-$used/target.img I-used-signatures-$used-at-base || true
done'
printf '%s START used-rows\n' "$(ts)"
CTR_DIR=$S bash $L/scripts/ctr.sh red2-used-rows localhost/px78-ubuntu:1 0 bash -c "$rows"
printf '%s STEP used-rows exit=%s\n' "$(ts)" "$?"
printf '%s CHAIN-RED2 DONE\n' "$(ts)"
