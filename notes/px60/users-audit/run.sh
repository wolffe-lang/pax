#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
A=$L/users-audit
printf '%s\n' $$ > "$A/job.pid"
trap 's=$?; echo "$s" > /home/mfwolffe/lanes/px60/users-audit/job.status; exit "$s"' EXIT
for label in base head; do
    echo "BUILD $label $(date -Iseconds)"
    podman run --rm --name "px60-users-$label-build" -v "$A/$label:/pax" -v "$A/$label-out:/out" \
      -v "$L/cache:/cache" -w /pax -e PAX_CACHE=/cache -e PAX_BUILD=/out -e SOURCE_DATE_EPOCH=0 \
      localhost/px13-ubuntu bash -c '
        set -euo pipefail
        export PAX_WOLF=$(tools/fetch-wolf)
        tools/fetch-limine
        tools/mkcred /out/bin > /out/programs.txt
        printf "root:x:0:0:root:/:/bin/pelt\n" > /out/passwd
        printf "root:x:0:\n" > /out/group
        printf "/bin/as 1000 1000 /bin/ident soak 100000\n" > /out/run
        tools/mkinitramfs /out/soak-user.cpio /bin/cred=/out/bin/cred:755 /bin/ids=/out/bin/ids:755 \
          /bin/ident=/out/bin/ident:755 /bin/ident-setid=/out/bin/ident:6755 /bin/as=/out/bin/as:755 \
          /etc/passwd=/out/passwd:644 /etc/group=/out/group:644 /etc/pax-run=/out/run:644 > /out/initramfs.txt
        mkdir -p /out/native
        tools/build-kernel --src /pax/kernel/kmain_console.lu /out/native > /out/elf.path 2>/out/kernel-build.log
        tools/mkimage --conf boot/limine-initramfs.conf --add /out/soak-user.cpio initramfs.cpio \
          /out/native/kmain_console.elf /out/soak-user.iso
        sha256sum /out/native/kmain_console.elf /out/soak-user.cpio /out/soak-user.iso
      '
done
cmp "$A/base-out/soak-user.cpio" "$A/head-out/soak-user.cpio"
cmp "$A/base-out/native/kmain_console.elf" "$A/head-out/native/kmain_console.elf"
cmp "$A/base-out/soak-user.iso" "$A/head-out/soak-user.iso"
echo 'PASS base/head kernel, initramfs and fixed-date ISO are byte-identical'
for label in base head; do
    echo "BOOT $label $(date -Iseconds)"
    python3 -I "$A/time.py" "$label" "$A/$label" taskset -c 0-3 "$A/$label/tools/qemu-halt" \
      --accel tcg --firmware bios --serial "$A/$label.serial.log" --timeout 1500 --qemu -m --qemu 256M \
      --elf "$A/$label-out/native/kmain_console.elf" --marker 'halt|PANIC .*' "$A/$label-out/soak-user.iso"
    grep -a -F '100000 rounds, 1000000 calls, 10000 children that changed their ids, 0 wrong answers' "$A/$label.serial.log"
    grep -a -F 'PAX: init /bin/as ended with status 0' "$A/$label.serial.log"
done
