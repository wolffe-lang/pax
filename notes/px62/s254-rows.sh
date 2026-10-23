#!/usr/bin/env bash
# px62, kasumi only: s254's [os.fs.lock] and [os.fs.mkfifo] rows
# (wolf-lang's crates/wolf_driver/tests/fixtures/fs_gaps/{lock,fifo}_rows.lu)
# built by a wolf from wolf-lang trunk (no release carries s254 yet:
# v0.2.34 predates it), linked static, then run as pid 1 on Linux (a
# throwaway container) and on PAX (the head's kmain_console). The wolf
# source is a read-only `git archive` of the org's checkout; nothing of
# wolf-lang is changed. Builds in px57-rust on CPUs 4-7.
#   s254-rows.sh WOLFSRC.tar RUNDIR
set -euo pipefail
L=$HOME/lanes/px62
tarball=$1 run=$2
S=$L/s254; rm -rf "$S"; mkdir -p "$S/src" "$S/bin" "$S/tmp"
tar -xf "$tarball" -C "$S/src"
ulimit -c 0
podman run --rm --cpuset-cpus 4-7 --ulimit core=0:0 -v "$L:$L:Z" -e CARGO_INCREMENTAL=0 -e TMPDIR="$S/tmp" \
    localhost/px57-rust bash -c '
    set -euo pipefail
    S=$1; cd "$S/src"
    CARGO_TARGET_DIR=$S/target cargo build --release --locked -j 4 -p wolf_driver -p wolf_rt >&2
    w=$S/target/release/wolf
    "$w" --version
    rev=$(sed -n "s/^wolf-std-commit = //p" crates/wolf_driver/STD-PIN)
    git -C "$S" init -q std && git -C "$S/std" fetch -q --depth 1 https://github.com/wolffe-lang/wolf-std "$rev"
    git -C "$S/std" -c advice.detachedHead=false checkout -q FETCH_HEAD
    [ "$(git -C "$S/std" rev-parse HEAD)" = "$rev" ]
    mkdir -p "$S/cc"; printf "#!/bin/sh\nexec %s -static \"\$@\"\n" "$(command -v cc)" > "$S/cc/cc"; chmod +x "$S/cc/cc"
    for r in lock_rows fifo_rows; do
        cp crates/wolf_driver/tests/fixtures/fs_gaps/$r.lu "$S/bin/$r.lu"
        (cd "$S/bin" && PATH="$S/cc:$PATH" WOLF_STD=$S/std/std "$w" build --no-cache $r.lu -o $r)
        readelf -lW "$S/bin/$r" | grep -q INTERP && { echo "$r not static"; exit 1; }
        sha256sum "$S/bin/$r"
    done
' px62 "$S"
for r in lock_rows fifo_rows; do
    mkdir -p "$S/root-$r/bin" "$S/root-$r/t"
    cp "$S/bin/$r" "$S/root-$r/bin/$r"
    echo "== linux $r"
    podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 --network none --tmpfs /w:rw,mode=755 \
        -v "$S/bin:/p:ro,Z" -w /w localhost/px13-ubuntu /p/$r > "$S/$r.linux" 2>&1 || true
    cat "$S/$r.linux"
    echo "== pax $r"
    cd "$L/pax"
    export PAX_CACHE=$L/cache PAX_BUILD=$S
    echo "/bin/$r" > "$S/root-$r/run"
    tools/mkinitramfs "$S/$r.cpio" "/bin/$r=$S/bin/$r:755" "/etc/pax-run=$S/root-$r/run:644" > /dev/null
    tools/mkimage --conf boot/limine-initramfs.conf --add "$S/$r.cpio" initramfs.cpio "$L/build/$run/mpx3-maps/native/kmain_console.elf" "$S/$r.iso" > /dev/null
    taskset -c 0-3 tools/qemu-halt --firmware bios --serial "$S/$r.serial" --timeout 300 \
        --elf "$L/build/$run/mpx3-maps/native/kmain_console.elf" --marker 'halt|PANIC .*' "$S/$r.iso" > "$S/$r.verdict" 2>&1 || true
    tr -d '\r' < "$S/$r.serial" | awk '/^user: exec pid 1 /{on=1;next} on && /^user: [^ ]+ pid 1 (exit_group|exit) /{exit} on { i=index($0,"user: "); if (i==1) next; if (i>1) {printf "%s", substr($0,1,i-1); next}; print }' > "$S/$r.pax"
    cat "$S/$r.pax"
    grep -a -E 'refused|ENOSYS|PAX: init' "$S/$r.serial" | tr -d '\r'
    if cmp -s "$S/$r.linux" "$S/$r.pax"; then echo "SAME $r $(sha256sum < "$S/$r.pax" | cut -c1-16)"; else echo "DIFFER $r"; diff "$S/$r.linux" "$S/$r.pax" || true; fi
done
