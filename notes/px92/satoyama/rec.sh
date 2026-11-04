#!/usr/bin/env bash
# px92: the dev compiler's PAX sessions again at user/wolf.pin's v0.2.36, for tests/mpx5-wolf.d/test_rows.py's fixtures
# (px65's notes/px65/wolf-pax-{root,user}.tty are v0.2.35's). tests/mpx5-wolf itself, unmodified, PAX side only:
#   1 as         tools/mkas (gcc, px75-ubuntu:2): PAX_DEV_BASE's /bin/as (pelt and cat/env: px86's verified inputs)
#   2 wolf       tools/mkwolf and mkwolf-std at the pin (r41-toolchain:1): PAX_DEV_WOLF_DIR and PAX_DEV_STD_DIR
#   3 w0         tests/mpx5-wolf --only build --firmware bios --tier native (px75-ubuntu:2): W0, the root, the image
#   4 boot       tests/mpx5-wolf --images <W0's work> --firmware bios --tier native: the boot under TCG as the suite
#                types it, both sessions, W2 (rows.py) on each; W1 fails by design (no Linux side here)
#   5 fixtures   the two sessions as the suite compares them (.session.cmp), and rows.py on them again
# One take of both satoyama locks (A, then B), slot A's CPUs 0-3,8-11.
#   rec.sh CHECKOUT
set -uo pipefail
L=/home/mfwolffe/lanes/px92 C=$1 R=/home/mfwolffe/lanes/px92/rec-run B=/home/mfwolffe/lanes/px92/base CPUS=0-3,8-11
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
export TMPDIR=$L/tmp
printf '%s\n' "$$" > "$L/rec.pid"
ts() { date -u +%FT%TZ; }
[ ! -e "$R" ] || { echo "$R exists"; exit 3; }
[ -z "$(git -C "$C" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; exit 3; }
mkdir -p "$R"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return $rc; }
ctr() {  # NAME IMAGE CMD...
  local name=$1 img=$2; shift 2
  local tsb=taskset; [ "$img" = localhost/r41-toolchain:1 ] && tsb=/usr/bin/taskset.real
  "$P" run --rm --name "px92-$name" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    -v "$L:$L" -w "$C" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$R/pb ${CTR_ENV:-} "$img" $tsb -c "$CPUS" "$@"
}
DEV="-e PAX_DEV_BASE=$B -e PAX_DEV_WOLF_DIR=$R/wolf -e PAX_DEV_STD_DIR=$R/std -e PAX_TASKSET_CPUS=$CPUS"

exec 8>/home/mfwolffe/lanes/satoyama-A.lock
printf '%s px92 rec: waiting on satoyama-A.lock (one flock -w 21600), then B\n' "$(ts)"
flock -w 21600 8 || { echo "$(ts) the A lock wait timed out"; exit 4; }
exec 9>/home/mfwolffe/lanes/satoyama-B.lock
printf '%s px92 rec: satoyama-A.lock acquired; waiting on satoyama-B.lock\n' "$(ts)"
flock -w 21600 9 || { echo "$(ts) the B lock wait timed out"; exit 4; }
printf '%s px92 rec: both satoyama locks acquired (CPUs %s); checkout %s\n' "$(ts)" "$CPUS" "$(git -C "$C" rev-parse HEAD)"
taskset -cp "$CPUS" $$ > /dev/null
( while kill -0 $$ 2>/dev/null; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E '^(Core [0-9]+):' | awk '{printf "%s%s %s; ", $1, $2, $3}'; echo; sleep 30; done ) > "$L/logs/sensors-rec.log" 2>&1 &

rec() {
  step as ctr rec-as localhost/px75-ubuntu:2 bash -c "tools/mkas $B/bin && ls -la $B/bin/as" || return 1
  CTR_ENV="-e PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin -e PAX_WOLF_BUILD_JOBS=8" step wolf ctr rec-wolf localhost/r41-toolchain:1 \
    bash -c "set -e; PAX_BUILD=$R/wb tools/mkwolf $R/wolf; PAX_BUILD=$R/wb tools/mkwolf-std $R/std; cmp $R/wolf/sums.txt user/wolf.sums && echo 'PASS the build reproduces user/wolf.sums'" || return 1
  CTR_ENV="$DEV" step w0 ctr rec-w0 localhost/px75-ubuntu:2 bash -c "tests/mpx5-wolf --only build --firmware bios --tier native" || return 1
  CTR_ENV="$DEV" step boot ctr rec-boot localhost/px75-ubuntu:2 bash -c "tests/mpx5-wolf --images $R/pb/mpx5-wolf --firmware bios --tier native; echo \"mpx5-wolf exit \$? (W1 is red by design here: no Linux side)\""
  mkdir -p "$R/fixtures"
  cp "$R/pb/mpx5-wolf-native-bios-root.session.cmp" "$R/fixtures/wolf-pax-root.tty" || return 1
  cp "$R/pb/mpx5-wolf-native-bios-pax.session.cmp" "$R/fixtures/wolf-pax-user.tty" || return 1
  step fixtures ctr rec-rows localhost/px75-ubuntu:2 bash -c "python3 -I tests/mpx5-wolf.d/rows.py $R/fixtures/wolf-pax-root.tty root && python3 -I tests/mpx5-wolf.d/rows.py $R/fixtures/wolf-pax-user.tty pax && wc -l $R/fixtures/*.tty && sha256sum $R/fixtures/*.tty"
}
rec; rc=$?
flock -u 9; exec 9>&-; flock -u 8; exec 8>&-
printf '%s px92 rec: both satoyama locks RELEASED; REC DONE exit=%s\n' "$(ts)" "$rc"
exit $rc
