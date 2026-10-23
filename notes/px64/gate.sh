#!/bin/bash
# px64, kasumi: the lane's whole local gate, at the head of ~/lanes/px64/pax.
# Exit 0 only when every part is green; each part's exit code is read
# from the part itself (no pipe), and the gate's own from this script.
#   gate.sh   (run under flock ~/lanes/scent-cores-12-15.lock, CPUs 12-15)
#  1 ci-plan     tests/ci-plan in the lane's container
#  2 mpx5-scent  every leg: native and release, BIOS and UEFI (the build
#                runs tools/mkscent, two builds to one digest)
#  3 static      the suite's scent is ct02's digest, bd860457…, 14,846,984 bytes
#  4 posture     scent's whole byte suite (tools/pax-posture: plain Ubuntu,
#                no LANG, no locale data) against the suite's scent
#  5 mpx3-tree   the tree's own suite (the adoption is kernel/tree's), native BIOS
#  6 mpx5-aspen  a neighbour image with no link, native BIOS
#  7 dev-iso     the dev ISO rebuilt at the head, booted, both sessions checked
set -u
L=$HOME/lanes/px64
P=$L/pax
head=$(git -C "$P" rev-parse HEAD)
printf '%s\n' $$ > "$L/gate.pid"
echo "gate at $head $(date -Is)"
[ -z "$(git -C "$P" status --porcelain)" ] || { echo "gate: the tree is not clean"; git -C "$P" status --short; exit 2; }
fail=0
part() { # name command...
    local name=$1 t0 rc; shift
    t0=$(date +%s)
    "$@" > "$L/gate-$name.log" 2>&1
    rc=$?
    echo "part $name rc=$rc $(( $(date +%s) - t0 ))s"
    [ "$rc" = 0 ] || fail=1
}
part ci-plan podman run --rm --cpuset-cpus 12-15 -v "$L:$L:Z" localhost/px64-ubuntu bash -c "git config --global --add safe.directory '*'; cd $P && tests/ci-plan"
grep -c '^ci-plan: PASS' "$L/gate-ci-plan.log"; grep '^ci-plan: FAIL' "$L/gate-ci-plan.log"
part mpx5-scent env PX64_TIERS=both bash "$L/run-suite.sh" mpx5-scent gate-scent --tier both --firmware both
grep -E 'PASS|FAIL|SKIP' "$L/build/gate-scent.boot.log" | cut -c1-200
S=$L/build/gate-scent/mpx5-scent/scent
static() {
    cat "$S/sums.txt"
    grep -qx 'scent bd860457f2ff97591b7525da5f46c186feee4b8266d3f51b121866b001135d89 14846984' "$S/sums.txt"
}
part static static
cat "$L/gate-static.log"
posture() {
    cp "$S/scent" "$L/scent/target/mkscent/scent" && sha256sum "$L/scent/target/mkscent/scent" &&
        (cd "$L/scent" && SCENT_IMAGE=localhost/px64-scent-oracle SCENT_CONTAINER_ARGS="--cpuset-cpus 12-15 --ulimit core=0:0" tools/pax-posture)
}
part posture posture
grep -E '^PAX posture|agree / |reviewed divergences' "$L/gate-posture.log"
part mpx3-tree bash "$L/run-suite.sh" mpx3-tree gate-tree
grep -cE 'PASS' "$L/build/gate-tree.boot.log"; grep -E 'FAIL|SKIP' "$L/build/gate-tree.boot.log" | cut -c1-200
part mpx5-aspen bash "$L/run-suite.sh" mpx5-aspen gate-aspen
grep -E 'PASS|FAIL|SKIP' "$L/build/gate-aspen.boot.log" | cut -c1-200
part dev-iso bash "$L/dev-all.sh" "$head"
grep -E 'rc=|PASS|FAIL|pax-dev.iso$' "$L/gate-dev-iso.log" | sort -u | cut -c1-200
echo "gate at $head: $([ "$fail" = 0 ] && echo GREEN || echo RED) $(date -Is)"
exit "$fail"
