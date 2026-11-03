#!/usr/bin/env bash
# px87: gauntlet4's two red steps again at HEAD, run by hostchain.sh (one hold of kasumi-cores-0-3.lock):
#   usb-stick      the whole of tests/usb-stick as gauntlet4 ran it, with kmod (depmod, for tools/fetch-usb-linux's
#                  Linux, U8) installed in the throwaway container after its apt lists are refreshed, as CI's
#                  runner has it; the container image is not changed
#   mpx6-firmware  --tier native --firmware both with PAX_BUILD the short $L/m itself: gauntlet4's
#                  $L/h/mpx6-firmware put mpx6-nmi's mce-initramfs.report QMP socket at 108 bytes, past sun_path's
#                  107 and its NUL (pax#273's class); the longest sockets of mpx6-nmi and mpx6-triage printed first
# Every step runs and prints END.
#   rerun5.sh WORKTREE
set -uo pipefail
W=$1 E=$L/bin/engine-local.sh M=$L/m U=$L/mu
[ ! -e "$M" ] && [ ! -e "$U" ] || { echo "$M or $U exists: pick new directories"; exit 3; }
[ -z "$(git -C "$W" status --porcelain --untracked-files=no)" ] || { echo "the worktree is dirty"; exit 3; }
mkdir -p "$M" "$U"
printf '%s rerun5 at %s\n' "$(ts)" "$(git -C "$W" rev-parse HEAD)"
for fw in bios uefi; do
    for p in "$M/firmware/native/mpx6-nmi/native/$fw/mce-initramfs.report/qmp.sock" "$M/firmware/native/mpx6-triage/native/$fw/fault3-reset/qmp.sock"; do
        printf 'socket %s: %d bytes (sun_path holds 107 and a NUL)\n' "$p" "${#p}"
        [ "${#p}" -le 107 ] || { echo "too long"; exit 3; }
    done
done
reds=0
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; [ "$rc" = 0 ] || reds=$((reds + 1)); }
cat > "$U/run.sh" <<EOF
set -uo pipefail
cd $W
export PAX_CACHE=$L/cache PAX_BUILD=$U/b TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
printf 'commit %s\n' "\$(git rev-parse HEAD)"
apt-get update -q > $U/apt-update.log 2>&1 || echo "apt-get update failed: \$(tail -n 1 $U/apt-update.log)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends kmod > $U/apt-kmod.log 2>&1 || echo "apt-get install kmod failed: \$(tail -n 1 $U/apt-kmod.log)"
printf 'depmod: %s\n' "\$(command -v depmod || echo absent)"
if timeout --kill-after=10s 660 tools/fetch-usb-linux "$U/linux" > "$U/linux.json" 2> "$U/linux.err"; then
    export PAX_LINUX_KERNEL=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"])' "$U/linux.json")
    export PAX_LINUX_MODULES=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["modules"])' "$U/linux.json")
    echo "fetch-usb-linux: \$PAX_LINUX_KERNEL"
else
    echo "fetch-usb-linux failed (the environment; U8 cannot run): \$(tail -n 2 $U/linux.err)"
fi
rc=0
tests/usb-stick || rc=\$?
for f in $U/b/usb-stick/native-iso.log $U/b/usb-stick/native-usb.log; do
    [ -f "\$f" ] || continue
    echo "== \$f: \$(grep -ac 'PASS T[1-7] ' "\$f") PASS T rows, \$(grep -ac 'FAIL ' "\$f") FAIL"
done
exit \$rc
EOF
CTR_ROOT=1 CTR_CAPS=1 step usb-stick ctr bash "$U/run.sh"
step mpx6-firmware ctr bash "$L/bin/run.sh" "$W" "$M" mpx6-firmware tests/mpx6-firmware --tier native --firmware both
printf '%s rerun5: %d red\n' "$(ts)" "$reds"
[ "$reds" = 0 ]
