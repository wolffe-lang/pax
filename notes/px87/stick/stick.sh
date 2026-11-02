#!/usr/bin/env bash
# px87: the metal session's stick at HEAD, by px86's recipe (notes/px86/hasu/stick.sh) on kasumi, run by
# the lane's hostchain.sh (one hold of kasumi-cores-0-3.lock, CPUs 0-3; `ctr` is a px76-ubuntu container):
#   sbuild   (container) tools/mkdistribution: the release pair at HEAD (kernel, installer, disk tools, Limine,
#            reboot/poweroff), tests/distribution on both archives, then the live payload (px86's
#            live-payload.py: /etc/pax-live-login, /etc/pax-run, /root); the toolchain archives read twice
#   sstick   (host: tools/mkdisk's disk tools run in podman) tools/mkdisk --usb with notes/px87/stick/
#            limine-usb-ab.conf, tools/check-usb (six files), the allow-list naming no disk, a second build
#            byte-identical, the EFI and MBR corruptions refused by name, the image read twice; and a copy
#            whose configuration makes the second entry the default (`default_entry: 2`), for its leg
#   squal-*  (container) notes/px87/stick/qual.py on copies: serial (the live session's rows), kasumi (no COM1,
#            the USB keyboard, the xHCI on MSI behind OVMF's 64 GiB window), fbread (the second entry)
#   stick.sh HEAD WORKTREE OUT
set -uo pipefail
HEAD=$1 W=$2 O=$3
SI=$L/stick-in
short=${HEAD:0:8}
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; [ "$rc" = 0 ] || { echo "STICK CHAIN STOPPED at $n"; exit "$rc"; }; }
[ "$(git -C "$W" rev-parse HEAD)" = "$HEAD" ] || { echo "the worktree is not at $HEAD"; exit 3; }
[ -z "$(git -C "$W" status --porcelain --untracked-files=no)" ] || { echo "the worktree is dirty"; exit 3; }
[ ! -e "$O/sout" ] || { echo "$O/sout exists"; exit 3; }
mkdir -p "$O/slogs"

sbuild() {
    cat > "$O/sbuild-inside.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd $W
export PAX_CACHE=$L/cache PAX_BUILD=$O/sb TMPDIR=$L/tmp PAX_LOPE_REPO=$SI/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
[ "\$(git rev-parse HEAD)" = $HEAD ]
printf '%s START release-pair\n' "\$(date -u +%FT%TZ)"
tools/mkdistribution "$SI/inputs/base-dev.cpio" "$SI/build/inputs" "$O/sout" > "$O/slogs/distribution.log" 2>&1
printf '%s END release-pair\n' "\$(date -u +%FT%TZ)"
grep -E '^(distribution|I1|R0|image)' "$O/slogs/distribution.log" || true
python3 -I "$SI/scripts/live-payload.py" "$W" "$O/sout"
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$O/archive-reads.txt"
for n in 1 2; do sha256sum "$SI/inputs/limine-download/limine-binary.tar.gz"; done | tee "$O/limine-reads.txt"
nm "$O/sout/kernel/kmain_console.elf" > "$O/sout/kernel.symbols"
qemu-system-x86_64 --version | head -1
EOF
    ctr bash "$O/sbuild-inside.sh"
}

sstick() (
    set -euo pipefail
    cd "$W"
    export PAX_CACHE=$L/cache PAX_BUILD=$O/sb TMPDIR=$L/tmp PAX_ENGINE=podman
    . tools/lib.sh
    export SOURCE_DATE_EPOCH=$(cat "$O/sout/source-date-epoch")
    [ "$(cat "$O/sout/commit")" = "$HEAD" ]
    elf=$O/sout/kernel/kmain_console.elf cpio=$O/sout/release.cpio conf=$W/notes/px87/stick/limine-usb-ab.conf
    allow=$W/boot/install-targets
    load_limine_pin
    stick=$O/sout/pax-stick-$short.img
    expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
      --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
      --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
      --expect "/boot/limine/limine.conf=$conf"
      --expect "/pax/install-targets=$allow")
    python3 -I tests/usb-tools
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$HEAD" "$stick" > "$O/slogs/usb-build.log"
    tools/check-usb "$stick" "${expected[@]}" | tee "$O/slogs/usb-check.log"
    entries=$(grep -cvE '^[[:space:]]*(#|$)' "$allow" || true)
    [ "$entries" = 0 ] || { echo "FAIL boot/install-targets names $entries line(s)"; exit 1; }
    echo "PASS the allow-list on the image is boot/install-targets ($(wc -l < "$allow") lines, $entries entries): the stick writes no disk"
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$HEAD" "$O/sout/repeat.img" > "$O/slogs/usb-repeat.log"
    cmp "$stick" "$O/sout/repeat.img"
    echo 'PASS second stick build byte-identical'
    rm "$O/sout/repeat.img"
    for fault in efi mbr; do
        broken=$O/sout/usb-$fault-red.img
        cp --sparse=always "$stick" "$broken"
        python3 -I tests/usb-stick.d/corrupt.py "$broken" "$fault"
        if tools/check-usb "$broken" > "$O/slogs/usb-$fault-red.log" 2>&1; then echo 'FAIL corrupt image accepted'; exit 1; fi
        case $fault in
            efi) grep -F 'required boot file missing: /EFI/BOOT/BOOTX64.EFI' "$O/slogs/usb-$fault-red.log" ;;
            mbr) grep -F 'protective MBR must cover the disk' "$O/slogs/usb-$fault-red.log" ;;
        esac
        rm "$broken"
    done
    { printf 'default_entry: 2\n'; cat "$conf"; } > "$O/sout/fbread-default.conf"
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$O/sout/fbread-default.conf" --kernel-commit "$HEAD" \
        "$O/sout/fbread-default.img" > "$O/slogs/usb-fbread.log"
    for n in 1 2; do sha256sum "$stick" | tee "$O/stick-read-$n.sha256"; done
    stat -c '%s' "$stick"
)

# The qualification script is this script's sibling (it may be newer than HEAD's: a notes-only change).
Q=$(cd "$(dirname "$0")" && pwd)/qual.py
squal() {
    ctr bash -c "cd $W && export PAX_CACHE=$L/cache TMPDIR=$L/tmp && python3 -I $Q $W $1 $O/sout/kernel/kmain_console.elf $HEAD $O/q-$2 $3"
}

step sbuild sbuild
step sstick sstick
step squal-serial squal "$O/sout/pax-stick-$short.img" serial serial
step squal-kasumi squal "$O/sout/pax-stick-$short.img" kasumi kasumi
step squal-fbread squal "$O/sout/fbread-default.img" fbread serial
printf '%s STICK CHAIN DONE %s\n' "$(ts)" "$short"
