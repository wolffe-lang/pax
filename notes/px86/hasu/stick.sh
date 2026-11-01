#!/usr/bin/env bash
# px86: the maintainer's install stick at HEAD by px78b's recipe (197330ad's: notes/px78b/scripts/sbuild*.sh,
# sstick.sh, sline.sh, sleg.sh), the leg run by the head's own metal.py (PAX_METAL_LISTED, no lane variant):
#   1 sbuild   the release pair in px75-ubuntu:2 (tools/mkdistribution), the live payload, the archive reads
#   2 sstick   on the host: tools/mkdisk --usb, tools/check-usb (six files), a second build byte-identical,
#              the EFI and MBR corruptions refused by name, the plain stick's sha256 twice
#   3 sline    on the host: the 860's line appended to /pax/install-targets on a copy by the stick's own paxfat,
#              read back, check-usb again, the staged name, read-only, sha256 twice
#   4 sleg-*   the kasumi leg on a COPY of that exact image under KVM in px78-ubuntu:1: the 860 target used
#              (fat32, then ext4), the maintainer's serial, the line already on the stick
# Every step holds both block-A lock names for itself alone; a red step stops the chain.
#   stick.sh HEAD SERIAL
set -uo pipefail
L=/home/mfwolffe/lanes/px86
HEAD=$1 SERIAL=$2
short=${HEAD:0:8}
printf '%s\n' "$$" > $L/stick.pid
export PATH=$L/bin:/home/mfwolffe/lanes/hasu-env/bin:/home/mfwolffe/lanes/hasu-env/profile/bin:$PATH
taskset -cp 0-5 $$ > /dev/null   # block A for every host step and its children
ts() { date -u +%FT%TZ; }
lock() { printf '%s (block A held by the chain) %s\n' "$(ts)" "$1"; }
unlock() { :; }
take() {
  [ "${STICK_HELD:-}" = 1 ] && { printf '%s block A already held by the calling chain\n' "$(ts)"; return 0; }
  exec 9>/home/mfwolffe/lanes/hasu-block-A.lock
  until flock -w 240 9; do printf '%s hasu-block-A.lock held; waiting\n' "$(ts)"; done
  exec 8>/home/mfwolffe/lanes/hasu-A.lock
  until flock -w 240 8; do printf '%s hasu-A.lock held; waiting\n' "$(ts)"; done
  printf '%s block A acquired (both names) %s\n' "$(ts)" "$1"
}
release() { [ "${STICK_HELD:-}" = 1 ] && return 0; flock -u 8; exec 8>&-; flock -u 9; exec 9>&-; printf '%s block A RELEASED (both names) %s\n' "$(ts)" "$1"; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; echo $rc > $L/stick-$n.exit; [ $rc = 0 ] || { echo "STICK CHAIN STOPPED at $n"; release stick; exit $rc; }; }
[ "$(git -C $L/stick rev-parse HEAD)" = "$HEAD" ] || { echo "stick checkout is not at $HEAD"; exit 3; }
[ -z "$(git -C $L/stick status --porcelain --untracked-files=no)" ] || { echo "stick checkout dirty"; exit 3; }
mkdir -p $L/slogs

sbuild() {
  cat > $L/sbuild-inside.sh <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd $L/stick
export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
[ "\$(git rev-parse HEAD)" = $HEAD ]
[ -z "\$(git status --porcelain --untracked-files=no)" ]
printf '%s START release-pair\n' "\$(date -u +%FT%TZ)"
tools/mkdistribution "$L/inputs/base-dev.cpio" "$L/build/inputs" "$L/sout" > "$L/slogs/distribution.log" 2>&1
printf '%s END release-pair\n' "\$(date -u +%FT%TZ)"
python3 -I "$L/scripts/live-payload.py" "$L/stick" "$L/sout"
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$L/archive-reads.txt"
for n in 1 2; do sha256sum "$L/inputs/limine-download/limine-binary.tar.gz" | tee "$L/limine-read-\$n.sha256"; done
nm "$L/sout/kernel/kmain_console.elf" > "$L/sout/kernel.symbols"
qemu-system-x86_64 --version | head -1
EOF
  lock sbuild
  local rc=0
  /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px86-sbuild --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    -v "$L:$L" -w "$L/stick" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    localhost/px75-ubuntu:2 taskset -c 0-5 bash "$L/sbuild-inside.sh" || rc=$?
  unlock sbuild
  return $rc
}

