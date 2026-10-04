#!/bin/sh
# inject.sh — which of the M-PX3 calls can a kernel answer ENOSYS and still
# run boreutils' suite? For every call the census saw a boreutils build
# make (out/boreutils-<kind>.csv), rerun tools/difftest with that ONE call
# answered -ENOSYS in every boreutils process (strace --inject, through
# inject-wrap), and compare the passing set with the wrapper's own
# baseline (no injection). Writes out/inject-<kind>.csv:
#   syscall,number,passed,failed,baseline_passed,verdict,first_failures
# verdict: tolerated (same passing set), degraded (some cases now fail),
# required (no case passes, or the binary never starts).
set -eu
K=${1:-static}
case $K in static) B=static ;; dynamic) B=dyn ;; *) echo "inject: static or dynamic" >&2; exit 2 ;; esac
OUT=/out/inject-$K
if [ "${2:-}" = one ]; then # inject.sh <kind> one <name>: one rerun of the suite
    [ -x /work/inj/inject-wrap ] || { mkdir -p "$OUT" /work/inj; cc -O2 -o /work/inj/inject-wrap /census/inside/inject-wrap.c; }
    d=/work/inj/$3
    rm -rf "$d"; mkdir -p "$d/bin"
    for u in /stage/bore/$B/*; do cp /work/inj/inject-wrap "$d/bin/$(basename "$u")"; done
    printf '%s\n%s\n' "$3" "/stage/bore/$B" > "$d/bin/.census-inject"
    cp -R /stage/boreutils "$d/tree"
    ( cd "$d/tree" && BORE_ORACLE_ANY=1 BORE_GNU_PREFIX= \
        python3 tools/difftest --bin "$d/bin" > "$OUT/$3.log" 2>&1 ) || true
    rm -rf "$d"
    echo "inject-$K: $3: $(tail -n 1 "$OUT/$3.log")"
    exit 0
fi
if [ "${2:-}" != summary ]; then # the whole run; `inject.sh <kind> summary` only re-summarizes
    rm -rf "$OUT" /work/inj
    mkdir -p "$OUT" /work/inj
    cc -O2 -o /work/inj/inject-wrap /census/inside/inject-wrap.c
    { echo none; tail -n +2 "/out/boreutils-$K.csv" | cut -d, -f1; } |
        xargs -P 8 -n 1 sh /census/inside/inject.sh "$K" one
fi
python3 - "$OUT" "$K" <<'PY'
import csv, os, re, sys
out, k = sys.argv[1], sys.argv[2]
def res(name):
    p = os.path.join(out, name + ".log")
    ok, bad = set(), []
    for l in open(p, errors="replace"):
        if l.startswith("ok   "): ok.add(l[5:].strip())
        elif l.startswith("FAIL "): bad.append(l[5:].split("  args=")[0].strip())
    return ok, bad
base, _ = res("none")
nums = {}
for r in csv.DictReader(open(f"/out/boreutils-{k}.csv")):
    nums[r["syscall"]] = r["number"]
rows = []
for name in nums:
    if not os.path.exists(os.path.join(out, name + ".log")):
        rows.append([name, nums[name], "", "", len(base), "not run", ""])
        continue
    ok, bad = res(name)
    lost = sorted(base - ok)
    if not ok: v = "required"
    elif not lost: v = "tolerated"
    else: v = "degraded"
    rows.append([name, nums[name], len(ok), len(bad), len(base), v, "; ".join(lost[:3])])
with open(f"/out/inject-{k}.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["syscall", "number", "passed", "failed", "baseline_passed", "verdict", "first_failures"])
    for r in sorted(rows, key=lambda r: ({"required": 0, "degraded": 1, "tolerated": 2}.get(r[5], 3), int(r[1]))):
        w.writerow(r)
print(f"inject-{k}: baseline {len(base)} passed; " +
      ", ".join(f"{v} {sum(1 for r in rows if r[5]==v)}" for v in ("required", "degraded", "tolerated")))
PY
