#!/usr/bin/env bash
# kasumi only. Coordinator corrected the allocation to CPUs 12-15.
# Final local gauntlet, palette plant and paired scroll measurements.
set -euo pipefail
L=$HOME/lanes/px70
PHASE=${1:?inputs or tail}
case $PHASE in inputs|tail) ;; *) exit 2;; esac
export L
ulimit -c 0
mkdir -p "$L/out" "$L/build/final"
echo $$ > "$L/out/resume-$PHASE.pid"
trap 'rc=$?; echo "$rc" > "$L/out/resume-$PHASE.exit"' EXIT
exec 9>"$HOME/lanes/kasumi-cores-12-15.lock"
echo "$(date -Is) waiting for CPUs12-15"
flock 9
echo "$(date -Is) acquired CPUs12-15"
cd "$L/pax"
git log -1 --format='%H %s'
export PAX_CACHE="$L/cache" PAX_BUILD="$L/build/final" TMPDIR="$L/tmp"
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
step() {
    local label=$1; shift
    echo "$(date -Is) START $label"
    "$@" > "$L/out/$label.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$L/out/$label.pid"
    while kill -0 "$pid" 2>/dev/null; do
        echo "$(date -Is) $label pid=$pid size=$(du -sh "$L" | cut -f1)"
        sleep 30
    done
    local rc=0
    wait "$pid" || rc=$?
    echo "$rc" > "$L/out/$label.exit"
    tail -15 "$L/out/$label.log"
    echo "$(date -Is) END $label rc=$rc"
    [ "$rc" = 0 ]
    [ "$(du -sk "$L" | cut -f1)" -lt 15728640 ]
}
if [ "$PHASE" = inputs ]; then
    step resume-mpx5-yew-boot taskset -c 12-15 tests/mpx5-yew \
        --images "$PAX_BUILD/mpx5-yew" --tier native --firmware bios
    step final-mpx3-console-build podman run --rm --name px70-final-console \
        --privileged --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
        -e L -e PAX_CACHE -e PAX_BUILD -e TMPDIR localhost/px13-ubuntu bash -c '
        set -euo pipefail; cd "$L/pax"; export PAX_WOLF=$(tools/fetch-wolf)
        tests/mpx3-console --no-boot --tier native'
    step final-mpx3-console-boot taskset -c 12-15 tests/mpx3-console \
        --images "$PAX_BUILD/mpx3-console" --tier native --firmware bios
    echo "$(date -Is) input validation complete"
    exit 0
fi
for plant in palette; do
    export PLANT="$plant"
    step "plant-$plant-build" podman run --rm --name "px70-plant-$plant-build" \
        --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
        -e L -e PLANT -e PAX_CACHE -e TMPDIR localhost/px13-ubuntu bash -c '
        set -euo pipefail
        cd "$L/plant-$PLANT"
        git log -1 --format="%H %s"
        export PAX_WOLF=$(tools/fetch-wolf)
        p="$L/build/plant-$PLANT"
        control="$L/build/final/mpx5-screen"
        mkdir -p "$p/native"
        elf=$(tools/build-kernel --src kernel/kmain_console.lu "$p/native")
        cp "$control/vt.keys" "$p/vt.keys"
        tools/mkimage --conf boot/limine-vt.conf --add "$control/vt.cpio" initramfs.cpio "$elf" "$p/native/vt.iso"
        tools/mkimage --conf boot/limine-initramfs.conf --add "$control/session.cpio" initramfs.cpio "$elf" "$p/native/session.iso"'
    # The suite must fail specifically at the planted row; a boot failure
    # or unrelated test failure cannot satisfy this expected-red gate.
    step "plant-$plant-proof" bash -c '
        set -uo pipefail
        export PAX_BUILD="$L/build/plant-$PLANT/run"
        mkdir -p "$PAX_BUILD"
        taskset -c 12-15 "$L/pax/tests/mpx5-screen" \
            --images "$L/build/plant-$PLANT" --tier native --firmware bios \
            > "$L/out/plant-$PLANT-boot.log" 2>&1
        rc=$?
        echo "$rc" > "$L/out/plant-$PLANT-boot.exit"
        [ "$rc" = 1 ] || { echo "unexpected plant exit $rc"; exit 1; }
        pattern="FAIL vt-3-palette-"
        grep -aE "$pattern" "$L/out/plant-$PLANT-boot.log" || exit 1
        grep -a "PASS S4 native bios vt" "$L/out/plant-$PLANT-boot.log" || exit 1
        echo "EXPECTED RED: $PLANT row, suite exit $rc"'
done
step scroll-cost bash "$L/pax/notes/px70/scroll-cost.sh"
echo "$(date -Is) final control, palette plant and paired scroll measurements complete"
