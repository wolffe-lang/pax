set -euo pipefail
. "/home/mfwolffe/lanes/px85/wt-a08cf2f1/tools/lib.sh"
row() { echo "PASS $*"; }
t=release k=/home/mfwolffe/lanes/px85/runs/head-a08cf2f1-control/run-01 images=/home/mfwolffe/lanes/px85/images/head-a08cf2f1-release
    cp "$PAX_ROOT/boot/limine-initramfs.conf" "$k/limine.conf"
    printf '\n    resolution: 3840x2160\n' >> "$k/limine.conf"
    "$PAX_ROOT/tools/mkimage" --conf "$k/limine.conf" --add "$images/probe.cpio" initramfs.cpio "$images/kmain_console.elf" "$k/kasumi.iso"
    python3 -I "$PAX_ROOT/tools/usb-session" --image "$k/kasumi.iso" --elf "$images/kmain_console.elf" \
        --output "$k/session" --firmware uefi --topology root --reference "$PAX_ROOT/notes/px74/linux.rows" --no-serial \
        --flag=--no-pit --flag=--usb-irq=msi --flag=--high-bar --flag=--display-mode=3840x2160 \
        || die "FAIL F8 $t: the serial-less session"
    python3 -I - "$k/session/serial.log" "$k/session/screen.ppm" <<'PY'
import re, sys
s = open(sys.argv[1], errors='replace').read().replace('\r', '')
bar = re.search(r'^xhci 1: BAR0 (0x[0-9a-f]+)$', s, re.M)
assert bar and int(bar[1], 16) >= 1 << 32, 'FAIL F8: xHCI BAR0 not above 4 GiB: %r' % (bar and bar[1])
assert re.search(r'^xhci 1: ports [0-9]+ MSI vector 80 ', s, re.M), 'FAIL F8: no MSI vector 80 line'
assert re.search(r'^clock: HPET [0-9]+ fs/tick, checked against the PM timer$', s, re.M), 'FAIL F8: the clock is not the checked HPET'
assert re.search(r'^timer: LAPIC calibrated by HPET ', s, re.M), 'FAIL F8: the tick is not the HPET\'s'
screen = re.search(r'^screen: 3840x2160 32 bpp .* font spleen 8x16 at 2x, 240x67 cells', s, re.M)
assert screen, 'FAIL F8: the screen line is not 3840x2160 at 2x'
header = open(sys.argv[2], 'rb').read(20).split(b'\n')
assert header[0] == b'P6' and header[1] == b'3840 2160', 'FAIL F8: the screendump is not 3840x2160: %r' % header[:2]
for line in s.splitlines():
    if re.match(r'^(firmware|memory|acpi: (XSDT|RSDT|FACP|APIC|HPET|MCFG)|clock|timer|screen|xhci 1): ', line):
        print('  ' + line)
print('PASS F8: no COM1, no PIT, the xHCI on MSI at BAR0 %s, 3840x2160 at 2x' % bar[1])
PY
    row "F8 $t: kasumi's shape, the session's 18 rows with no serial port"
