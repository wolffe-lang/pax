#!/usr/bin/env bash
# notes/px128/rig/step.sh WHAT [ARGS…] — one step of px128's local records, run by the recorder
# (gauntlet-record.sh --steps, a manifest beside this file) from a clean checkout of the commit under
# test, under take.sh's locks. lib.sh (GAUNTLET_RIG_DIR's) gives the host's facts and `ctr`.
#   preflight       the host has what the steps use: KVM, the engine, the image, the image directories
#   ci-plan         tests/ci-plan
#   census          tests/census
#   fetch-retry     tests/fetch-retry-selftest
#   mkligature      tools/mkligature, its two checkouts' digest held to user/ligature.pin's
#   rows NAME       tests/distribution-ligature on a fresh copy of the image directory NAME
#   assemble NAME   tools/distribution-root's dev archive from NAME's inputs and identity (NAME/inputs,
#                   NAME/base.cpio), then tests/distribution on it
# A red row is said at column 0 as `FAIL ROW …` (the judge's own lines; `lift` turns tests/distribution's
# assertion and mkligature's refusal into one) so a plant's row is named in its record. The step's exit
# is the suite's.
set -uo pipefail
trap 'exit 143' TERM; trap 'exit 130' INT; trap 'exit 129' HUP
# shellcheck disable=SC1091
. "${GAUNTLET_RIG_DIR:?run by the recorder}/lib.sh"
cd "$CO" || exit 2
img=localhost/px75-ubuntu:2
lift() { "$@" 2>&1 | sed -u -E 's/^AssertionError: (image-[A-Za-z0-9-]+)$/FAIL \1/; s/^mkligature: REFUSED: (.*)$/FAIL mkligature-reproducible: \1/'; return "${PIPESTATUS[0]}"; }
what=${1:?}; shift
case $what in
    preflight)
        [ -c /dev/kvm ] && [ -w /dev/kvm ] || echo "REFUSED no-kvm /dev/kvm is not usable"
        [ -x "$P" ] || echo "REFUSED no-engine $P"
        "$P" image inspect $img > /dev/null 2>&1 || echo "REFUSED no-image $img"
        for d in "$@"; do [ -f "$IMAGES/$d/commit" ] || echo "REFUSED no-image-directory $IMAGES/$d"; done
        echo "preflight: kvm, engine, image and image directories ($*) looked at; the take's CPUs $CPUS"
        exit 0 ;;
    ci-plan) ctr 0 $img python3 -I tests/ci-plan ;;
    census) ctr 0 $img tests/census ;;
    fetch-retry) ctr 0 $img tests/fetch-retry-selftest ;;
    mkligature)
        rm -rf "$PAX_BUILD/ligature"
        lift ctr 0 $img tools/mkligature "$PAX_BUILD/ligature" || exit $?
        row=$(cat "$PAX_BUILD/ligature/sums.txt")
        if grep -qx "#   $row" user/ligature.pin; then echo "mkligature: $row, the digest user/ligature.pin records"
        else echo "FAIL mkligature-pin: built $row, user/ligature.pin records $(grep '^#   ligature ' user/ligature.pin)"; exit 1; fi ;;
    rows)
        d=$(copy "$1") || { echo "FAIL rows-image: no image directory $IMAGES/$1"; exit 2; }
        shift
        ctr 1 $img tests/distribution-ligature "$d" --accel kvm "$@" ;;
    assemble)
        n=$1; o=$PAX_BUILD/assemble-$n; rm -rf "$o"; mkdir -p "$o"
        lift ctr 0 $img bash -c "python3 -I tools/distribution-root '$IMAGES/$n/base.cpio' '$IMAGES/$n/inputs' '$IMAGES/$n' '$o/dev.cpio' dev \
            && python3 -I tests/distribution '$o/dev.cpio' '$IMAGES/$n/kernel/kmain_console.elf' '$IMAGES/$n/inputs' '$IMAGES/$n' dev"; exit $? ;;
    *) echo "step.sh: no step $what"; exit 2 ;;
esac
