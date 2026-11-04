#!/usr/bin/env bash
# px93 on satoyama: one chunk per run, both locks (A outside, then B), slot A's CPUs 0-3,8-11 for every
# step (taskset inside each container), at most 2 h a hold. A step's END line carries its exit; a red
# step stops the chunk, but in the `red` chunk, where each step must fail by name.
#   job.sh red   SHA   the tests-only head: fat.py's replace row, and the leg's U1, U2, U0 and U8 with the
#                      staged 9c88ec8a stick as both sticks (its pax-install has no --upgrade)
#   job.sh units SHA   the head's installer and kernel compiled, its paxfat and fat.py; a Linux build of the
#                      env_args() program (U5's twin)
#   job.sh build SHA   tools/mkdistribution at SHA, the dev variant's live payload, the upgrade stick
#                      (tools/mkdisk --usb, tools/check-usb, a second build byte-identical, the 860's line,
#                      read-only, sha256 twice)
#   job.sh legs  SHA   tests/mpx6-install.d/upgrade.py, every row, the staged old stick and the new stick
set -uo pipefail
L=/home/mfwolffe/lanes/px93
CHUNK=$1 SHA=$2
short=${SHA:0:8}
CPUS=0-3,8-11
P=/home/mfwolffe/lanes/satoyama-env/bin/podman
export PATH=/home/mfwolffe/lanes/satoyama-env/bin:$PATH TMPDIR=$L/tmp
mkdir -p "$L/tmp" "$L/slogs" "$L/runs"
printf '%s\n' "$$" > "$L/$CHUNK-$short.pid"
taskset -cp "$CPUS" $$ > /dev/null
ts() { date -u +%FT%TZ; }
RED=0
step() {
  local n=$1; shift
  printf '%s START %s\n' "$(ts)" "$n"
  "$@"; local rc=$?
  printf '%s END %s exit=%s\n' "$(ts)" "$n" "$rc"
  echo "$rc" > "$L/runs/$CHUNK-$short-$n.exit"
  if [ "$RED" = 1 ]; then return 0; fi
  [ "$rc" = 0 ] || { echo "CHUNK $CHUNK STOPPED at $n"; exit "$rc"; }
}
CO=$L/co-$short
checkout() {
  [ -d "$CO" ] || git -C "$L/repo" worktree add -f "$CO" "$SHA" > /dev/null 2>&1 || git -c commit.gpgsign=false -C "$L/repo" worktree add -f "$CO" "$SHA"
  [ "$(git -C "$CO" rev-parse HEAD)" = "$SHA" ] || { echo "the checkout is not at $SHA"; exit 3; }
  [ -z "$(git -C "$CO" status --porcelain --untracked-files=no)" ] || { echo "the checkout is dirty"; exit 3; }
}
ctr() { # NAME IMAGE KVM CMD...
  local name=$1 img=$2 kvm=$3; shift 3
  local dev=(); [ "$kvm" = 1 ] && dev=(--device /dev/kvm)
  "$P" run --rm --name "px93-$name-$short" --memory 12g --pids-limit 16384 --ulimit nproc=32768:32768 --ulimit core=0:0 "${dev[@]}" \
    -v "$L:$L" -w "$CO" -e TMPDIR="$L/tmp" -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e 'GIT_CONFIG_VALUE_0=*' \
    ${CTR_ENV:-} "$img" taskset -c "$CPUS" "$@"
}
SERIAL=$(sed -n 's/^model=Samsung SSD 860 serial=//p' /home/mfwolffe/lanes/px92/allow-line)
[ -n "$SERIAL" ] || { echo "no serial"; exit 3; }
OLD=$L/old/pax-install-kasumi-9c88ec8a.img

