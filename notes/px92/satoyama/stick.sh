#!/usr/bin/env bash
# px92: the maintainer's install stick at trunk's HEAD by px86's recipe (notes/px86/hasu/stick.sh, itself
# px78b's), on satoyama, in two chunks, each one hold of one slot's lock (never idle, under 2 h):
#   stick.sh SLOT HEAD SERIAL build   sbuild  the release pair in px75-ubuntu:2 (tools/mkdistribution), the live
#                                             payload (px86's live-payload.py), the archive reads
#                                     sstick  on the host: tools/mkdisk --usb, tools/check-usb (six files), the
#                                             allow-list naming no disk, a second build byte-identical, the EFI
#                                             and MBR corruptions refused by name, the plain stick's sha256 twice
#                                     sline   on the host: the 860's line appended to /pax/install-targets on a
#                                             copy by the stick's own paxfat, read back, check-usb again, the
#                                             staged name, read-only, sha256 twice
#   stick.sh SLOT HEAD SERIAL legs    the kasumi leg on COPIES under KVM in px78-ubuntu:1, the head's metal.py
#                                     through notes/px92/make-variant.py (R-px92-3), the 860 and the
#                                     maintainer's serial, the line already on each stick:
#                                     sleg-mpx6   px86's staged stick (adb53141) onto a used 860 (fat32), the
#                                                 installed target kept: the state M-PX6 left on kasumi's 860
#                                     sleg-pax    the new stick onto a copy of that target, px87's rows
#                                     sleg-fat32, sleg-ext4   px86's used cases with the new stick, px87's rows
# SLOT is A (CPUs 0-3,8-11), B (4-7,12-15) or AB (both locks, A outside then B, CPUs 0-15: the maintainer's
# one-heavy-job ruling of 2026-11-04, every run after the first build); a red step stops the chunk.
set -uo pipefail
L=/home/mfwolffe/lanes/px92
SLOT=$1 HEAD=$2 SERIAL=$3 CHUNK=$4
case $SLOT in A) CPUS=0-3,8-11 ;; B) CPUS=4-7,12-15 ;; AB) CPUS=0-15 ;; ABA) CPUS=0-3,8-11 ;; NOLOCK-B) CPUS=4-7,12-15 ;; *) echo "slot A, B, AB or ABA (both locks; ABA on slot A's CPUs)"; exit 2 ;; esac
short=${HEAD:0:8}
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
export PATH=/home/mfwolffe/lanes/satoyama-env/bin:$PATH TMPDIR=$L/tmp
printf '%s\n' "$$" > "$L/$CHUNK.pid"
taskset -cp "$CPUS" $$ > /dev/null   # the slot for every host step and its children
ts() { date -u +%FT%TZ; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; echo $rc > "$L/$CHUNK-$n.exit"; [ $rc = 0 ] || { echo "CHUNK $CHUNK STOPPED at $n"; exit $rc; }; }
[ "$(git -C "$L/stick" rev-parse HEAD)" = "$HEAD" ] || { echo "stick checkout is not at $HEAD"; exit 3; }
[ -z "$(git -C "$L/stick" status --porcelain --untracked-files=no)" ] || { echo "stick checkout dirty"; exit 3; }
mkdir -p "$L/slogs"
ctr() {  # NAME IMAGE KVM CMD...: one container on the slot (taskset inside), the lock already held
  local name=$1 img=$2 kvm=$3; shift 3
  local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  "$P" run --rm --name "px92-$name" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$L/stick" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    ${CTR_ENV:-} "$img" taskset -c "$CPUS" "$@"
}

