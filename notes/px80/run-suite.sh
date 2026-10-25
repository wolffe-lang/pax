#!/usr/bin/env bash
# px80 (px79's run-suite.sh, px67's, px63's), kasumi, CPUs 0-3: a suite built
# in px65's container (localhost/px80-ubuntu) with notes/px80/lld-wrap first on
# PATH, so every kernel it links is the bundle's lld 18.1.8's, and so is every
# hosted program wolf links with -fuse-ld=lld (each link also compared with
# the container's lld 18.1.3: $B/lld.log), its Linux side on this
# host, then its images booted under TCG on the host on EVERY leg (both tiers,
# both firmwares, PAX_REQUIRE_UEFI=1), as CI's `tier all` does, and the
# root-on-disk leg (tools/rootdisk-leg, native BIOS) where CI runs one.
# Run under the block's lock. No package installed.
#   run-suite.sh SUITE [OUTNAME]
set -uo pipefail
L=$HOME/lanes/px80
T=${PAX_TREE:-$L/pax}
suite=$1; run=${2:-$1}
ulimit -c 0
B=$L/build/$run
rm -rf "$B"; mkdir -p "$B" "$L/tmp" "$L/cache" "$L/bin"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px80-ubuntu TMPDIR=$L/tmp PAX_REQUIRE_UEFI=1
extra=()
case $suite in
    mpx5-wolf)
        # CI's Linux-side image, by digest; the dev compiler's pinned bytes
        # (user/wolf.sums, verified by the suite's own W0) instead of a rebuild.
        export PAX_TREE_IMAGE=docker.io/library/python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
        podman image exists "$PAX_TREE_IMAGE" || podman pull -q "$PAX_TREE_IMAGE" > /dev/null
        extra=(-e PAX_DEV_WOLF_DIR=$L/wolf-bin) ;;
esac
cd "$T"
t0=$(date +%s)
how=--no-boot
grep -q -- '--only build' "tests/$suite" && how="--only build"
if grep -q fetch-busybox "tests/$suite"; then tools/fetch-busybox "$L/bin" > /dev/null; fi
podman run --rm --privileged --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$L/lld-out:/opt/px80:ro" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e CARGO_INCREMENTAL=0 -e PAX_LOPE_REPO=$L/lope "${extra[@]}" localhost/px80-ubuntu bash -c '
        set -euo pipefail; cd "$1"; git config --global --add safe.directory "*"
        export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        # CI fetches lupin by digest for a suite that runs it (mkw).
        if grep -q PAX_LUPIN "tests/$2"; then export PAX_LUPIN=$(tools/fetch-lupin | tail -1); fi
        export PATH=$1/notes/px80/lld-wrap:$PATH PX80_LLD=/opt/px80/ld.lld PX80_LLD_REF=/usr/bin/ld.lld PX80_LLD_LOG=$PAX_BUILD/lld.log
        tests/"$2" $3
    ' px80 "$T" "$suite" "$how" > "$B.build.log" 2>&1
brc=$?
lrc=-
if grep -q -- '--only linux' "tests/$suite"; then
    lrc=0
    taskset -c 0-3 "tests/$suite" --only linux --images "$B/$suite" > "$B.linux.log" 2>&1 || lrc=$?
fi
img=$B/$(ls "$B" | grep -m1 "^$suite\$" || echo "$suite")
for d in "$img"/*.img; do
    [ -f "$d" ] && cmp -s -n 4096 "$d" /dev/zero && rm -f "$d"
done
rc=0
env -u PAX_ROOTDISK taskset -c 0-3 "tests/$suite" --images "$img" > "$B.boot.log" 2>&1 || rc=$?
drc=-
if grep -q "tools/rootdisk-leg $suite " "$T/.github/workflows/ci.yml"; then
    dargs=$(grep -o "tools/rootdisk-leg $suite .*" "$T/.github/workflows/ci.yml" | head -n 1 | sed "s#tools/rootdisk-leg $suite ##")
    drc=0
    # shellcheck disable=SC2086
    PAX_BUILD=$B taskset -c 0-3 tools/rootdisk-leg "$suite" $dargs > "$B.disk.log" 2>&1 || drc=$?
fi
links=0 same=0
if [ -f "$B/lld.log" ]; then links=$(wc -l < "$B/lld.log"); same=$(grep -c '^identical ' "$B/lld.log"); fi
# A PASS line may quote the refusal it expected (mpx1's A6: `qemu-halt: NOT
# HALTED` for the spin kernel), so only a FAIL or NOT HALTED line with no
# PASS on it counts against the run.
pass=$(grep -c "PASS" "$B.boot.log")
fails=$(grep -E "FAIL|NOT HALTED" "$B.boot.log" | grep -vc "PASS")
printf '%s build rc=%s linux rc=%s boot rc=%s disk rc=%s %ss pass %s fail %s links %s identical %s\n' "$suite" "$brc" "$lrc" "$rc" "$drc" \
    $(( $(date +%s) - t0 )) "$pass" "$fails" "$links" "$same"
