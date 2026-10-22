#!/usr/bin/env bash
# An unmodified upstream corpus row alone, to distinguish the row's
# semantics from accumulated resources in the complete replay.
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/focused-fork.pid"
ulimit -c 0
uptime
O=$L/focused-fork
mkdir -p "$O"
export PAX_CACHE=$L/cache PAX_BUILD=$O TMPDIR=$L/tmp
podman run --rm --cpuset-cpus 8-11 --ulimit core=0:0 -v "$L:$L:Z" -e L="$L" -e PAX_CACHE -e TMPDIR localhost/px13-ubuntu bash -c '
set -euo pipefail
O=$L/focused-fork
r=$L/build/mpx5-pelt-r2/mpx5-pelt/root
for role in root pax; do
    run="/bin/env HOME=/ /bin/sh -i -m"
    [ "$role" = root ] || run="/bin/as 1000 1000 /bin/env HOME=/home/pax /bin/sh -i -m"
    printf "%s\n" "$run" > "$O/$role.run"
    args=(/tmp/:1777 /home/pax/:755:1000:1000 /etc/pax-run="$O/$role.run":644)
    while IFS= read -r -d "" f; do
        [ "$f" != "$r/etc/pax-run" ] || continue
        mode=644; case "$f" in "$r/bin/"*) mode=755 ;; esac
        args+=("${f#"$r"}=$f:$mode")
    done < <(find "$r" -type f -print0)
    "$L/pax/tools/mkinitramfs" "$O/$role.cpio" "${args[@]}" > "$O/$role.initramfs.txt"
    "$L/pax/tools/mkimage" --conf "$L/pax/boot/limine-initramfs.conf" --add "$O/$role.cpio" initramfs.cpio \
        "$L/build/mpx5-pelt-r2/mpx5-pelt/native/kmain_console.elf" "$O/$role.iso"
done
'
printf 'cd /tmp\nsh /usr/share/pelt/fork/diff/signal/subshell_end_said_outside.sh; echo focused-st=$?\nexit 0\n' > "$O/row.keys"
for role in root pax; do
    uptime
    rc=0
    taskset -c 8-11 "$L/pax/tools/qemu-halt" --firmware bios --accel tcg --serial "$O/$role.log" --timeout 900 \
        --qemu -m --qemu 1024M --elf "$L/build/mpx5-pelt-r2/mpx5-pelt/native/kmain_console.elf" --marker 'halt|PANIC .*' \
        --type "$O/row.keys" --prompt '$ ' "$O/$role.iso" > "$O/$role.verdict" 2>&1 || rc=$?
    echo "focused fork $role result $rc $(date -Is)"
    tail -n 2 "$O/$role.verdict"
done
uptime
