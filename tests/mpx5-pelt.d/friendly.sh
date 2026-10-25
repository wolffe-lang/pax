#!/usr/bin/env bash
# Sourced by mpx5-pelt: existing static root/kernel, distinct opt-in shell image.
friendly_image() {
    local d=$1 tier=$2 f
    local args=(/tmp/:1777 /home/pax/:755:1000:1000)
    while IFS= read -r -d '' f; do
        [ "$f" != "$d/root/etc/pax-run" ] || continue
        mode=644; case "$f" in "$d/root/bin/"*) mode=755 ;; esac
        args+=("${f#"$d/root"}=$f:$mode")
    done < <(find "$d/root" -type f -print0)
    # stty is the already-pinned, digest-checked BusyBox binary, run black-box.
    args+=("/bin/stty=$d/bin/busybox:755")
    echo '/bin/env HOME=/ TERM=linux /bin/sh -i +m' > "$d/friendly.run"
    "$PAX_ROOT/tools/mkinitramfs" "$d/friendly.cpio" "${args[@]}" \
        "/etc/pax-run=$d/friendly.run:644" > "$d/friendly.initramfs.txt" || return 1
    "$PAX_ROOT/tools/mkimage" --conf "$PAX_ROOT/boot/limine-initramfs.conf" \
        --add "$d/friendly.cpio" initramfs.cpio "$d/$tier/kmain_console.elf" "$d/$tier/friendly.iso"
}
friendly_boot() {
    local d=$1 tier=$2 leg=$3 console=$4 rc=0 kp= krc=0
    local out=$PAX_BUILD/mpx5-pelt-friendly-$tier-$leg-$console
    mkdir -p "$out"
    local log=$out/serial.log sock=$out/monitor.sock
    python3 -I "$PAX_ROOT/tests/mpx5-pelt.d/friendly.py" generate "$out" "$console" || return 1
    local args=()
    if [ "$console" = framebuffer ]; then
        args=(--qemu -monitor --qemu "unix:$sock,server=on,wait=off")
        python3 -I "$PAX_ROOT/tools/ps2-session" --serial "$log" --monitor "$sock" \
            --keys "$out/friendly.ps2.keys" --out "$out" --gap 0.1 --timeout 120 \
            > "$out/keys.log" 2>&1 &
        kp=$!
    else
        args=(--no-screen --type "$out/friendly.serial.keys" --prompt '$ ')
    fi
    PAX_TYPE_PAUSE=2 "$PAX_ROOT/tools/qemu-halt" --firmware "$leg" --serial "$log" \
        --timeout 240 --qemu -m --qemu 1024M --elf "$d/$tier/kmain_console.elf" \
        --marker 'halt|PANIC .*' "${args[@]}" "$d/$tier/friendly.iso" > "$out/halt.log" 2>&1 || rc=$?
    if [ -n "$kp" ]; then wait "$kp" || krc=$?; fi
    python3 -I "$PAX_ROOT/tests/mpx5-pelt.d/friendly.py" check "$log" "$console" > "$out/check.log" || rc=1
    cat "$out/check.log"
    [ "$rc" = 0 ] && [ "$krc" = 0 ]
}
