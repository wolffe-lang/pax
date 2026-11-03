#!/usr/bin/env bash
# px87: the mpx3 and mpx6 legs at HEAD after CI's tier-all red at 088312b1, run by hostchain.sh (one hold of
# kasumi-cores-0-3.lock, CPUs 0-3): a fresh clone of GitHub's pax at HEAD ($L/h4/s), fresh build directories
# under the short $L/h (the triage's QMP sockets well inside sun_path's 107 bytes; the longest printed first).
# Every step runs and prints `END <step> exit=N` (a red step does not stop the next); the last line counts them.
#   1 ci-plan, ci-budgets, pax-release   the planner's proofs, the budgets, the release record
#   2 mpx3-screen   --tier both --firmware both (V0-V7)
#   3 mpx3-console  --tier both --firmware both, the Linux side with CAP_SYS_ADMIN in the user namespace
#   4 usb-stick     the whole of tests/usb-stick as CI's mpx3-console job runs it (U1-U8; U5's console suite
#                   from the stick, T6 and T7 among it), the disk tools through engine-local.sh, the container's
#                   apt lists refreshed first (as CI's runner does) for tools/fetch-usb-linux's Linux (U8)
#   5 mpx6-install  --rows smoke --tier native --firmware bios
#   6 mpx6-part     the whole suite as CI runs it (both tiers, both firmwares; P9 among it), the disk tools
#                   through engine-local.sh
#   7 mpx6-firmware --tier native --firmware both
#   gauntlet4.sh HEAD
set -uo pipefail
HEAD=$1
S=$L/h4/s B=$L/h E=$L/bin/engine-local.sh
[ ! -e "$L/h4" ] && [ ! -e "$B" ] || { echo "$L/h4 or $B exists: pick new directories"; exit 3; }
reds=0 steps=0
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; steps=$((steps + 1)); [ "$rc" = 0 ] || reds=$((reds + 1)); }
mkdir -p "$L/h4" "$B"
git clone -q https://github.com/wolffe-lang/pax.git "$S" && git -C "$S" checkout -q -b gauntlet4 "$HEAD" || exit 3
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || exit 3
printf '%s gauntlet4 at %s\n' "$(ts)" "$HEAD"
for fw in bios uefi; do
    p=$B/mpx6-firmware/firmware/native/mpx6-triage/native/$fw/fault3-reset/qmp.sock
    printf 'the longest triage socket %s: %d bytes (sun_path holds 107 and a NUL)\n' "$p" "${#p}"
    [ "${#p}" -le 107 ] || { echo "too long"; exit 3; }
done
inc() { local n=$1; shift; ctr bash "$L/bin/run.sh" "$S" "$B/$n" "$n" "$@"; }
step ci-plan inc ci-plan python3 -I tests/ci-plan
step ci-budgets inc ci-budgets python3 -I tests/ci-budgets.py
step pax-release inc pax-release python3 -I tests/pax-release
step mpx3-screen inc mpx3-screen tests/mpx3-screen --tier both --firmware both
CTR_ROOT=1 CTR_CAPS=1 step mpx3-console inc mpx3-console tests/mpx3-console --tier both --firmware both
mkdir -p "$B/usb-stick"
cat > "$B/usb-stick/run.sh" <<EOF
set -uo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$B/usb-stick/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
printf 'commit %s\n' "\$(git rev-parse HEAD)"
apt-get update -q > $B/usb-stick/apt-update.log 2>&1 || echo "apt-get update failed: \$(tail -n 1 $B/usb-stick/apt-update.log)"
if timeout --kill-after=10s 660 tools/fetch-usb-linux "$B/usb-stick/linux" > "$B/usb-stick/linux.json" 2> "$B/usb-stick/linux.err"; then
    export PAX_LINUX_KERNEL=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"])' "$B/usb-stick/linux.json")
    export PAX_LINUX_MODULES=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["modules"])' "$B/usb-stick/linux.json")
    echo "fetch-usb-linux: \$PAX_LINUX_KERNEL"
else
    echo "fetch-usb-linux failed (the environment; U8 cannot run): \$(tail -n 2 $B/usb-stick/linux.err)"
fi
rc=0
tests/usb-stick || rc=\$?
for f in $B/usb-stick/b/usb-stick/native-iso.log $B/usb-stick/b/usb-stick/native-usb.log; do
    [ -f "\$f" ] || continue
    echo "== \$f: \$(grep -ac 'PASS T[1-7] ' "\$f") PASS T rows, \$(grep -ac 'FAIL ' "\$f") FAIL"
    grep -aE '(PASS|FAIL) T[67] (native|release) (bios|uefi) ask-serial|FAIL |mpx3-console: (PASS|FAIL)\$' "\$f" | head -12
done
exit \$rc
EOF
CTR_ROOT=1 CTR_CAPS=1 step usb-stick ctr bash "$B/usb-stick/run.sh"
step mpx6-install inc mpx6-install tests/mpx6-install --rows smoke --tier native --firmware bios --work "$B/mpx6-install/work"
mkdir -p "$B/mpx6-part"
cat > "$B/mpx6-part/run.sh" <<EOF
set -uo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$B/mpx6-part/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
printf 'commit %s\n' "\$(git rev-parse HEAD)"
tests/mpx6-part
EOF
step mpx6-part ctr bash "$B/mpx6-part/run.sh"
step mpx6-firmware inc mpx6-firmware tests/mpx6-firmware --tier native --firmware both
printf '%s gauntlet4 at %s: %d steps, %d red\n' "$(ts)" "$HEAD" "$steps" "$reds"
[ "$reds" = 0 ]
