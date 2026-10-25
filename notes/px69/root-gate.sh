#!/usr/bin/env bash
# px69, kasumi: all ext2 alternate-writer root rows on both tiers/firmwares,
# plus the unchanged ext3 default on native BIOS. Long, detached job.
set -euo pipefail
L=$HOME/lanes/px69
printf '%s\n' "$$" > "$L/root-gate.pid"
trap 'rc=$?; printf "%s\n" "$rc" > "$L/root-gate.exit"; printf "root gate exit=%s %s\n" "$rc" "$(date -Is)"' EXIT
exec 9> "$HOME/lanes/kasumi-cores-8-11.lock"
printf 'root gate starting %s; waiting for CPUs 8-11\n' "$(date -Is)"
flock 9
taskset -pc 8-11 $$
ulimit -c 0
P=$L/pax
export P L
mkdir -p "$L/root/logs" "$L/root/ext2" "$L/root/control"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp PAX_ENGINE=podman PAX_REQUIRE_UEFI=1
export PAX_E2FS_IMAGE=localhost/px69-ubuntu
export PAX_LINUX_KERNEL=/usr/lib/modules/7.3.0-4-cachyos/vmlinuz
[ -r "$PAX_LINUX_KERNEL" ]
[ "$(du -sk "$L" | cut -f1)" -lt 15728640 ]
find "$P/user/disktools" -type f -print0 | sort -z | xargs -0 sha256sum > "$L/root/source.sha256"
sha256sum "$P/tools/mkdisk" "$P/tests/mpx6-root" "$P/tests/mpx6-disktools" "$P/tests/mpx6-disktools.d/ext2.py" >> "$L/root/source.sha256"
step() {
    local name=$1; shift
    printf '%s start %s\n' "$name" "$(date -Is)"
    if "$@" > "$L/root/logs/$name.log" 2>&1; then
        printf '%s PASS %s\n' "$name" "$(date -Is)"
    else
        local rc=$?
        tail -n 80 "$L/root/logs/$name.log"
        printf '%s FAIL exit=%s\n' "$name" "$rc"
        return "$rc"
    fi
    [ "$(du -sk "$L" | cut -f1)" -lt 15728640 ]
}
step ext2-linux "$P/tests/mpx6-disktools" --only ext2 --programs "$L/bin" --work "$L/ext2/final" --executor "$L/container-exec"
step build podman run --rm -i --name px69-root-build --cpuset-cpus 8-11 --memory 8g --ulimit core=0:0 \
    -v "$L:$L:Z" -e L -e P -e PAX_CACHE -e TMPDIR -e CARGO_INCREMENTAL=0 \
    localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
cd "$P"
export PAX_BUILD=$L/root/ext2
PAX_WOLF=$(tools/fetch-wolf)
export PAX_WOLF
tests/mpx6-root --only build --fstype ext2 --tier both
INNER
# Copy only the pristine build, before Linux recordings or any disks exist.
cp -a "$L/root/ext2/mpx6-root" "$L/root/control/mpx6-root"
step linux-ext2 env PAX_BUILD="$L/root/ext2" "$P/tests/mpx6-root" --only linux --fstype ext2 --images "$L/root/ext2/mpx6-root" --record
step root-ext2 env PAX_BUILD="$L/root/ext2" PAX_EXT2_WRITER="$L/bin/paxext2" "$P/tests/mpx6-root" --fstype ext2 --images "$L/root/ext2/mpx6-root" --tier both --firmware both --rows all
step root-ext3-control env PAX_BUILD="$L/root/control" "$P/tests/mpx6-root" --images "$L/root/control/mpx6-root" --tier native --firmware bios --rows all
sha256sum -c "$L/root/source.sha256" > "$L/root/source.verify"
du -sh "$L" "$L/root"
printf 'root gate complete %s\n' "$(date -Is)"
