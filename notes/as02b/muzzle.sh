#!/usr/bin/env bash
# as02b, item 4's fresh muzzle CRT witness (as01's, notes/as01/seam/
# build-clef-kernel's tail and boot-clef-kernel at clef 996a3ccd): muzzle's
# pinned crt0.S and sys.S (clef's census copy) and as01's muzzle-user.S, each
# assembled by the clef PACKAGE and by GNU as, linked by ld.lld 18.1.3 into
# one static program each; the two programs byte-identical; on Linux it
# prints `clef muzzle CRT: pass` and exits 7; then, as PAX's init in an image
# of its own, on every leg with the kernels built through the explicit seam
# with clef (tests/kernel-as K5's). In clef's integration image on kasumi:
#   L=~/lanes/as02b notes/as02b/muzzle.sh PKG-DIR KAS-BUILD OUT
set -uo pipefail
pkg=$1 kas=$2/kernel-as m=$3
cd "$L/pax" || exit 2
. tools/lib.sh
fail=0
src=$L/clef/census/sources/muzzle/src user=$L/clef/notes/as01/seam/muzzle-user.S
mkdir -p "$m"
for name in crt0 sys; do
    "$pkg/clef" --64 -o "$m/$name.o" "$src/$name.S" || fail=1
    as --64 -o "$m/$name.gas.o" "$src/$name.S" || fail=1
done
"$pkg/clef" --64 -o "$m/main.o" "$user" || fail=1
as --64 -o "$m/main.gas.o" "$user" || fail=1
ld.lld -nostdlib -static -z max-page-size=0x1000 -e _start -o "$m/witness.elf" "$m/crt0.o" "$m/sys.o" "$m/main.o" || fail=1
ld.lld -nostdlib -static -z max-page-size=0x1000 -e _start -o "$m/witness.gas.elf" "$m/crt0.gas.o" "$m/sys.gas.o" "$m/main.gas.o" || fail=1
cmp "$m/witness.elf" "$m/witness.gas.elf" && echo "MUZZLE the clef program is the GNU-as program, byte for byte: $(sha256_of "$m/witness.elf")" || fail=1
rc=0; "$m/witness.elf" > "$m/linux.stdout" || rc=$?
printf 'clef muzzle CRT: pass\n' > "$m/expected.stdout"
[ "$rc" = 7 ] && cmp -s "$m/expected.stdout" "$m/linux.stdout" && echo "MUZZLE LINUX PASS: exact stdout and exit 7" || { echo "MUZZLE LINUX FAIL rc=$rc"; fail=1; }
printf '/bin/muzzle-witness\n' > "$m/pax-run"
tools/mkinitramfs "$m/user.cpio" "/bin/muzzle-witness=$m/witness.elf:755" "/etc/pax-run=$m/pax-run:644" > "$m/initramfs.log" || fail=1
for tier in native release; do
    elf=$kas/$tier/K5/out/kmain_console.elf
    tools/mkimage --conf boot/limine-initramfs.conf --add "$m/user.cpio" initramfs.cpio "$elf" "$m/$tier.iso" > /dev/null || fail=1
    for firmware in bios uefi; do
        log=$m/$tier-$firmware.serial.log
        tools/qemu-halt --accel tcg --firmware "$firmware" --serial "$log" --timeout 120 \
            --qemu -m --qemu 1024M --elf "$elf" --marker 'halt|PANIC .*' "$m/$tier.iso" > "$log.verdict" 2>&1
        h=$?
        serial_norm "$log" > "$log.norm"
        if [ "$h" = 0 ] && grep -Fxq 'clef muzzle CRT: pass' "$log.norm" &&
            grep -Fxq 'PAX: init /bin/muzzle-witness ended with status 7; nothing left to run' "$log.norm" &&
            ! grep -Eq '^PANIC |: refused: ' "$log.norm"; then
            echo "MUZZLE PAX PASS $tier $firmware: stdout and exit 7, halted (kernel $(sha256_of "$elf"))"
        else
            echo "MUZZLE PAX FAIL $tier $firmware: halt=$h"; fail=1
        fi
    done
done
exit "$fail"
