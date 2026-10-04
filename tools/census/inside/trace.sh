#!/bin/sh
# trace.sh <workload> <mode> — run one workload under strace, inside a
# fresh census container (tools/census/census trace starts one per call).
#
#   mode o: strace -ff -o  (one raw file per process; tally.py scopes it)
#   mode c: strace -f -c   (strace's own whole-tree summary, a cross-check)
#
# A workload is tools/census/workloads/<name>.sh: it defines `workload`,
# which prefixes every traced command with T. Untraced helpers (curl
# driving lobo, the ssh client) run bare.
set -eu
W=$1
MODE=$2
OUT=/out/$W/$MODE
rm -rf "$OUT"
mkdir -p "$OUT/raw" "$OUT/c"
: > "$OUT/commands.txt"
n=0
T() {
    n=$((n + 1))
    printf '%s\n' "$*" >> "$OUT/commands.txt"
    case $MODE in
        o) strace -ff -q -y -s 128 -o "$OUT/raw/t" "$@" ;;
        c) strace -f -q -c -o "$OUT/c/summary.$n" "$@" ;;
        *) echo "trace: mode is o or c" >&2; exit 2 ;;
    esac
}
mkdir -p /work
. "/census/workloads/$W.sh"
cd /work
start=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
workload > "$OUT/workload.log" 2>&1
rc=$?
set -e
end=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf 'workload=%s mode=%s rc=%s start=%s end=%s strace=%s\n' \
    "$W" "$MODE" "$rc" "$start" "$end" "$(strace -V | head -1)" > "$OUT/meta.txt"
cat "$OUT/meta.txt"
tail -n 5 "$OUT/workload.log"
exit "$rc"