fat_row() { # OUT: build paxfat at the checkout, then fat.py against the oracles
  local out=$L/runs/$1
  rm -rf "$out"; mkdir -p "$out"
  ctr fatbuild localhost/px75-ubuntu:2 0 bash -c "export PAX_CACHE=$L/cache PAX_BUILD=$L/pb-$short CARGO_INCREMENTAL=0; tools/mkdisktools $out/bin paxfat" > "$out/build.log" 2>&1 || { tail -30 "$out/build.log"; return 2; }
  ctr fatrow localhost/px78-ubuntu:1 0 python3 -I tests/mpx6-disktools.d/fat.py "$out/bin/paxfat" "$out/work" > "$out/fat.log" 2>&1
  local rc=$?
  grep -E '^PASS|Error|assert' "$out/fat.log" | tail -20
  tail -5 "$out/fat.log"
  return $rc
}
leg() { # NAME NEWSTICK ROWS [LINUX]
  local w=$L/runs/leg-$1-$short
  rm -rf "$w"; mkdir -p "$w"
  CTR_ENV="-e PAX_UPGRADE_SERIAL=$SERIAL -e PAX_UPGRADE_LINUX=${4:-} -e PYTHONUNBUFFERED=1" \
    ctr "leg-$1" localhost/px78-ubuntu:1 1 python3 -I tests/mpx6-install.d/upgrade.py "$CO" "$w" "$OLD" "$2" "$3" 2>&1 | sed -u "s/$SERIAL/<kasumi-serial>/g" | tee "$w/leg.log"
  return "${PIPESTATUS[0]}"
}
red_expect() { # LOG NEEDLE: a red step's FAIL line, by name
  grep -m1 '^FAIL' "$1" || { echo "no FAIL line in $1"; return 1; }
  grep -q "$2" "$1" && echo "RED BY NAME: $2"
}
units_args() {
  local out=$L/runs/args-$short
  rm -rf "$out"; mkdir -p "$out"
  printf 'fn main() {\n    for a in env_args() { print("arg: {a}") }\n}\n' > "$out/main.lu"
  ctr argsbuild localhost/px75-ubuntu:2 0 bash -c "export PAX_CACHE=$L/cache; w=\$(tools/fetch-wolf); cd $out && WOLF_STD=\$(dirname \$w)/std \$w build --no-cache main.lu -o args && ./args one 'two words' > linux-args.out; echo rc=\$?"
  od -c "$out/linux-args.out" | head
  [ -s "$out/linux-args.out" ]
}

