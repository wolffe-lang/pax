#!/usr/bin/env bash
# px64, kasumi only: a suite's build in the lane's own Ubuntu container
# (localhost/px64-ubuntu, CPUs 12-15), its Linux side through the host's
# podman (the suite's own throwaway container, CPUs 12-15 by taskset), its
# boots back in the lane's container under TCG (QEMU 8.2.2, CI's).
# No package installed on the host.
#   run-suite.sh SUITE [RUN] [BOOT ARGS...]   (default boot args: --tier native --firmware bios)
set -uo pipefail
L=$HOME/lanes/px64
suite=$1; run=${2:-$1}; shift; [ $# -gt 0 ] && shift
bootargs=("$@"); [ ${#bootargs[@]} -gt 0 ] || bootargs=(--tier native --firmware bios)
printf '%s\n' $$ > "$L/suite-$run.pid"
ulimit -c 0
uptime
B=$L/build/$run
rm -rf "$B"; mkdir -p "$B" "$L/tmp" "$L/cache"
export PAX_CACHE=$L/cache PAX_BUILD=$B PAX_ENGINE=podman TMPDIR=$L/tmp
export PAX_TREE_IMAGE=docker.io/library/python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
P=${PX64_SRC:-$L/pax}
cd "$P"
t0=$(date +%s)
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR -e CARGO_INCREMENTAL=0 localhost/px64-ubuntu bash -c '
        set -euo pipefail; cd "$1"; export PAX_WOLF=$(tools/fetch-wolf | tail -1)
        tests/"$2" --only build --tier "$3"
    ' px64 "$P" "$suite" "${PX64_TIERS:-native}" > "$B.build.log" 2>&1
rc=$?
printf 'build %s rc=%s %ss %s\n' "$suite" "$rc" $(( $(date +%s) - t0 )) "$(date -Is)"
[ "$rc" = 0 ] || { tail -20 "$B.build.log"; exit 1; }
t0=$(date +%s)
taskset -c 12-15 "tests/$suite" --only linux --images "$B/$suite" > "$B.linux.log" 2>&1
rc=$?
printf 'linux %s rc=%s %ss %s\n' "$suite" "$rc" $(( $(date +%s) - t0 )) "$(date -Is)"
[ "$rc" = 0 ] || { tail -20 "$B.linux.log"; exit 1; }
t0=$(date +%s)
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" \
    -e PAX_CACHE -e PAX_BUILD -e TMPDIR localhost/px64-ubuntu bash -c '
        cd "$1"; s=$2; shift 2; taskset -c 12-15 tests/"$s" --images "$PAX_BUILD/$s" "$@"
    ' px64 "$P" "$suite" "${bootargs[@]}" > "$B.boot.log" 2>&1
rc=$?
printf 'boot %s rc=%s %ss %s\n' "$suite" "$rc" $(( $(date +%s) - t0 )) "$(date -Is)"
grep -E 'PASS|FAIL|SKIP' "$B.boot.log" | cut -c1-400
uptime
exit $rc
