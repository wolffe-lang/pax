#!/usr/bin/env bash
# notes/px106/rig/witness.sh CHUNK SHA [CAPTURES_SHA] — the upgrade witness
# (tests/mpx6-install.d/upgrade.py) at SHA, px93's way, one chunk a call (lib.sh's host file).
# px93's built inputs, its two sticks and its allow line are COPIED by value into $L/u by `prep`
# (never moved, never written there); `auth/` is tools/mkauth's at SHA. Run from a checkout of SHA.
#   prep           (light) copy px93's inputs, sticks and allow line; read the sticks twice
#   build          (heavy) auth inputs, tools/mkdistribution, the live payload, the upgrade stick
#   legs-x|legs-d|legs-a   (heavy) one of upgrade.py's three sections against SHA's stick
#   compare        (light) U14's PAX captures (legs-x's at CAPTURES_SHA, default SHA) against
#                  tests/mpx6-install.d/sudo-linux.sh in the Ubuntu container, by sudo-compare.py
# A step's END line carries its exit; a red step stops the chunk.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
CHUNK=$1 SHA=$2 CAP=${3:-$2}
here=$(cd "$(dirname "$0")" && pwd)
. "$here/lib.sh"
checkout_ok "$SHA" || exit 3
cd "$CO"
short=${SHA:0:8}
U=$L/u
OLD=$U/old/stick-9c88ec8a.img
DEV=$U/old/stick-dev-8b4e98ae.img
IN=$U/inputs-$short
fail() { echo "CHUNK $CHUNK STOPPED at $1"; exit "$2"; }
prep() (
    set -euo pipefail
    : "${INPUTS_SRC:?}" "${SRC_DIR:?}" "${STICK_A:?}" "${STICK_D:?}" "${STICK_A_READ:?}" "${STICK_D_READ:?}" "${ALLOW_SRC:?}"
    [ ! -e "$U/inputs" ] || { echo "$U/inputs exists"; exit 2; }
    mkdir -p "$U/src" "$U/old"
    cp -a "$INPUTS_SRC" "$U/inputs.part" && mv "$U/inputs.part" "$U/inputs"
    cp -a "$SRC_DIR/base-dev.cpio" "$SRC_DIR/limine-download" "$SRC_DIR/lope-local" "$U/src/"
    cp --sparse=always "$STICK_A" "$OLD"; cp --sparse=always "$STICK_D" "$DEV"; chmod 444 "$OLD" "$DEV"
    cp "$ALLOW_SRC" "$U/allow-line"
    for n in 1 2; do
        for s in A D; do
            f=$OLD r=$STICK_A_READ; [ $s = A ] || { f=$DEV r=$STICK_D_READ; }
            want=$(cut -d' ' -f1 "$r"); got=$(sha256sum "$f" | cut -d' ' -f1)
            echo "read $n $(basename "$f") $got"; [ "$want" = "$got" ] || { echo "MISMATCH $f: px93 read $want"; exit 3; }
        done
    done
    (cd "$INPUTS_SRC" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$U/inputs-px93.sums"
    (cd "$U/inputs" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$U/inputs-copy.sums"
    cmp "$U/inputs-px93.sums" "$U/inputs-copy.sums" && echo "inputs copied: $(wc -l < "$U/inputs-copy.sums") files byte-identical"
)
auth_inputs() (
    set -euo pipefail
    rm -rf "$IN"; cp -al "$U/inputs" "$IN"
    CTR_ENV="-e PAX_BUILD=$L/ub-$short" ctr 0 localhost/px75-ubuntu:2 tools/mkauth "$IN/auth"
    cat "$IN/auth/sums.txt"
)
sbuild() (
    set -euo pipefail
    out=$U/sout-$short
    rm -rf "$out"
    CTR_ENV="-e PAX_BUILD=$L/ub-$short -e PAX_LOPE_REPO=$U/src/lope-local -e CARGO_INCREMENTAL=0" ctr 0 localhost/px75-ubuntu:2 bash -c \
        "export PAX_WOLF=\$(tools/fetch-wolf) && tools/mkdistribution '$U/src/base-dev.cpio' '$IN' '$out' > '$L/runs/distribution-$short.log' 2>&1 || { tail -40 '$L/runs/distribution-$short.log'; exit 1; }
         grep -E '^(I0|I1|R0|image|distribution|payload)' '$L/runs/distribution-$short.log' || true
         python3 -I notes/px93/satoyama/live-payload.py '$CO' '$out' dev"
)
sstick() (
    set -euo pipefail
    out=$U/sout-$short
    export PAX_BUILD=$L/ub-$short PAX_ENGINE=$P PAX_E2FS_IMAGE=localhost/px75-ubuntu:2
    . tools/lib.sh
    SOURCE_DATE_EPOCH=$(cat "$out/source-date-epoch"); export SOURCE_DATE_EPOCH
    [ "$(cat "$out/commit")" = "$SHA" ]
    elf=$out/kernel/kmain_console.elf cpio=$out/dev.cpio conf=$PWD/boot/limine-usb.conf allow=$PWD/boot/install-targets
    load_limine_pin
    stick=$out/pax-upgrade-$short.img
    exp=(--expect "/boot/pax=$elf" --expect "/boot/initramfs.cpio=$cpio" --expect "/EFI/BOOT/BOOTX64.EFI=$LIMINE_DIR/BOOTX64.EFI"
         --expect "/boot/limine/limine-bios.sys=$LIMINE_DIR/limine-bios.sys" --expect "/boot/limine/limine.conf=$conf" --expect "/pax/install-targets=$allow")
    python3 -I tests/usb-tools
    tools/mkdisk --usb --kernel "$elf" --initramfs "$cpio" --conf "$conf" --kernel-commit "$SHA" "$stick" > "$L/runs/usb-build-$short.log"
    tools/check-usb "$stick" "${exp[@]}"
    k=$out/pax-upgrade-860-$short.img
    rm -f "$k" "$k.part"; cp --sparse=always "$stick" "$k.part"
    esp=$(python3 -I -c 'import struct,sys
f=open(sys.argv[1],"rb"); f.seek(512); h=f.read(92); a=struct.unpack_from("<Q",h,72)[0]; f.seek(a*512); e=f.read(128)
print(struct.unpack_from("<Q",e,32)[0]*512)' "$k.part")
    "$out/disktools/paxfat" --offset "$esp" append "$k.part" "$U/allow-line" /pax/install-targets
    "$out/disktools/paxfat" --offset "$esp" cat "$k.part" /pax/install-targets > "$out/install-targets.on-stick"
    cat boot/install-targets "$U/allow-line" > "$out/install-targets.expected"
    cmp "$out/install-targets.on-stick" "$out/install-targets.expected"
    tools/check-usb "$k.part" "${exp[@]:0:10}" --expect "/pax/install-targets=$out/install-targets.expected"
    mv "$k.part" "$k"; chmod 444 "$k"
    for n in 1 2; do sha256sum "$k"; done
)
leg() { # NAME ROWS
    local w=$L/runs/leg-$1-$short serial
    serial=$(sed -n 's/^model=Samsung SSD 860 serial=//p' "$U/allow-line")
    [ -n "$serial" ] || { echo "no serial in $U/allow-line"; return 3; }
    rm -rf "$w"; mkdir -p "$w"
    CTR_ENV="-e PAX_UPGRADE_SERIAL=$serial -e PAX_UPGRADE_DEV_STICK=$DEV -e PYTHONUNBUFFERED=1" \
        ctr 1 localhost/px78-ubuntu:1 python3 -I tests/mpx6-install.d/upgrade.py "$CO" "$w" "$OLD" "$U/sout-$short/pax-upgrade-860-$short.img" "$2" 2>&1 \
        | sed -u "s/$serial/<the-860-serial>/g" | tee "$w/leg.log" | grep -aE '^(PASS|FAIL|Traceback)|Error'
    return "${PIPESTATUS[0]}"
}
compare() ( # light: the light helper's CPUs and memory
    set -uo pipefail
    px=$L/runs/leg-x-${CAP:0:8}/session-pax lin=$L/runs/sudo-linux-$short
    [ -d "$px" ] || { echo "no PAX captures at $px"; exit 2; }
    rm -rf "$lin"; mkdir -p "$lin"
    local mnt=(-v "$L:$L"); [ "$R" = "$L" ] || mnt+=(-v "$R:$R")
    "$P" run --rm --network none --memory "$LIGHT_MEM" "${mnt[@]}" -w "$CO" localhost/px103-sudo:1 taskset -c "$LIGHT_CPUS" \
        bash "$CO/tests/mpx6-install.d/sudo-linux.sh" "$CO/tests/mpx6-install.d/sudo-session.txt" "$CO/user/sudo/sudoers" "$lin" < /dev/null || exit 3
    python3 -I "$CO/tests/mpx6-install.d/sudo-compare.py" "$px" "$lin"
)
case $CHUNK in
    prep)
        # The light helper runs this script again for the chunk, in a child of its own.
        if [ -z "${LIGHT_CPUS:-}" ]; then exec "$LIGHT" "$here/witness.sh" prep "$SHA"; fi
        step prep prep || fail prep $? ;;
    build)
        take || exit 4
        step auth-inputs auth_inputs || fail auth-inputs $?
        step sbuild sbuild || fail sbuild $?
        step sstick sstick || fail sstick $? ;;
    legs-x) take || exit 4; step legs-x leg x U9,U13f,U14,U10,U11,U12,U15 || fail legs-x $? ;;
    legs-d) take || exit 4; step legs-d leg d U1d,U2d,U3d,U4d,U6d,U13d || fail legs-d $? ;;
    legs-a) take || exit 4; step legs-a leg a U1,U2,U0,U8,U3,U4,U6,U7,U13a || fail legs-a $? ;;
    compare)
        # The light helper runs this script's compare in a child shell of its own.
        if [ -z "${LIGHT_CPUS:-}" ]; then exec "$LIGHT" "$here/witness.sh" compare "$SHA" "$CAP"; fi
        step sudo-compare compare || fail sudo-compare $? ;;
    *) echo "unknown chunk $CHUNK"; exit 2 ;;
esac
