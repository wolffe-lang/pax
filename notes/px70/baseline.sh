#!/usr/bin/env bash
# Run on kasumi only, launched by setsid -f. No implementation edits.
set -euo pipefail
L=$HOME/lanes/px70
mkdir -p "$L/out" "$L/build/baseline" "$L/tmp" "$L/measure" "$L/cache"
echo $$ > "$L/out/baseline.pid"
trap 'rc=$?; printf "%s\n" "$rc" > "$L/out/baseline.exit"' EXIT
ulimit -c 0
exec 9>"$HOME/lanes/kasumi-cores-4-7.lock"
echo "$(date -Is) waiting for cores 4-7"
flock 9
echo "$(date -Is) acquired cores 4-7"
cd "$L/pax"
git log -1 --format='%H %s'
[ "$(git rev-parse HEAD:kernel/screen/screen.lu)" = "$(git rev-parse 54570380:kernel/screen/screen.lu)" ]
export PAX_CACHE="$L/cache" PAX_BUILD="$L/build/baseline" TMPDIR="$L/tmp"
export PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
# The running 7.2.8 kernel package has been removed; use the installed image.
export PAX_VT_KERNEL=/usr/lib/modules/7.3.0-4-cachyos/vmlinuz
[ -r "$PAX_VT_KERNEL" ]
step() {
    local name=$1; shift
    echo "$(date -Is) START $name"
    "$@" > "$L/out/$name.log" 2>&1 &
    local child=$!
    echo "$child" > "$L/out/$name.pid"
    while kill -0 "$child" 2>/dev/null; do
        echo "$(date -Is) running $name pid=$child; $(du -sh "$L" | cut -f1)"
        sleep 60
    done
    local rc=0
    wait "$child" || rc=$?
    echo "$rc" > "$L/out/$name.exit"
    tail -n 15 "$L/out/$name.log"
    echo "$(date -Is) END $name rc=$rc"
    [ "$rc" = 0 ]
    [ "$(du -sk "$L" | cut -f1)" -lt 15728640 ] || { echo 'lane exceeds 15 GiB'; return 1; }
}
step vt-build podman run --rm --name px70-vt-build --cpuset-cpus 4-7 --ulimit core=0:0 \
    -v "$L:$L:Z" -e L="$L" localhost/px13-ubuntu bash -c '
    set -euo pipefail
    for suffix in "" 2; do
        cc -static -O1 -o "$L/measure/vtprobe$suffix" "$L/pax/notes/px59/vtprobe$suffix.c"
        sha256sum "$L/measure/vtprobe$suffix" "$L/pax/notes/px59/vtprobe$suffix.c"
    done'
for suffix in '' 2; do
    tools/mkinitramfs "$L/measure/vt$suffix.cpio" "/vtprobe$suffix=$L/measure/vtprobe$suffix:755"
done
printf "Linux guest image: %s\n" "$PAX_VT_KERNEL"
sha256sum "$PAX_VT_KERNEL" "$PAX_VT_KERNEL"
qemu-system-x86_64 --version
step vt-measure python3 notes/px70/vt-baseline.py "$L"
for suite in mpx5-screen mpx3-screen mpx5-yew; do
    step "$suite-build" podman run --rm --name "px70-$suite-build" --privileged \
        --cpuset-cpus 4-7 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" \
        -e SUITE="$suite" -e PAX_CACHE -e PAX_BUILD -e TMPDIR \
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
        step "$suite-linux" taskset -c 4-7 tests/"$suite" --only linux --images "$PAX_BUILD/$suite"
    fi
    step "$suite-boot" taskset -c 4-7 tests/"$suite" --images "$PAX_BUILD/$suite" --tier native --firmware bios
    if [ "$suite" = mpx3-screen ]; then
        for repeat in 2 3; do
            step "$suite-boot-$repeat" taskset -c 4-7 tests/"$suite" --images "$PAX_BUILD/$suite" --tier native --firmware bios
        done
    fi
done
echo "$(date -Is) baseline complete"
