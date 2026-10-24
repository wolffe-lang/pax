#!/usr/bin/env bash
# kasumi only. Coordinator corrected the allocation to CPUs 12-15.
# Full local control plus two isolated module-footprint plants (RULES R2).
set -euo pipefail
L=$HOME/lanes/px70
export L
ulimit -c 0
mkdir -p "$L/out" "$L/build/editing"
echo $$ > "$L/out/editing-validation.pid"
trap 'rc=$?; echo "$rc" > "$L/out/editing-validation.exit"' EXIT
exec 9>"$HOME/lanes/kasumi-cores-12-15.lock"
echo "$(date -Is) waiting for CPUs12-15"
flock 9
echo "$(date -Is) acquired CPUs12-15"
cd "$L/pax"
git log -1 --format='%H %s'
export PAX_CACHE="$L/cache" PAX_BUILD="$L/build/editing" TMPDIR="$L/tmp"
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
for suite in mpx5-screen mpx3-screen mpx5-yew; do
    step "editing-$suite-build" podman run --rm --name "px70-editing-$suite" \
        --privileged --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
        -e L -e SUITE="$suite" -e PAX_CACHE -e PAX_BUILD -e TMPDIR \
        localhost/px13-ubuntu bash -c '
        set -euo pipefail
        cd "$L/pax"
        export PAX_WOLF=$(tools/fetch-wolf)
        if grep -q -- "--only build" tests/"$SUITE"; then
            tests/"$SUITE" --only build --tier native
        else
            tests/"$SUITE" --no-boot --tier native
        fi'
    if [ "$suite" = mpx5-yew ]; then
        step "editing-$suite-linux" taskset -c 12-15 tests/"$suite" \
            --only linux --images "$PAX_BUILD/$suite"
    fi
    step "editing-$suite-boot" taskset -c 12-15 tests/"$suite" \
        --images "$PAX_BUILD/$suite" --tier native --firmware bios
done
for plant in ech region; do
    export PLANT="$plant"
    step "plant-$plant-build" podman run --rm --name "px70-plant-$plant-build" \
        --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
        -e L -e PLANT -e PAX_CACHE -e TMPDIR localhost/px13-ubuntu bash -c '
        set -euo pipefail
        cd "$L/plant-$PLANT"
        git log -1 --format="%H %s"
        export PAX_WOLF=$(tools/fetch-wolf)
        p="$L/build/plant-$PLANT"
        control="$L/build/editing/mpx5-screen"
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
        if [ "$PLANT" = ech ]; then pattern="FAIL vt-2-ECH|FAIL vt-3-char-ech";
        else pattern="FAIL vt-2-DECSTBM|FAIL vt-3-region-"; fi
        grep -aE "$pattern" "$L/out/plant-$PLANT-boot.log" || exit 1
        grep -a "PASS S4 native bios vt" "$L/out/plant-$PLANT-boot.log" || exit 1
        echo "EXPECTED RED: $PLANT row, suite exit $rc"'
done
echo "$(date -Is) editing control and two local plants complete"