sbuild() {
  cat > "$L/sbuild-inside.sh" <<EOF
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
grep -E '^(I0|I1|R0|image|distribution)' "$L/slogs/distribution.log" || true
python3 -I "$L/scripts/live-payload.py" "$L/stick" "$L/sout"
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$L/archive-reads.txt"
for n in 1 2; do sha256sum "$L/inputs/limine-download/limine-binary.tar.gz" | tee "$L/limine-read-\$n.sha256"; done
nm "$L/sout/kernel/kmain_console.elf" > "$L/sout/kernel.symbols"
qemu-system-x86_64 --version | head -1
EOF
  CTR_ENV= ctr sbuild localhost/px75-ubuntu:2 0 bash "$L/sbuild-inside.sh"
}

sstick() (
  set -euo pipefail
  cd "$L/stick"
  export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
  [ "$(command -v podman)" = "$P" ] || { echo "podman on PATH is not satoyama-env's"; exit 1; }
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
  rm "$L/sout/repeat.img" "$L/sout/repeat.img.inputs.json"
  for fault in efi mbr; do
    broken=$L/sout/usb-$fault-red.img
    cp --sparse=always "$stick" "$broken"
    python3 -I tests/usb-stick.d/corrupt.py "$broken" "$fault"
    if tools/check-usb "$broken" > "$L/slogs/usb-$fault-red.log" 2>&1; then echo 'FAIL corrupt image accepted'; exit 1; fi
    case $fault in
      efi) want='required boot file missing: /EFI/BOOT/BOOTX64.EFI' ;;
      mbr) want='protective MBR must cover the disk' ;;
    esac
    grep -qF "$want" "$L/slogs/usb-$fault-red.log"
    echo "PASS a copy with its $fault broken is refused by name ('$want')"
    rm "$broken"
  done
  sha256sum "$stick" | tee "$L/stick-plain-read-1.sha256"
  sha256sum "$stick" | tee "$L/stick-plain-read-2.sha256"
  stat -c '%s' "$stick"
)

sline() (
  set -euo pipefail
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
  printf 'model=Samsung SSD 860 serial=%s\n' "$SERIAL" > "$L/allow-line"
  "$L/sout/disktools/paxfat" --offset "$esp" append "$k.tmp" "$L/allow-line" /pax/install-targets
  "$L/sout/disktools/paxfat" --offset "$esp" cat "$k.tmp" /pax/install-targets > "$L/install-targets.on-stick"
  cat boot/install-targets "$L/allow-line" > "$L/install-targets.expected"
  cmp "$L/install-targets.on-stick" "$L/install-targets.expected"
  n=$(grep -cvE '^[[:space:]]*(#|$)' "$L/install-targets.on-stick" || true)
  [ "$n" = 1 ] && grep -qxF "model=Samsung SSD 860 serial=$SERIAL" "$L/install-targets.on-stick"
  echo "PASS /pax/install-targets on the copy: boot/install-targets plus the one line ($n entry), sha256 $(sha256sum "$L/install-targets.on-stick" | cut -c1-16)..."
  tools/check-usb "$k.tmp" --expect "/boot/pax=$L/sout/kernel/kmain_console.elf" --expect "/boot/initramfs.cpio=$L/sout/release.cpio" \
    --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI" --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" \
    --expect "/boot/limine/limine.conf=$PWD/boot/limine-usb.conf" --expect "/pax/install-targets=$L/install-targets.expected" | tee "$L/slogs/kasumi-usb-check.log"
  mv "$k.tmp" "$k"
  chmod 444 "$k"
  for n in 1 2; do sha256sum "$k" | tee "$L/kasumi-build-read-$n.sha256"; done
  stat -c '%s' "$k"
)

