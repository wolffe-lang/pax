#!/usr/bin/env bash
# px87: tests/usb-stick alone again at a worktree's commit (rerun5's usb-stick step), run by hostchain.sh:
# kmod in the throwaway container, and tools/fetch-usb-linux's JSON read from its LAST line. rerun5 and
# gauntlet4 parsed the whole of fetch-usb-linux's stdout as JSON (its progress lines come first), so
# PAX_LINUX_KERNEL was empty and U8's tools/linux-part looked for the container host's own kernel
# (`linux-part: cannot read the kernel /usr/lib/modules/7.3.0-4-cachyos/vmlinuz`): the lane's rig, not PAX.
#   usb6.sh WORKTREE
set -uo pipefail
W=$1 E=$L/bin/engine-local.sh U=$L/mu6
[ ! -e "$U" ] || { echo "$U exists: pick a new directory"; exit 3; }
[ -z "$(git -C "$W" status --porcelain --untracked-files=no)" ] || { echo "the worktree is dirty"; exit 3; }
mkdir -p "$U"
printf '%s usb6 at %s\n' "$(ts)" "$(git -C "$W" rev-parse HEAD)"
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
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
    tail -n 1 "$U/linux.json" > "$U/linux.last.json"
    export PAX_LINUX_KERNEL=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"])' "$U/linux.last.json")
    export PAX_LINUX_MODULES=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["modules"])' "$U/linux.last.json")
    [ -r "\$PAX_LINUX_KERNEL" ] && [ -d "\$PAX_LINUX_MODULES" ] || { echo "no fetched Linux to hand to U8"; exit 2; }
    echo "fetch-usb-linux: \$PAX_LINUX_KERNEL"
else
    echo "fetch-usb-linux failed (the environment; U8 cannot run): \$(tail -n 2 $U/linux.err)"
fi
rc=0
tests/usb-stick || rc=\$?
grep -aE "PASS U8|FAIL U8|linux-part:" $U/b/usb-stick/linux-native.log 2>/dev/null | head -5
for f in $U/b/usb-stick/native-iso.log $U/b/usb-stick/native-usb.log; do
    [ -f "\$f" ] || continue
    echo "== \$f: \$(grep -ac 'PASS T[1-7] ' "\$f") PASS T rows, \$(grep -ac 'FAIL ' "\$f") FAIL"
done
exit \$rc
EOF
CTR_ROOT=1 CTR_CAPS=1 step usb-stick ctr bash "$U/run.sh"
