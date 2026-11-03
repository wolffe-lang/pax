#!/usr/bin/env bash
# px87: CI's two red steps of run 41530916165 (tier all at 088312b1) on kasumi, at a worktree's commit:
#   versions   the pinned e2fs and disktools images' programs (host podman) against the container's through
#              engine-local.sh: the same versions and sha256, or the probe stops
#   usb-stick  (container, PAX_ENGINE=engine-local.sh) tools/fetch-usb-linux, then tests/usb-stick as the
#              mpx3-console job runs it (its own --no-boot build; native), its U5 logs printed after
#   mpx6-part  (container, the same) tests/mpx6-part --tier native --firmware bios (P9 among its rows)
# Run by hostchain.sh (one hold of kasumi-cores-0-3.lock, CPUs 0-3). Each step prints END; a red step does
# not stop the next (both are wanted, red or green).
#   probe-ci.sh WORKTREE BUILD_DIR
set -uo pipefail
W=$1 B=$2
E=$L/bin/engine-local.sh
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; return "$rc"; }
[ ! -e "$B" ] || { echo "$B exists: pick a new directory"; exit 3; }
mkdir -p "$B"
printf '%s probe-ci at %s (%s dirty paths), build %s\n' "$(ts)" "$(git -C "$W" rev-parse HEAD)" "$(git -C "$W" status --porcelain --untracked-files=no | wc -l)" "$B"
cat > "$B/versions.sh" <<EOF
set -euo pipefail
cd $W
export PAX_CACHE=$L/cache
tools/e2fs --version | grep -E '^(e2fsprogs|mke2fs|e2fsck|debugfs):'
tools/disktools --version | grep -E '^(sfdisk|sgdisk|mkfs.fat|fsck.fat|mcopy|blkid):' | cut -d' ' -f1-2
EOF
versions() {
    bash "$B/versions.sh" > "$B/versions-pinned.txt" 2>&1 || { cat "$B/versions-pinned.txt"; return 1; }
    ctr env PAX_ENGINE="$E" bash "$B/versions.sh" > "$B/versions-container.txt" 2>&1 || { cat "$B/versions-container.txt"; return 1; }
    paste -d'|' "$B/versions-pinned.txt" "$B/versions-container.txt" | sed 's/|/   container: /'
    cmp -s "$B/versions-pinned.txt" "$B/versions-container.txt" && echo "the same programs, pinned and in the container"
}
step versions versions || { echo "PROBE STOPPED: the container's disk tools are not the pinned ones"; exit 1; }
cat > "$B/usb.sh" <<EOF
set -uo pipefail
cd $W
export PAX_CACHE=$L/cache PAX_BUILD=$B/u TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
if timeout --kill-after=10s 660 tools/fetch-usb-linux "$B/usb-linux" > "$B/usb-linux.json" 2> "$B/usb-linux.err"; then
    export PAX_LINUX_KERNEL=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["kernel"])' "$B/usb-linux.json")
    export PAX_LINUX_MODULES=\$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["modules"])' "$B/usb-linux.json")
else
    echo "fetch-usb-linux failed (U8 will say so; U1-U7 do not need it): \$(tail -n 2 "$B/usb-linux.err")"
fi
rc=0
tests/usb-stick || rc=\$?
for f in "$B"/u/usb-stick/native-iso.log "$B"/u/usb-stick/native-usb.log; do
    [ -f "\$f" ] || continue
    echo "== \$f"; grep -aE '(PASS|FAIL) T[67] |mpx3-console: (PASS|FAIL)\$' "\$f" | head -48
done
exit \$rc
EOF
CTR_ROOT=1 CTR_CAPS=1 step usb-stick ctr bash "$B/usb.sh"
cat > "$B/part.sh" <<EOF
set -uo pipefail
cd $W
export PAX_CACHE=$L/cache PAX_BUILD=$B/p TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0 PAX_ENGINE=$E
export PAX_WOLF=\$(tools/fetch-wolf)
tools/fetch-limine > /dev/null
tests/mpx6-part --tier native --firmware bios
EOF
step mpx6-part ctr bash "$B/part.sh"
