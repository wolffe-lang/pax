#!/usr/bin/env bash
# px92: the dev compiler at user/wolf.pin (v0.2.36) and its std, from source by tools/mkwolf and tools/mkwolf-std
# (px65's way for v0.2.35), in localhost/r41-toolchain:1 (rustup 1.97.1 with the musl target, the tag's own
# rust-toolchain.toml channel). Under the maintainer's exception: no locks, slot B's CPUs 4-7,12-15 (cargo -j 8),
# a 12 GiB cap, a sensor log beside the take.
#   wolf.sh CHECKOUT OUT
set -uo pipefail
L=/home/mfwolffe/lanes/px92 W=$1 O=$2
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
ts() { date -u +%FT%TZ; }
printf '%s\n' "$$" > "$L/wolf.pid"
[ -z "$(git -C "$W" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; exit 3; }
[ ! -e "$O" ] || { echo "$O exists"; exit 3; }
mkdir -p "$O" "$L/wbuild" "$L/tmp"
printf "%s px92 wolf: the maintainer's exception, no locks, slot B's CPUs (4-7,12-15), beside vc17; checkout %s\n" "$(ts)" "$(git -C "$W" rev-parse HEAD)"
( while kill -0 $$ 2>/dev/null; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E '^(Core [0-9]+):' | awk '{printf "%s%s %s; ", $1, $2, $3}'; echo; sleep 30; done ) > "$L/logs/sensors-wolf.log" 2>&1 &
cat > "$L/wolf-inside.sh" <<IN
#!/usr/bin/env bash
set -euo pipefail
export PATH=/opt/s263-rust/bin:/usr/local/bin:/usr/bin:/bin PAX_BUILD=$L/wbuild TMPDIR=$L/tmp PAX_WOLF_BUILD_JOBS=8
cd "$W"
grep -E '^WOLF_(SRC_TAG|SRC_REV|SRC_RUST|SRC_VERSION_LINE|STD_REV)=' user/wolf.pin
printf '%s START mkwolf\n' "\$(date -u +%FT%TZ)"
tools/mkwolf "$O/wolf"
printf '%s END mkwolf\n' "\$(date -u +%FT%TZ)"
tools/mkwolf-std "$O/wolf-std"
cat "$O/wolf-std/STD-REV"
for n in 1 2; do sha256sum "$O/wolf/wolf" "$O/wolf/wolf-cimport-worker" "$O/wolf/libwolf_rt.a"; done
IN
step() { local n=$1; shift; printf "%s START %s\n" "$(ts)" "$n"; "$@"; local rc=$?; printf "%s END %s exit=%s\n" "$(ts)" "$n" "$rc"; return $rc; }
build() {
  "$P" run --rm --name px92-mkwolf --memory 12g --pids-limit 16384 -v "$L:$L" -w "$W" \
    -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    localhost/r41-toolchain:1 /usr/bin/taskset.real -c 4-7,12-15 bash "$L/wolf-inside.sh"
}
step mkwolf build
rc=$?
printf '%s WOLF DONE exit=%s\n' "$(ts)" "$rc"
exit $rc