sstick() {
  lock sstick
  local rc=0
  ( set -euo pipefail
    cd "$L/stick"
    export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
    . tools/lib.sh
    export SOURCE_DATE_EPOCH=$(cat "$L/sout/source-date-epoch")
    head=$(cat "$L/sout/commit"); [ "$head" = "$HEAD" ]
    elf=$L/sout/kernel/kmain_console.elf cpio=$L/sout/release.cpio conf=$PWD/boot/limine-usb.conf allow=$PWD/boot/install-targets
    load_limine_pin
    stick=$L/sout/pax-install-$short.img
    expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
      --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
      --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
      --expect "/boot/limine/limine.conf=$conf"
      --expect "/pax/install-targets=$allow")
    python3 -I tests/usb-tools
    python3 -I tests/usb-linux-fetch
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$stick" > "$L/slogs/usb-build.log"
    tools/check-usb "$stick" "${expected[@]}" | tee "$L/slogs/usb-check.log"
    entries=$(grep -cvE '^[[:space:]]*(#|$)' "$allow" || true)
    [ "$entries" = 0 ] || { echo "FAIL boot/install-targets names $entries line(s)"; exit 1; }
    echo "PASS the allow-list on the image is boot/install-targets ($(wc -l < "$allow") lines, $entries entries)"
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$L/sout/repeat.img" > "$L/slogs/usb-repeat.log"
    cmp "$stick" "$L/sout/repeat.img"
    echo 'PASS second stick build byte-identical'
    rm "$L/sout/repeat.img"
    for fault in efi mbr; do
      broken=$L/sout/usb-$fault-red.img
      cp --sparse=always "$stick" "$broken"
      python3 -I tests/usb-stick.d/corrupt.py "$broken" "$fault"
      if tools/check-usb "$broken" > "$L/slogs/usb-$fault-red.log" 2>&1; then echo 'FAIL corrupt image accepted'; exit 1; fi
      case $fault in
        efi) grep -F 'required boot file missing: /EFI/BOOT/BOOTX64.EFI' "$L/slogs/usb-$fault-red.log" ;;
        mbr) grep -F 'protective MBR must cover the disk' "$L/slogs/usb-$fault-red.log" ;;
      esac
      rm "$broken"
    done
    sha256sum "$stick" | tee "$L/stick-plain-read-1.sha256"
    sha256sum "$stick" | tee "$L/stick-plain-read-2.sha256"
    stat -c '%s' "$stick"
  ) || rc=$?
  unlock sstick
  return $rc
}

sline() {
  lock sline
  local rc=0
  ( set -euo pipefail
    cd "$L/stick"
    export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp
    . tools/lib.sh
    load_limine_pin
    plain=$L/sout/pax-install-$short.img k=$L/sout/pax-install-kasumi-$short.img
    rm -f "$k" "$k.tmp"
    cp --sparse=always "$plain" "$k.tmp"
    esp=$(python3 -I -c '
import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$k.tmp")
    echo "ESP at byte $esp"
    printf 'model=Samsung SSD 860 serial=%s\n' "$SERIAL" > $L/allow-line
    $L/sout/disktools/paxfat --offset "$esp" append "$k.tmp" $L/allow-line /pax/install-targets
    $L/sout/disktools/paxfat --offset "$esp" cat "$k.tmp" /pax/install-targets > $L/install-targets.on-stick
    cat boot/install-targets $L/allow-line > $L/install-targets.expected
    cmp $L/install-targets.on-stick $L/install-targets.expected
    n=$(grep -cvE '^[[:space:]]*(#|$)' $L/install-targets.on-stick || true)
    [ "$n" = 1 ] && grep -qxF "model=Samsung SSD 860 serial=$SERIAL" $L/install-targets.on-stick
    echo "PASS /pax/install-targets on the copy: boot/install-targets plus the one line ($n entry)"
    tools/check-usb "$k.tmp" --expect "/boot/pax=$L/sout/kernel/kmain_console.elf" --expect "/boot/initramfs.cpio=$L/sout/release.cpio" \
      --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI" --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" \
      --expect "/boot/limine/limine.conf=$PWD/boot/limine-usb.conf" --expect "/pax/install-targets=$L/install-targets.expected" | tee $L/slogs/kasumi-usb-check.log
    mv "$k.tmp" "$k"
    chmod 444 "$k"
    for n in 1 2; do sha256sum "$k" | tee $L/kasumi-hasu-build-read-$n.sha256; done
    stat -c '%s' "$k"
  ) || rc=$?
  unlock sline
  return $rc
}

sleg() {
  local used=$1
  local k=$L/sout/pax-install-kasumi-$short.img W=$L/leg-stick-$used I=$L/leg-inputs
  [ ! -e "$W" ] || { echo "$W exists"; return 2; }
  mkdir -p "$W/metal" "$I/build/disktools/bin"
  printf '%s\n' "$L/sout/kernel/kmain_console.elf" > "$I/build/disktools/native.elf.path"
  cp "$L/sout/disktools/paxfat" "$I/build/disktools/bin/paxfat"
  cp --sparse=always "$k" "$W/metal/stick.img"
  chmod 644 "$W/metal/stick.img"
  sha256sum "$W/metal/stick.img" | tee "$W/stick-at-start.sha256"
  [ "$(cut -d' ' -f1 "$W/stick-at-start.sha256")" = "$(cut -d' ' -f1 $L/kasumi-hasu-build-read-1.sha256)" ] || { echo "the copy differs from the staged image"; return 2; }
  lock sleg-$used
  local rc=0
  /home/mfwolffe/lanes/hasu-env/bin/podman run --rm --name px86-sleg-$used --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 \
    --device /dev/kvm -v "$L:$L" -w "$L/stick" \
    -e PAX_CACHE=$L/cache -e PAX_BUILD=$L/sb -e TMPDIR=$L/tmp -e PAX_METAL_ACCEL=kvm -e SOURCE_DATE_EPOCH=1700000000 \
    -e PAX_METAL_TARGET=860 -e PAX_METAL_TARGET_SERIAL="$SERIAL" -e PAX_METAL_LISTED=1 -e PAX_METAL_USED=$used \
    localhost/px78-ubuntu:1 taskset -c 0-5 bash -c "time python3 -I $L/stick/tests/mpx6-install.d/metal.py $L/stick $I $W/metal run" || rc=$?
  unlock sleg-$used
  return $rc
}

# One hold for the chain (about 12 minutes of work, never idle): the maintainer's stick is the lane's first
# deliverable, and seven separate acquisitions on a block three other chains share cost an hour of waits.
take stick
step sbuild sbuild
step sstick sstick
step sline sline
step sleg-fat32 sleg fat32
step sleg-ext4 sleg ext4
release stick
printf '%s STICK CHAIN DONE %s\n' "$(ts)" "$short"