sbuild() {
  local out=$L/sout-$short
  [ ! -e "$out" ] || { echo "$out exists"; return 2; }
  cat > "$L/sbuild-inside-$short.sh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd $CO
export PAX_CACHE=$L/cache PAX_BUILD=$L/sb-$short TMPDIR=$L/tmp PAX_LOPE_REPO=$L/inputs/lope-local CARGO_INCREMENTAL=0
export PAX_WOLF=\$(tools/fetch-wolf)
[ "\$(git rev-parse HEAD)" = $SHA ]
tools/mkdistribution "$L/inputs/base-dev.cpio" "$L/build/inputs" "$out" > "$L/slogs/distribution-$short.log" 2>&1
grep -E '^(I0|I1|R0|image|distribution|payload)' "$L/slogs/distribution-$short.log" || true
python3 -I "$CO/notes/px93/satoyama/live-payload.py" "$CO" "$out" dev
for n in 1 2; do sha256sum "$L/cache/wolf-0.2.35-4cc4045bbbb605c07835bc4f32685953c784eeef4cd3139a48b457dfc90dad1a.tar.gz"; done | tee "$out/archive-reads.txt"
for n in 1 2; do sha256sum "$L/inputs/limine-download/limine-binary.tar.gz"; done | tee "$out/limine-reads.txt"
EOF
  ctr sbuild localhost/px75-ubuntu:2 0 bash "$L/sbuild-inside-$short.sh"
}
sstick() (
  set -euo pipefail
  cd "$CO"
  local out=$L/sout-$short
  export PAX_CACHE=$L/cache PAX_BUILD=$L/sb-$short TMPDIR=$L/tmp PAX_ENGINE=podman PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
  . tools/lib.sh
  export SOURCE_DATE_EPOCH=$(cat "$out/source-date-epoch")
  [ "$(cat "$out/commit")" = "$SHA" ]
  elf=$out/kernel/kmain_console.elf cpio=$out/dev.cpio conf=$PWD/boot/limine-usb.conf allow=$PWD/boot/install-targets
  load_limine_pin
  stick=$out/pax-upgrade-$short.img
  exp=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio" --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
       --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" --expect "/boot/limine/limine.conf=$conf" --expect "/pax/install-targets=$allow")
  python3 -I tests/usb-tools
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$SHA" "$stick" > "$L/slogs/usb-build-$short.log"
  tools/check-usb "$stick" "${exp[@]}" | tee "$L/slogs/usb-check-$short.log"
  tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$SHA" "$out/repeat.img" > /dev/null
  cmp "$stick" "$out/repeat.img"; echo 'PASS second stick build byte-identical'
  rm -f "$out/repeat.img" "$out/repeat.img.inputs.json"
  sha256sum "$stick" | tee "$out/stick-plain-read-1.sha256"
  # The 860's line, on a copy, by the stick's own paxfat; read back; check-usb again; read-only.
  k=$out/pax-upgrade-kasumi-$short.img
  rm -f "$k" "$k.tmp"; cp --sparse=always "$stick" "$k.tmp"
  esp=$(python3 -I -c 'import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$k.tmp")
  "$out/disktools/paxfat" --offset "$esp" append "$k.tmp" /home/mfwolffe/lanes/px92/allow-line /pax/install-targets
  "$out/disktools/paxfat" --offset "$esp" cat "$k.tmp" /pax/install-targets > "$out/install-targets.on-stick"
  cat boot/install-targets /home/mfwolffe/lanes/px92/allow-line > "$out/install-targets.expected"
  cmp "$out/install-targets.on-stick" "$out/install-targets.expected"
  tools/check-usb "$k.tmp" "${exp[@]:0:10}" --expect "/pax/install-targets=$out/install-targets.expected" | tee "$L/slogs/kasumi-usb-check-$short.log"
  mv "$k.tmp" "$k"; chmod 444 "$k"
  for n in 1 2; do sha256sum "$k" | tee "$out/kasumi-build-read-$n.sha256"; done
  stat -c '%s' "$k"
)

exec 8>/home/mfwolffe/lanes/satoyama-A.lock
printf '%s px93 %s %s: waiting on satoyama-A.lock (flock -w 21600), then B\n' "$(ts)" "$CHUNK" "$short"
flock -w 21600 8 || { echo "$(ts) the A lock wait timed out"; exit 4; }
printf '%s px93 %s: satoyama-A.lock acquired; waiting on satoyama-B.lock\n' "$(ts)" "$CHUNK"
exec 9>/home/mfwolffe/lanes/satoyama-B.lock
flock -w 21600 9 || { echo "$(ts) the B lock wait timed out"; exit 4; }
printf '%s px93 %s: both satoyama locks acquired (CPUs %s)\n' "$(ts)" "$CHUNK" "$CPUS"
sensors > "$L/runs/$CHUNK-$short-sensors-start.txt" 2>&1 || true
checkout
case $CHUNK in
  red)
    RED=1
    step red-fat fat_row "fat-red-$short"
    red_expect "$L/runs/fat-red-$short/fat.log" "replace" ; echo "red-fat-named=$?"
    step red-leg leg red "$OLD" U1,U2,U0,U8
    red_expect "$L/runs/leg-red-$short/leg.log" "FAIL U8-wrong-serial: /^usage: pax-install/" ; echo "red-leg-named=$?"
    ;;
  units)
    step units-install ctr instbuild localhost/px75-ubuntu:2 0 bash -c "export PAX_CACHE=$L/cache PAX_BUILD=$L/pb-$short; tools/mkinstall $L/runs/inst-$short"
    step units-kernel ctr kbuild localhost/px75-ubuntu:2 0 bash -c "export PAX_CACHE=$L/cache PAX_BUILD=$L/pb-$short; tools/fetch-limine >/dev/null; tools/build-kernel --release --src kernel/kmain_console.lu $L/runs/kernel-$short"
    step units-fat fat_row "fat-$short"
    step units-args units_args
    ;;
  build)
    step sbuild sbuild
    step sstick sstick
    ;;
  legs)
    step legs leg all "$L/sout-$short/pax-upgrade-kasumi-$short.img" U1,U2,U0,U8,U3,U4,U5,U6,U7 "$L/runs/args-$short/linux-args.out"
    ;;
  *) echo "CHUNK is red, units, build or legs"; exit 2 ;;
esac
sensors > "$L/runs/$CHUNK-$short-sensors-end.txt" 2>&1 || true
flock -u 9; exec 9>&-; flock -u 8; exec 8>&-
printf '%s px93 %s: both satoyama locks RELEASED\n' "$(ts)" "$CHUNK"
printf '%s CHUNK %s DONE %s\n' "$(ts)" "$CHUNK" "$short"
