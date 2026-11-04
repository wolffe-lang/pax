#!/usr/bin/env bash
# px92: the dev stick again at the branch head (user/wolf.pin v0.2.36, wolf-lang#962), by the same recipe as
# pax-install-kasumi-dev-9c88ec8a.img: tools/mkdistribution with px86's inputs plus INPUTS/wolf and
# INPUTS/wolf-std (tools/mkwolf and mkwolf-std at the pin), px86's live payload on the dev archive, tools/mkdisk
# --usb, check-usb, a second build byte-identical, the 860's line, sha256 twice; then one leg: the stick over
# the 860 as it is today (adb53141's install, then pax-install-kasumi-9c88ec8a.img's: legs/rel's kept target),
# with px87's rows and the dev rows D1-D4. The maintainer's exception: no locks, slot B's CPUs 4-7,12-15,
# 12 GiB, a sensor log beside the take.
#   dev2.sh HEAD SERIAL
set -uo pipefail
L=/home/mfwolffe/lanes/px92 HEAD=$1 SERIAL=$2
short=${HEAD:0:8} S=$L/stick2 O=$L/sout2 D=$L/sdev2 IN=$L/build/inputs2 CPUS=4-7,12-15
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
export PATH=/home/mfwolffe/lanes/satoyama-env/bin:$PATH TMPDIR=$L/tmp
printf '%s\n' "$$" > "$L/dev2.pid"
taskset -cp "$CPUS" $$ > /dev/null
ts() { date -u +%FT%TZ; }
step() { local n=$1; shift; printf '%s START %s\n' "$(ts)" "$n"; "$@"; local rc=$?; printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"; echo $rc > "$L/dev2-$n.exit"; [ $rc = 0 ] || { echo "DEV2 STOPPED at $n"; exit $rc; }; }
[ "$(git -C "$S" rev-parse HEAD)" = "$HEAD" ] || { echo "stick2 is not at $HEAD"; exit 3; }
[ -z "$(git -C "$S" status --porcelain --untracked-files=no)" ] || { echo "stick2 dirty"; exit 3; }
printf "%s px92 dev2: the maintainer's exception, no locks, slot B's CPUs (%s), beside vc17; head %s\n" "$(ts)" "$CPUS" "$HEAD"
( while kill -0 $$ 2>/dev/null; do printf '%s ' "$(ts)"; sensors 2>/dev/null | grep -E '^(Core [0-9]+):' | awk '{printf "%s%s %s; ", $1, $2, $3}'; echo; sleep 30; done ) > "$L/logs/sensors-dev2.log" 2>&1 &
ctr() {
  local name=$1 img=$2 kvm=$3; shift 3
  local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  "$P" run --rm --name "px92-$name" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$S" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    ${CTR_ENV:-} "$img" taskset -c "$CPUS" "$@"
}
esp_of() { python3 -I -c '
import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$1"; }

d2inputs() (
  set -euo pipefail
  [ ! -e "$IN" ] && [ ! -e "$O" ] && [ ! -e "$D" ]
  cp -al "$L/build/inputs" "$IN"
  cp -a "$L/winputs/wolf" "$IN/wolf"
  cp -a "$L/winputs/wolf-std" "$IN/wolf-std"
  while read -r name digest size; do
    [ "$(sha256sum "$IN/wolf/$name" | cut -d' ' -f1)" = "$digest" ] && [ "$(stat -c %s "$IN/wolf/$name")" = "$size" ]
    echo "PASS INPUTS/wolf/$name = user/wolf.sums ($digest)"
  done < "$S/user/wolf.sums"
  [ "$(cat "$IN/wolf-std/STD-REV")" = "$(sed -n 's/^WOLF_STD_REV=//p' "$S/user/wolf.pin")" ]
  echo "PASS INPUTS/wolf-std/STD-REV = user/wolf.pin's WOLF_STD_REV ($(cat "$IN/wolf-std/STD-REV"))"
)

d2build() {
  mkdir -p "$D"
  cat > "$D/build-inside.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd $S
export PAX_CACHE=$L/cache PAX_BUILD=$L/sb2 TMPDIR=$L/tmp PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
[ "\$(git rev-parse HEAD)" = $HEAD ]
[ -z "\$(git status --porcelain --untracked-files=no)" ]
tools/mkdistribution "$L/inputs/base-dev.cpio" "$IN" "$O" > "$D/distribution.log" 2>&1
grep -E '^(I0|I1)' "$D/distribution.log" || true
python3 -I "$L/lane/notes/px92/live-payload-dev.py" "$S" "$O/dev.cpio" "$D/dev-live.cpio" "$D/live-payload.txt"
EOF
  CTR_ENV= ctr d2build localhost/px75-ubuntu:2 0 bash "$D/build-inside.sh"
}

d2stick() (
  set -euo pipefail
  cd "$S"
  export PAX_CACHE=$L/cache PAX_BUILD=$L/sb2 TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
  [ "$(command -v podman)" = "$P" ]
  . tools/lib.sh
  export SOURCE_DATE_EPOCH=$(cat "$O/source-date-epoch")
  [ "$(cat "$O/commit")" = "$HEAD" ]
  elf=$O/kernel/kmain_console.elf cpio=$D/dev-live.cpio conf=$PWD/boot/limine-usb.conf allow=$PWD/boot/install-targets
  load_limine_pin
  stick=$D/pax-install-dev-$short.img
  exp=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio" --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
       --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" --expect "/boot/limine/limine.conf=$conf"
       --expect "/pax/install-targets=$allow")
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$HEAD" "$stick" > "$D/usb-build.log"
  tools/check-usb "$stick" "${exp[@]}" | tee "$D/usb-check.log"
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$HEAD" "$D/repeat.img" > "$D/usb-repeat.log"
  cmp "$stick" "$D/repeat.img"; echo 'PASS second dev stick build byte-identical'
  rm "$D/repeat.img" "$D/repeat.img.inputs.json"
  for n in 1 2; do sha256sum "$stick" | tee "$D/stick-plain-read-$n.sha256"; done
  stat -c '%s' "$stick"
  k=$D/pax-install-kasumi-dev-$short.img
  cp --sparse=always "$stick" "$k.tmp"
  esp=$(esp_of "$k.tmp")
  printf 'model=Samsung SSD 860 serial=%s\n' "$SERIAL" > "$D/allow-line"
  "$O/disktools/paxfat" --offset "$esp" append "$k.tmp" "$D/allow-line" /pax/install-targets
  "$O/disktools/paxfat" --offset "$esp" cat "$k.tmp" /pax/install-targets > "$D/install-targets.on-stick"
  cat boot/install-targets "$D/allow-line" > "$D/install-targets.expected"
  cmp "$D/install-targets.on-stick" "$D/install-targets.expected"
  echo "PASS /pax/install-targets on the copy: boot/install-targets plus the one line"
  tools/check-usb "$k.tmp" "${exp[@]:0:10}" --expect "/pax/install-targets=$D/install-targets.expected" | tee "$D/kasumi-usb-check.log"
  mv "$k.tmp" "$k"; chmod 444 "$k"
  for n in 1 2; do sha256sum "$k" | tee "$D/kasumi-dev-build-read-$n.sha256"; done
  stat -c '%s' "$k"
)

d2cmp() {
  # Against the v0.2.35 dev stick: informational (the kernel names its own head, so /boot/pax differs by design).
  python3 -I "$L/lane/notes/px92/dev-compare.py" "$S" "$L/sdev/pax-install-kasumi-dev-9c88ec8a.img" "$D/pax-install-kasumi-dev-$short.img" \
    "$L/sdev/dev-live.cpio" "$D/dev-live.cpio" "$O/disktools/paxfat" > "$D/compare-0235.log" 2>&1
  echo "dev-compare exit $? (informational)"; grep -vE '^  \+ usr/share' "$D/compare-0235.log" | head -40
}

d2leg() {
  local W=$L/legs/dev2 I=$L/legs/dev2-inputs k=$D/pax-install-kasumi-dev-$short.img
  [ ! -e "$W" ] || { echo "$W exists"; return 2; }
  rm -rf "$L/variant-dev2"; mkdir -p "$L/variant-dev2" "$W/metal" "$I/build/disktools/bin"
  python3 -I "$L/lane/notes/px92/make-variant.py" "$S/tests/mpx6-install.d/metal.py" "$L/variant-dev2/metal-px92.py"
  diff -u "$S/tests/mpx6-install.d/metal.py" "$L/variant-dev2/metal-px92.py" > "$L/variant-dev2/metal-px92.diff"
  cp --sparse=always "$k" "$W/metal/stick.img"; chmod 644 "$W/metal/stick.img"
  sha256sum "$W/metal/stick.img" | tee "$W/stick-at-start.sha256"
  [ "$(cut -d' ' -f1 "$W/stick-at-start.sha256")" = "$(cut -d' ' -f1 "$D/kasumi-dev-build-read-1.sha256")" ] || return 2
  cp "$O/disktools/paxfat" "$I/build/disktools/bin/paxfat"
  "$O/disktools/paxfat" --offset "$(esp_of "$k")" cat "$k" /boot/pax > "$I/stick-kernel.elf"
  printf '%s\n' "$I/stick-kernel.elf" > "$I/build/disktools/native.elf.path"
  [ -f "$L/legs/rel/metal/target-after.img" ] || return 2
  CTR_ENV="-e PAX_CACHE=$L/cache -e PAX_BUILD=$L/sb2 -e TMPDIR=$L/tmp -e PAX_METAL_ACCEL=kvm -e SOURCE_DATE_EPOCH=1700000000 -e PAX_METAL_TARGET=860 -e PAX_METAL_TARGET_SERIAL=$SERIAL -e PAX_METAL_LISTED=1 -e PAX_METAL_USED=pax -e PAX_METAL_TARGET_FROM=$L/legs/rel/metal/target-after.img -e PAX_METAL_PX87=$HEAD -e PAX_METAL_MEM=4096M -e PAX_METAL_DEV=1" \
    ctr sleg-dev2 localhost/px78-ubuntu:1 1 bash -c "time python3 -I $L/variant-dev2/metal-px92.py $S $I $W/metal run"
}

step d2inputs d2inputs
step d2build d2build
step d2stick d2stick
step d2cmp d2cmp
step d2leg d2leg
printf '%s DEV2 DONE %s\n' "$(ts)" "$short"
