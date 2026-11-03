#!/usr/bin/env bash
# px87: the steps px88's fork and getrusage (trunk 9e106768) can touch, at the rebased head, for planning's
# tools/gauntlet-record.sh: each step `START name` ... `END name exit=N secs=S` (gauntlet_step), its output
# indented two spaces (so a suite's own `SKIP`/`END` words are never read as the record's), nothing printed
# outside a step, the first nonzero step stopping the run. Run from a clean clone at the head (record6.sh).
#   ci-plan       python3 -I tests/ci-plan (the planner with px88's mpx5-forks rules and this lane's map line)
#   mpx3-console  --tier both --firmware both, T1-T7 (the console rows), the Linux side with CAP_SYS_ADMIN
#   mpx3-screen   --tier both --firmware both, V0-V7
#   usb-stick     the whole suite (U5's console sessions from the stick, U7, U8's Linux), the disk tools through
#                 engine-local.sh, kmod in the throwaway container, fetch-usb-linux's JSON from its last line
#   mpx5-forks    px88's sessions with this lane's kernel lines: the build in the container (musl-tools in the
#                 throwaway container, as CI's apt step), the Linux side on the host (tools/linux-tree needs a
#                 --privileged engine: kasumi's rootless podman), the boots and comparisons in the container
#   mpx6-install  --rows smoke --tier native --firmware bios (px88's I-peak and this lane's as-user rows)
set -uo pipefail
. "$L/bin/gauntlet-record.sh"
S=$PWD B=${PX87_STEPS_BUILD:-$L/r6} E=$L/bin/engine-local.sh
ind() { "$@" 2>&1 | sed -u 's/^/  /'; return "${PIPESTATUS[0]}"; }
inc() { local n=$1; shift; ctr bash "$L/bin/run.sh" "$S" "$B/$n" "$n" "$@"; }
mkdir -p "$B/usb-stick" "$B/mpx5-forks"
cat > "$B/usb-stick/run.sh" <<EOF
set -uo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$B/usb-stick/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
printf 'commit %s\n' "\$(git rev-parse HEAD)"
apt-get update -q > $B/usb-stick/apt-update.log 2>&1 || echo "apt-get update failed: \$(tail -n 1 $B/usb-stick/apt-update.log)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends kmod > $B/usb-stick/apt-kmod.log 2>&1 || echo "apt-get install kmod failed"
timeout --kill-after=10s 660 tools/fetch-usb-linux "$B/usb-stick/linux" > "$B/usb-stick/linux.out" 2> "$B/usb-stick/linux.err" || { echo "fetch-usb-linux failed: \$(tail -n 2 $B/usb-stick/linux.err)"; exit 2; }
tail -n 1 "$B/usb-stick/linux.out" > "$B/usb-stick/linux.json"
export PAX_LINUX_KERNEL=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"])' "$B/usb-stick/linux.json")
export PAX_LINUX_MODULES=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["modules"])' "$B/usb-stick/linux.json")
[ -r "\$PAX_LINUX_KERNEL" ] && [ -d "\$PAX_LINUX_MODULES" ] || { echo "no fetched Linux to hand to U8"; exit 2; }
echo "fetch-usb-linux: \$PAX_LINUX_KERNEL"
rc=0
tests/usb-stick || rc=\$?
for f in $B/usb-stick/b/usb-stick/native-iso.log $B/usb-stick/b/usb-stick/native-usb.log; do
    [ -f "\$f" ] && echo "== \$f: \$(grep -ac 'PASS T[1-7] ' "\$f") PASS T rows, \$(grep -ac 'FAIL ' "\$f") FAIL"
done
exit \$rc
EOF
cat > "$B/mpx5-forks/build.sh" <<EOF
set -uo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$B/mpx5-forks/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
apt-get update -q > $B/mpx5-forks/apt-update.log 2>&1 || echo "apt-get update failed"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends musl-tools > $B/mpx5-forks/apt-musl.log 2>&1 || { echo "apt-get install musl-tools failed: \$(tail -n 1 $B/mpx5-forks/apt-musl.log)"; exit 2; }
printf 'commit %s; musl-gcc %s\n' "\$(git rev-parse HEAD)" "\$(command -v musl-gcc)"
tests/mpx5-forks --only build
EOF
cat > "$B/mpx5-forks/boot.sh" <<EOF
set -uo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$B/mpx5-forks/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
tests/mpx5-forks --images $B/mpx5-forks/b/mpx5-forks
EOF
forks() {
    CTR_ROOT=1 ctr bash "$B/mpx5-forks/build.sh" || return $?
    ( cd "$S" && PAX_ENGINE=podman PAX_CACHE=$L/cache PAX_BUILD=$B/mpx5-forks/b TMPDIR=$L/tmp tests/mpx5-forks --only linux --images "$B/mpx5-forks/b/mpx5-forks" ) || return $?
    ctr bash "$B/mpx5-forks/boot.sh"
}
gauntlet_step ci-plan ind inc ci-plan python3 -I tests/ci-plan || exit $?
CTR_ROOT=1 CTR_CAPS=1 gauntlet_step mpx3-console ind inc mpx3-console tests/mpx3-console --tier both --firmware both || exit $?
gauntlet_step mpx3-screen ind inc mpx3-screen tests/mpx3-screen --tier both --firmware both || exit $?
CTR_ROOT=1 CTR_CAPS=1 gauntlet_step usb-stick ind ctr bash "$B/usb-stick/run.sh" || exit $?
gauntlet_step mpx5-forks ind forks || exit $?
gauntlet_step mpx6-install ind inc mpx6-install tests/mpx6-install --rows smoke --tier native --firmware bios --work "$B/mpx6-install/work" || exit $?