# One leg: NAME STICK USED [PX87] [TARGET_FROM] [KEEP]. The leg's own inputs: the stick's /boot/pax read off
# the stick's ESP by paxfat (the screen's symbols and the kernel line's expected digest come from the staged
# bytes themselves) and the head's paxfat.
sleg() {
  local name=$1 src=$2 used=$3 px87=${4:-} from=${5:-} keep=${6:-}
  local W=$L/legs/$name I=$L/legs/$name-inputs
  [ ! -e "$W" ] || { echo "$W exists"; return 2; }
  mkdir -p "$W/metal" "$I/build/disktools/bin"
  cp --sparse=always "$src" "$W/metal/stick.img"
  chmod 644 "$W/metal/stick.img"
  sha256sum "$W/metal/stick.img" | tee "$W/stick-at-start.sha256"
  [ "$(cut -d' ' -f1 "$W/stick-at-start.sha256")" = "$(sha256sum "$src" | cut -d' ' -f1)" ] || { echo "the copy differs from $src"; return 2; }
  cp "$L/sout/disktools/paxfat" "$I/build/disktools/bin/paxfat"
  local esp
  esp=$(python3 -I -c '
import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$src")
  "$L/sout/disktools/paxfat" --offset "$esp" cat "$src" /boot/pax > "$I/stick-kernel.elf"
  sha256sum "$I/stick-kernel.elf" | tee "$W/stick-kernel.sha256"
  printf '%s\n' "$I/stick-kernel.elf" > "$I/build/disktools/native.elf.path"
  local env=(-e PAX_CACHE=$L/cache -e PAX_BUILD=$L/sb -e TMPDIR=$L/tmp -e PAX_METAL_ACCEL=kvm -e SOURCE_DATE_EPOCH=1700000000
             -e PAX_METAL_TARGET=860 -e PAX_METAL_TARGET_SERIAL="$SERIAL" -e PAX_METAL_LISTED=1 -e PAX_METAL_USED=$used)
  [ -n "$px87" ] && env+=(-e PAX_METAL_PX87=$px87)
  [ -n "$from" ] && env+=(-e PAX_METAL_TARGET_FROM=$from)
  [ -n "$keep" ] && env+=(-e PAX_METAL_KEEP_TARGET=1)
  CTR_ENV="${env[*]} ${SLEG_EXTRA:-}" ctr "sleg-$name" localhost/px78-ubuntu:1 1 bash -c "time python3 -I ${VARIANT:-$L/variant}/metal-px92.py $L/stick $I $W/metal run"
}

legs_prep() {
  rm -rf "$L/variant"; mkdir -p "$L/variant"
  python3 -I "$L/lane/notes/px92/make-variant.py" "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant/metal-px92.py"
  diff -u "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant/metal-px92.py" > "$L/variant/metal-px92.diff" || true
  sha256sum "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant/metal-px92.py" "$L/lane/notes/px92/make-variant.py" | tee "$L/variant/sha256.txt"
  [ "$(cut -d' ' -f1 "$L/old/adb53141-read-1.sha256")" = ce86a7e699111eccc3a71570e7d19b04104c31358f8df7fa6200d899a1c280ac ]
  [ "$(sha256sum "$L/sout/pax-install-kasumi-$short.img" | cut -d' ' -f1)" = "$(cut -d' ' -f1 "$L/kasumi-build-read-1.sha256")" ]
}

# The dev stick (the coordinator's addition, 2026-11-04): the same recipe and head, the dev archive.
D=$L/sdev
sdevpay() {
  mkdir -p "$D"
  [ ! -e "$D/dev-live.cpio" ] || { echo "$D/dev-live.cpio exists"; return 2; }
  CTR_ENV= ctr sdevpay localhost/px75-ubuntu:2 0 python3 -I "$L/lane/notes/px92/live-payload-dev.py" "$L/stick" "$L/sout/dev.cpio" "$D/dev-live.cpio" "$D/live-payload.txt"
}

sdevstick() (
  set -euo pipefail
  cd "$L/stick"
  export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
  [ "$(command -v podman)" = "$P" ] || { echo "podman on PATH is not satoyama-env's"; exit 1; }
  . tools/lib.sh
  export SOURCE_DATE_EPOCH=$(cat "$L/sout/source-date-epoch")
  head=$(cat "$L/sout/commit"); [ "$head" = "$HEAD" ]
  elf=$L/sout/kernel/kmain_console.elf cpio=$D/dev-live.cpio conf=$PWD/boot/limine-usb.conf allow=$PWD/boot/install-targets
  load_limine_pin
  stick=$D/pax-install-dev-$short.img
  expected=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio"
    --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
    --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys"
    --expect "/boot/limine/limine.conf=$conf"
    --expect "/pax/install-targets=$allow")
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$stick" > "$D/usb-build.log"
  tools/check-usb "$stick" "${expected[@]}" | tee "$D/usb-check.log"
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$head" "$D/repeat.img" > "$D/usb-repeat.log"
  cmp "$stick" "$D/repeat.img"
  echo 'PASS second dev stick build byte-identical'
  rm "$D/repeat.img" "$D/repeat.img.inputs.json"
  for n in 1 2; do sha256sum "$stick" | tee "$D/stick-plain-read-$n.sha256"; done
  stat -c '%s' "$stick"
)

