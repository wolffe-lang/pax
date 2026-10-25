#!/usr/bin/env bash
# Unmodified static Limine against /dev/vda, compared to its Linux run.
# px79 kernel/tools are a separate checkout; no dependency commits pushed.
set -euo pipefail
L=$HOME/lanes/px69
P=$L/pax
K=$L/px79
W=$L/limine-pax
mkdir -p "$W"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp SOURCE_DATE_EPOCH=1700000000
podman run --rm -i --cpuset-cpus 8-11 -v "$L:$L:Z" -e L="$L" -e P="$P" -e W="$W" -e PAX_CACHE -e TMPDIR -e SOURCE_DATE_EPOCH localhost/px69-ubuntu bash -s <<'INNER'
set -euo pipefail
"$L/bin/paxgpt" --seed px69-limine --size 128M "$W/pax.img" 1:esp:4096:135167:esp 2:linux:135168:262103:root 3:bios:2048:4095:bios
cp --sparse=always "$W/pax.img" "$W/linux.img"
"$L/limine-static/limine" bios-install "$W/linux.img" 3 > "$W/linux.log" 2>&1
printf '/bin/limine bios-install /dev/vda 3\n' > "$W/run"
"$P/tools/mkinitramfs" "$W/init.cpio" /bin/limine="$L/limine-static/limine":755 /etc/pax-run="$W/run":644 > "$W/cpio.log"
"$P/tools/mkimage" --conf "$P/boot/limine-initramfs.conf" --add "$W/init.cpio" initramfs.cpio "$(cat "$L/kernel79/elf.path")" "$W/pax.iso"
INNER
PAX_BUILD=$W "$K/tools/qemu-halt" --firmware bios --drive "$W/pax.img" --timeout 120 --serial "$W/pax.serial" --elf "$(cat "$L/kernel79/elf.path")" --marker halt "$W/pax.iso" > "$W/pax.boot" 2>&1
python3 -I - "$W" <<'PY'
from pathlib import Path
import hashlib,sys
p=Path(sys.argv[1]);s=(p/'pax.serial').read_text()
assert 'installed successfully' in s,s
assert 'user: limine pid 1 exit_group 0' in s,s
with (p/'linux.img').open('rb') as a,(p/'pax.img').open('rb') as b:
 while x:=a.read(1048576):assert x==b.read(1048576)
(p/'compare').write_text('PASS: identical whole disk after the same static Limine bios-install on Linux and PAX /dev/vda; px79 99b3bf3b\n')
print((p/'compare').read_text(),end='')
PY
