#!/bin/bash
# px65, kasumi: boot a built suite's images (TCG) in the lane's container
# under taskset -c 12-15, its Linux side first through the host's
# rootless podman when the suite has an `--only linux` (the suite's own
# throwaway container, CPUs 12-15 by taskset).
#   boot.sh SUITE TAG BOOT-ARGS...   (default: --tier native --firmware bios)
L=$HOME/lanes/px65; X=${PX65_TREE:-$L/pax}
S=$1 T=$2; shift 2
[ $# -gt 0 ] || set -- --tier native --firmware bios
B=$L/build/$T
cd "$X" || exit 2
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman TMPDIR=$L/tmp
export PAX_TREE_IMAGE=${PAX_TREE_IMAGE:-docker.io/library/python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1}
W=$B/$S
if grep -q -- '--only linux' "tests/$S" && [ -z "${PX65_NO_LINUX:-}" ]; then
    taskset -c 12-15 "tests/$S" --only linux --images "$W" > "$B.linux.log" 2>&1
    echo "linux $S: $? ($(tail -n 1 "$B.linux.log" | cut -c1-200))"
fi
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e PAX_TASKSET_CPUS=12-15 \
    ${PX65_BOOT_ENV:-} localhost/px65-ubuntu bash -c 'cd "$1"; s=$2; shift 2; taskset -c 12-15 tests/"$s" --images "$PAX_BUILD/$s" "$@"' \
    px65 "$X" "$S" "$@" > "$B.boot.log" 2>&1
rc=$?
echo "boot $S: $rc"
grep -a -E 'FAIL|SKIP' "$B.boot.log" | cut -c1-600 | head -40
grep -a -c 'PASS' "$B.boot.log"
tail -n 1 "$B.boot.log"
exit $rc
