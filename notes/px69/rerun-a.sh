#!/usr/bin/env bash
# px69 after the rebase onto px79's merge (8d631040), kasumi only, CPUs
# 0-3: the planner's self-test, mpx6-disktools built for both tiers in
# the lane's Ubuntu image, the Linux differentials against both oracle
# sets (tools/disktools' pinned packages, as CI; the image's own tools,
# the versions in oracles.versions), then the PAX leg on both tiers and
# both firmwares. The cores' lock is taken per step and released between
# (shared with px80 and wl68). Launched with setsid -f; pid, log and exit
# marker under ~/lanes/px69/rerun.
set -euo pipefail
L=$HOME/lanes/px69 R=$HOME/lanes/px69/r J=$HOME/lanes/px69/rerun
W=$J/dt
LOCK=$HOME/lanes/kasumi-cores-0-3.lock
mkdir -p "$J/logs" "$W" "$L/tmp"
printf '%s\n' "$$" > "$J/a.pid"
trap 'rc=$?; printf "%s\n" "$rc" > "$J/a.exit"; printf "job a exit=%s %s\n" "$rc" "$(date -Is)"' EXIT
ulimit -c 0
export PAX_CACHE=$L/cache TMPDIR=$L/tmp PAX_BUILD=$J/build PAX_ENGINE=podman
export PAX_LOPE_REPO=$L/lope PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0
printf 'job a at %s, %s\n' "$(git -C "$R" rev-parse --short=8 HEAD)" "$(date -Is)"
[ -z "$(git -C "$R" status --porcelain)" ]
cap() { [ "$(du -sk "$L" | cut -f1)" -lt 10485760 ] || { echo "lane over 10 GB"; return 3; }; }
cap
step() {
    local name=$1 rc=0; shift
    printf '%s start %s\n' "$name" "$(date -Is)"
    # the lock on fd 9 of this shell only: closed for the step's children,
    # so nothing they leave behind can keep the cores
    exec 9> "$LOCK"; flock 9
    "$@" 9>&- > "$J/logs/$name.log" 2>&1 || rc=$?
    flock -u 9; exec 9>&-
    if [ "$rc" != 0 ]; then
        tail -n 40 "$J/logs/$name.log"
        printf '%s FAIL exit=%s %s\n' "$name" "$rc" "$(date -Is)"
        return "$rc"
    fi
    printf '%s PASS %s\n' "$name" "$(date -Is)"
    cap
}
box() {
    podman run --rm --cpuset-cpus 0-3 --memory 8g --ulimit core=0:0 -v "$L:$L:Z" \
        -e PAX_CACHE -e TMPDIR -e PAX_BUILD -e PAX_LOPE_REPO -e CARGO_INCREMENTAL \
        -e SOURCE_DATE_EPOCH=1700000000 -e TZ=UTC -w "$R" localhost/px69-ubuntu "$@"
}
step ci-plan taskset -c 0-3 "$R/tests/ci-plan"
step build box bash -c 'set -euo pipefail; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
    "$PAX_WOLF" --version; tests/mpx6-disktools --only build --work "$1" --tier both' px69 "$W"
( cd "$W" && sha256sum bin/paxgpt bin/paxfat bin/paxext2 limine/limine native/*.elf release/*.elf 2>/dev/null ) > "$J/dt-binaries.sha256" || true
step linux-ci taskset -c 0-3 "$R/tests/mpx6-disktools" --only linux --work "$W"
mkdir -p "$J/host"
step host-gpt box python3 -I "$R/tests/mpx6-disktools.d/gpt.py" "$W/bin/paxgpt" "$J/host/gpt"
step host-fat box python3 -I "$R/tests/mpx6-disktools.d/fat.py" "$W/bin/paxfat" "$J/host/fat"
printf '#!/bin/bash\nexec podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "%s:%s:Z" -e SOURCE_DATE_EPOCH -e TZ=UTC localhost/px69-ubuntu "$@"\n' "$L" "$L" > "$J/container-exec"
chmod +x "$J/container-exec"
step host-ext2 env PAX_E2FS_IMAGE=localhost/px69-ubuntu taskset -c 0-3 python3 -I "$R/tests/mpx6-disktools.d/ext2.py" "$W/bin/paxext2" "$J/host/ext2" "$J/container-exec"
step pax taskset -c 0-3 "$R/tests/mpx6-disktools" --only pax --work "$W" --tier both --firmware both
du -sh "$L" "$J"
printf 'job a complete %s\n' "$(date -Is)"
