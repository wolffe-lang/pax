#!/usr/bin/env bash
# px69 after the rebase onto px79's merge (8d631040), kasumi only, CPUs
# 0-3, the lock per step: mpx6-root's explicit ext2 leg with paxext2 as
# the writer (both tiers, both firmwares, every row), the unchanged ext3
# default as the control (native BIOS, every row), and px79's own
# mpx6-nodes on the same head (native BIOS, px79's run-suite.sh order:
# the build in the Ubuntu image, the Linux side live on this host, then
# the boots). Every Linux side is the live guest (no --record: the tree
# is not written). Launched with setsid -f after rerun-a.sh; pid, log and
# exit marker under ~/lanes/px69/rerun.
set -euo pipefail
L=$HOME/lanes/px69 R=$HOME/lanes/px69/r J=$HOME/lanes/px69/rerun
W=$J/dt
LOCK=$HOME/lanes/kasumi-cores-0-3.lock
mkdir -p "$J/logs" "$L/tmp"
printf '%s\n' "$$" > "$J/b.pid"
trap 'rc=$?; printf "%s\n" "$rc" > "$J/b.exit"; printf "job b exit=%s %s\n" "$rc" "$(date -Is)"' EXIT
ulimit -c 0
export PAX_CACHE=$L/cache TMPDIR=$L/tmp PAX_ENGINE=podman PAX_REQUIRE_UEFI=1 CARGO_INCREMENTAL=0
export PAX_LINUX_KERNEL=/usr/lib/modules/7.3.0-4-cachyos/vmlinuz
[ -r "$PAX_LINUX_KERNEL" ]
[ -x "$W/bin/paxext2" ]
printf 'job b at %s, %s\n' "$(git -C "$R" rev-parse --short=8 HEAD)" "$(date -Is)"
[ -z "$(git -C "$R" status --porcelain)" ]
cap() { [ "$(du -sk "$L" | cut -f1)" -lt 10485760 ] || { echo "lane over 10 GB"; return 3; }; }
cap
step() {
    local name=$1 rc=0; shift
    printf '%s start %s\n' "$name" "$(date -Is)"
    exec 9> "$LOCK"; flock 9
    "$@" 9>&- > "$J/logs/$name.log" 2>&1 || rc=$?
    flock -u 9; exec 9>&-
    if [ "$rc" != 0 ]; then
        tail -n 60 "$J/logs/$name.log"
        printf '%s FAIL exit=%s %s\n' "$name" "$rc" "$(date -Is)"
        return "$rc"
    fi
    printf '%s PASS %s\n' "$name" "$(date -Is)"
    cap
}
box() { # IMAGE BUILD-DIR CMD...
    local img=$1 b=$2; shift 2
    podman run --rm --cpuset-cpus 0-3 --memory 8g --ulimit core=0:0 -v "$L:$L:Z" \
        -e PAX_CACHE -e TMPDIR -e PAX_BUILD="$b" -e CARGO_INCREMENTAL -w "$R" "$img" \
        bash -c 'set -euo pipefail; export PAX_WOLF=$(tools/fetch-wolf | tail -1); "$@"' px69 "$@"
}
host() { taskset -c 0-3 "$@"; }
E2=$J/root-ext2 E3=$J/root-ext3 N=$J/nodes
rm -rf "$E2" "$E3" "$N"; mkdir -p "$E2" "$E3" "$N"
step root-ext2-build box localhost/px69-ubuntu "$E2" tests/mpx6-root --only build --fstype ext2 --tier both
step root-ext2-linux host env PAX_BUILD="$E2" "$R/tests/mpx6-root" --only linux --fstype ext2 --images "$E2/mpx6-root"
step root-ext2-boots host env PAX_BUILD="$E2" PAX_EXT2_WRITER="$W/bin/paxext2" "$R/tests/mpx6-root" --fstype ext2 --images "$E2/mpx6-root" --tier both --firmware both --rows all
rm -rf "$E2/mpx6-root"/*/disks; rm -f "$E2"/*.img
step root-ext3-build box localhost/px69-ubuntu "$E3" tests/mpx6-root --only build --tier native
step root-ext3-linux host env PAX_BUILD="$E3" "$R/tests/mpx6-root" --only linux --images "$E3/mpx6-root"
step root-ext3-boots host env PAX_BUILD="$E3" "$R/tests/mpx6-root" --images "$E3/mpx6-root" --tier native --firmware bios --rows all
rm -rf "$E3/mpx6-root"/*/disks; rm -f "$E3"/*.img
# px79's order (notes/px79/run-suite.sh): its build in the Ubuntu image
# (px79-ubuntu, used read-only), the Linux side here, then the boot; a
# disk the build container could not finish (all zeros at its head) is
# removed so the suite makes it on this host.
step nodes-build podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD="$N" -e TMPDIR -e CARGO_INCREMENTAL localhost/px79-ubuntu bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/mpx6-nodes --only build --tier native' px69 "$R"
step nodes-linux host env PAX_BUILD="$N" "$R/tests/mpx6-nodes" --only linux --images "$N/mpx6-nodes"
for d in "$N/mpx6-nodes"/*.img; do
    [ -f "$d" ] && cmp -s -n 4096 "$d" /dev/zero && rm -f "$d"
done
step nodes-boots host env PAX_BUILD="$N" "$R/tests/mpx6-nodes" --images "$N/mpx6-nodes" --tier native --firmware bios
for f in root-ext2-boots root-ext3-boots nodes-boots; do
    printf '%s: %s PASS, %s FAIL, %s SKIP\n' "$f" "$(grep -c 'PASS' "$J/logs/$f.log")" \
        "$(grep -cE 'FAIL|NOT HALTED' "$J/logs/$f.log")" "$(grep -c 'SKIP' "$J/logs/$f.log")"
done
du -sh "$L" "$J"
printf 'job b complete %s\n' "$(date -Is)"
