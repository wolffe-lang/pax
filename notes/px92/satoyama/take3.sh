#!/usr/bin/env bash
# px92: one take of both satoyama locks (A outside, then B; slot A's CPUs 0-3,8-11), never idle:
#   gauntlet  at HEAD in a fresh clone from GitHub, fresh directories; stops at the first nonzero step and prints
#             every step's END line:
#               ci-plan, ci-budgets            tests/ci-plan, tests/ci-budgets.py
#               mkwolf                         tools/mkwolf and mkwolf-std at the pin (the compiler's second build),
#                                              its sums.txt equal to user/wolf.sums
#               release-pair                   tools/mkdistribution with px86's inputs plus that compiler and std
#                                              (tests/distribution I0 on both variants inside it)
#               distribution-boot              tests/distribution-boot, I2 on both ISOs and firmwares under KVM
#   plant     PLANT (HEAD plus v0.2.35's pin and sums) the same way: mkwolf, release-pair, distribution-boot,
#             expected red by name at I2's guest-dev-args
#   facts     the dev image's 0.2.36 toolchain on Linux (README's three facts), and the bytes behind d2cmp's
#             differences between the 9c88ec8a and 8b4e98ae dev archives
#   take3.sh HEAD PLANT
set -uo pipefail
L=/home/mfwolffe/lanes/px92 HEAD=$1 PLANT=$2 T=/home/mfwolffe/lanes/px92/t3 CPUS=0-3,8-11
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
export PATH=/home/mfwolffe/lanes/satoyama-env/bin:$PATH TMPDIR=$L/tmp
printf '%s\n' "$$" > "$L/take3.pid"
ts() { date -u +%FT%TZ; }
[ ! -e "$T" ] || { echo "$T exists"; exit 3; }
mkdir -p "$T"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return $rc; }
ctr() {  # NAME IMAGE KVM DIR CMD...
  local name=$1 img=$2 kvm=$3 dir=$4; shift 4
  local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  local ts_bin=taskset; [ "$img" = localhost/r41-toolchain:1 ] && ts_bin=/usr/bin/taskset.real
  "$P" run --rm --name "px92-$name" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$dir" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp ${CTR_ENV:-} "$img" $ts_bin -c "$CPUS" "$@"
}
# One whole build and boot of a checkout: CK at REV, WORK its directory.
compiler() { CTR_ENV="-e PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin -e PAX_BUILD=$2/wb -e PAX_WOLF_BUILD_JOBS=8" \
  ctr "mkwolf-$3" localhost/r41-toolchain:1 0 "$1" bash -c "set -e; tools/mkwolf $2/winputs/wolf; tools/mkwolf-std $2/winputs/wolf-std; cat $2/winputs/wolf-std/STD-REV; cmp $2/winputs/wolf/sums.txt user/wolf.sums && echo 'PASS the build reproduces user/wolf.sums'"; }
pair() {
  cp -al "$L/build/inputs" "$2/inputs" && cp -a "$2/winputs/wolf" "$2/inputs/wolf" && cp -a "$2/winputs/wolf-std" "$2/inputs/wolf-std" || return 2
  CTR_ENV="-e PAX_BUILD=$2/sb -e PAX_LOPE_REPO=$L/inputs/lope-local -e CARGO_INCREMENTAL=0" \
  ctr "pair-$3" localhost/px75-ubuntu:2 0 "$1" bash -c "set -e; export PAX_WOLF=\$(tools/fetch-wolf); tools/mkdistribution $L/inputs/base-dev.cpio $2/inputs $2/sout > $2/distribution.log 2>&1; grep -E '^(I0|I1)' $2/distribution.log"
}
boot() {
  CTR_ENV="-e PAX_BUILD=$2/ib" ctr "i2-$3" localhost/px75-ubuntu:2 1 "$1" bash -c "tests/distribution-boot $2/sout"
}

exec 8>/home/mfwolffe/lanes/satoyama-A.lock
printf '%s px92 take3: waiting on satoyama-A.lock (one flock -w 21600), then B\n' "$(ts)"
flock -w 21600 8 || { echo "$(ts) the A lock wait timed out"; exit 4; }
exec 9>/home/mfwolffe/lanes/satoyama-B.lock
printf '%s px92 take3: satoyama-A.lock acquired; waiting on satoyama-B.lock\n' "$(ts)"
flock -w 21600 9 || { echo "$(ts) the B lock wait timed out"; exit 4; }
printf '%s px92 take3: both satoyama locks acquired (CPUs %s)\n' "$(ts)" "$CPUS"
taskset -cp "$CPUS" $$ > /dev/null   # slot A's CPUs for the host steps and their children
( while kill -0 $$ 2>/dev/null; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E '^(Core [0-9]+):' | awk '{printf "%s%s %s; ", $1, $2, $3}'; echo; sleep 30; done ) > "$L/logs/sensors-take3.log" 2>&1 &

# --- the gauntlet -------------------------------------------------------------------------------------------
G=$T/g
git clone -q https://github.com/wolffe-lang/pax "$G/pax" && git -C "$G/pax" checkout -q --detach "$HEAD" || { echo "GAUNTLET: no clone at $HEAD"; exit 3; }
[ "$(git -C "$G/pax" rev-parse HEAD)" = "$HEAD" ] || exit 3
printf '%s GAUNTLET at %s (a fresh clone of GitHub)\n' "$(ts)" "$HEAD"
gauntlet() {
  step ci-plan ctr ci-plan localhost/px75-ubuntu:2 0 "$G/pax" python3 -I tests/ci-plan || return 1
  step ci-budgets ctr ci-budgets localhost/px75-ubuntu:2 0 "$G/pax" python3 -I tests/ci-budgets.py || return 1
  step mkwolf compiler "$G/pax" "$G" g || return 1
  step release-pair pair "$G/pax" "$G" g || return 1
  step distribution-boot boot "$G/pax" "$G" g || return 1
}
gauntlet; grc=$?
printf '%s GAUNTLET %s at %s (exit %s)\n' "$(ts)" "$([ $grc = 0 ] && echo GREEN || echo RED)" "$HEAD" "$grc"

# --- the plant (red by name expected) ------------------------------------------------------------------------
Q=$T/plant
git clone -q "$G/pax" "$Q/pax" && git -C "$Q/pax" fetch -q https://github.com/wolffe-lang/pax "px92-plant-wolf035" && git -C "$Q/pax" checkout -q --detach "$PLANT"
[ "$(git -C "$Q/pax" rev-parse HEAD)" = "$PLANT" ] || { echo "PLANT: no checkout at $PLANT"; exit 3; }
printf '%s PLANT at %s\n' "$(ts)" "$PLANT"
step plant-mkwolf compiler "$Q/pax" "$Q" p
step plant-release-pair pair "$Q/pax" "$Q" p
step plant-distribution-boot boot "$Q/pax" "$Q" p
grep -h -E "guest-dev-args|I2 PASS" "$Q"/sout/*.halt.log "$L/logs/take3.log" 2>/dev/null | tail -3

# --- facts for the note -----------------------------------------------------------------------------------
facts() {
  python3 -I "$L/lane/notes/px92/satoyama/facts.py" "$G/pax" "$L/sdev/dev-live.cpio" "$L/sdev2/dev-live.cpio" "$G/sout/dev.cpio" "$T/facts"
}
step facts facts
flock -u 9; exec 9>&-; flock -u 8; exec 8>&-
printf '%s px92 take3: both satoyama locks RELEASED\n' "$(ts)"
exit $grc