sdevline() (
  set -euo pipefail
  cd "$L/stick"
  export PAX_CACHE=$L/cache PAX_BUILD=$L/sb TMPDIR=$L/tmp
  . tools/lib.sh
  load_limine_pin
  plain=$D/pax-install-dev-$short.img k=$D/pax-install-kasumi-dev-$short.img
  rm -f "$k" "$k.tmp"
  cp --sparse=always "$plain" "$k.tmp"
  esp=$(python3 -I -c '
import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$k.tmp")
  "$L/sout/disktools/paxfat" --offset "$esp" append "$k.tmp" "$L/allow-line" /pax/install-targets
  "$L/sout/disktools/paxfat" --offset "$esp" cat "$k.tmp" /pax/install-targets > "$D/install-targets.on-stick"
  cmp "$D/install-targets.on-stick" "$L/install-targets.expected"
  echo "PASS /pax/install-targets on the dev copy: the release stick's file, one entry"
  tools/check-usb "$k.tmp" --expect "/boot/pax=$L/sout/kernel/kmain_console.elf" --expect "/boot/initramfs.cpio=$D/dev-live.cpio" \
    --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI" --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" \
    --expect "/boot/limine/limine.conf=$PWD/boot/limine-usb.conf" --expect "/pax/install-targets=$L/install-targets.expected" | tee "$D/kasumi-usb-check.log"
  mv "$k.tmp" "$k"
  chmod 444 "$k"
  for n in 1 2; do sha256sum "$k" | tee "$D/kasumi-dev-build-read-$n.sha256"; done
  stat -c '%s' "$k"
)

sdevcmp() {
  python3 -I "$L/lane/notes/px92/dev-compare.py" "$L/stick" "$L/sout/pax-install-kasumi-$short.img" "$D/pax-install-kasumi-dev-$short.img" \
    "$L/sout/release.cpio" "$D/dev-live.cpio" "$L/sout/disktools/paxfat" | tee "$D/compare.log"
  return "${PIPESTATUS[0]}"
}

devlegs_prep() {
  rm -rf "$L/variant-dev"; mkdir -p "$L/variant-dev"
  python3 -I "$L/lane/notes/px92/make-variant.py" "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant-dev/metal-px92.py"
  diff -u "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant-dev/metal-px92.py" > "$L/variant-dev/metal-px92.diff" || true
  sha256sum "$L/stick/tests/mpx6-install.d/metal.py" "$L/variant-dev/metal-px92.py" "$L/lane/notes/px92/make-variant.py" | tee "$L/variant-dev/sha256.txt"
  [ "$(sha256sum "$L/sout/pax-install-kasumi-$short.img" | cut -d' ' -f1)" = "$(cut -d' ' -f1 "$L/kasumi-build-read-1.sha256")" ]
  [ -f "$L/legs/mpx6/metal/target-after.img" ]
}

if [ "$SLOT" = NOLOCK-B ]; then
  # The maintainer's exception for the dev stick's take only (2026-11-04, through the coordinator): no satoyama
  # lock, slot B's CPUs, beside vc17 (which holds both locks and runs on 0-3,8-11); a sensor log beside the take.
  printf "%s px92 %s: the maintainer's exception, no locks, slot B's CPUs (%s), beside vc17\n" "$(ts)" "$CHUNK" "$CPUS"
  ( while kill -0 $$ 2>/dev/null; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E '^(Package id 0|Core [0-9]+):' | awk '{printf "%s%s %s; ", $1, $2, $3}'; echo; sleep 30; done ) > "$L/logs/sensors-$CHUNK.log" 2>&1 &
elif [ "$SLOT" = AB ] || [ "$SLOT" = ABA ]; then
  # The maintainer's ruling (2026-11-04): one heavy job at a time on satoyama, both locks, A outside then B.
  exec 8>/home/mfwolffe/lanes/satoyama-A.lock
  printf '%s px92 %s: waiting on satoyama-A.lock (one flock -w 21600), then B\n' "$(ts)" "$CHUNK"
  flock -w 21600 8 || { echo "$(ts) the A lock wait timed out"; exit 4; }
  printf '%s px92 %s: satoyama-A.lock acquired; waiting on satoyama-B.lock\n' "$(ts)" "$CHUNK"
  exec 9>/home/mfwolffe/lanes/satoyama-B.lock
  flock -w 21600 9 || { echo "$(ts) the B lock wait timed out"; exit 4; }
  printf '%s px92 %s: both satoyama locks acquired (CPUs %s)\n' "$(ts)" "$CHUNK" "$CPUS"
else
  exec 9>"/home/mfwolffe/lanes/satoyama-$SLOT.lock"
  printf '%s px92 %s: waiting on satoyama-%s.lock (one flock -w 21600)\n' "$(ts)" "$CHUNK" "$SLOT"
  flock -w 21600 9 || { echo "$(ts) the lock wait timed out"; exit 4; }
  printf '%s px92 %s: satoyama-%s.lock acquired (CPUs %s)\n' "$(ts)" "$CHUNK" "$SLOT" "$CPUS"
fi
case $CHUNK in
  build)
    [ ! -e "$L/sout" ] || { echo "$L/sout exists"; exit 3; }
    step sbuild sbuild
    step sstick sstick
    step sline sline
    ;;
  legs)
    k=$L/sout/pax-install-kasumi-$short.img
    step legs-prep legs_prep
    step sleg-mpx6 sleg mpx6 "$L/old/pax-install-kasumi-adb53141.img" fat32 "" "" keep
    step sleg-pax sleg pax "$k" pax "$HEAD" "$L/legs/mpx6/metal/target-after.img"
    step sleg-fat32 sleg fat32 "$k" fat32 "$HEAD"
    step sleg-ext4 sleg ext4 "$k" ext4 "$HEAD"
    ;;
  dev)
    step sdevpay sdevpay
    step sdevstick sdevstick
    step sdevline sdevline
    step sdevcmp sdevcmp
    step devlegs-prep devlegs_prep
    VARIANT=$L/variant-dev step sleg-rel sleg rel "$L/sout/pax-install-kasumi-$short.img" pax "" "$L/legs/mpx6/metal/target-after.img" keep
    VARIANT=$L/variant-dev SLEG_EXTRA="-e PAX_METAL_MEM=4096M -e PAX_METAL_DEV=1" step sleg-dev sleg dev "$D/pax-install-kasumi-dev-$short.img" pax "$HEAD" "$L/legs/rel/metal/target-after.img"
    ;;
  *) echo "CHUNK is build, legs or dev"; exit 2 ;;
esac
[ "$SLOT" = NOLOCK-B ] || { flock -u 9; exec 9>&-; }
{ [ "$SLOT" = AB ] || [ "$SLOT" = ABA ]; } && { flock -u 8; exec 8>&-; }
printf '%s px92 %s: satoyama-%s lock(s) RELEASED\n' "$(ts)" "$CHUNK" "$SLOT"
printf '%s CHUNK %s DONE %s\n' "$(ts)" "$CHUNK" "$short"
