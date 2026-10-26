#!/usr/bin/env bash
# as02b, items 2 and 4 on every leg: tests/mpx5-clef with its kernel built
# through the explicit seam with the clef package (WOLF_AS, the seam wolf),
# both tiers; then tests/mpx5-wolf, its kernels built the same way, with the
# dev compiler's recorded bytes (user/wolf.sums, held by its own W0). The
# builds and the boots in clef's integration image; the Linux sides on the
# kasumi host, whose podman they need. PHASE is build, linux or boot.
#   L=~/lanes/as02b notes/as02b/qualify-legs.sh PHASE PKG-DIR OUT
set -uo pipefail
phase=$1 pkg=$2 out=$3
cd "$L/pax" || exit 2
seam=$L/cache/wolf-9f2cff44c945697903e52ea7e5fdf05539b207ae/bin/wolf
case $phase in
    build)
        export WOLF_AS=$pkg/clef PAX_WOLF=$seam PAX_CLEF_REPO=$L/clef
        PAX_BUILD=$out/q tests/mpx5-clef --only build; echo "mpx5-clef build rc=$?"
        PAX_BUILD=$out/w PAX_DEV_WOLF_DIR=$L/dev-wolf tests/mpx5-wolf --only build; echo "mpx5-wolf build rc=$?"
        ;;
    linux)
        PAX_BUILD=$out/q tests/mpx5-clef --only linux --images "$out/q/mpx5-clef"; echo "mpx5-clef linux rc=$?"
        PAX_BUILD=$out/w tests/mpx5-wolf --only linux --images "$out/w/mpx5-wolf"; echo "mpx5-wolf linux rc=$?"
        ;;
    boot)
        export PAX_REQUIRE_UEFI=1
        PAX_BUILD=$out/q tests/mpx5-clef --images "$out/q/mpx5-clef"; echo "mpx5-clef boots rc=$?"
        PAX_BUILD=$out/w tests/mpx5-wolf --images "$out/w/mpx5-wolf"; echo "mpx5-wolf boots rc=$?"
        ;;
    *) echo "phase: build, linux or boot"; exit 2 ;;
esac
