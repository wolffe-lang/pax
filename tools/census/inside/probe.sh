#!/bin/sh
# probe.sh — the auxiliary vector and the vDSO, black-box, under gdb
# (inside/auxv.py). For each subject: the vector as built; then each
# entry hidden in turn (its type overwritten with AT_IGNORE), the run's
# exit status and stdout digest compared with the unmodified run; then
# the time/cpu/random system calls counted with the vDSO present and
# with AT_SYSINFO_EHDR hidden (what a kernel without a vDSO is asked);
# and, for one subject of each shape, which code reads each entry.
# Writes /out/auxv.jsonl and /out/auxv.csv.
set -eu
O=/out/auxv.jsonl
rm -f "$O"
mkdir -p /work
cp -R /stage/reel /work/reel
ssh-keygen -A > /dev/null
cd /work
probe() { # probe <subject> <dir> <prog> <args...as one shell string> [watch]
    s=$1 d=$2 p=$3 a=$4 w=${5:-}
    run() { # run <mode>
        rm -f /work/probe.out /work/probe.one
        ( cd "$d" && CENSUS_PROBE=$1 CENSUS_PROBE_OUT=/work/probe.one \
            CENSUS_PROBE_ARGS="$a < /dev/null > /work/probe.out 2>/dev/null" \
            gdb -q -batch -nx -x /census/inside/auxv.py "$p" > /dev/null 2>&1 ) || true
        sum=$(sha256sum /work/probe.out 2>/dev/null | cut -c1-16)
        if [ -s /work/probe.one ]; then
            python3 -c 'import json,sys; r=json.loads(open(sys.argv[1]).read()); r["subject"]=sys.argv[2]; r["stdout"]=sys.argv[3]; print(json.dumps(r))' \
                /work/probe.one "$s" "$sum" >> "$O"
        else
            printf '{"subject": "%s", "mode": "%s", "probe_failed": true}\n' "$s" "$1" >> "$O"
        fi
    }
    run list
    types=$(tail -n 1 "$O" | python3 -c 'import json,sys; print(" ".join(str(t) for _, t in json.loads(sys.stdin.read()).get("entries", [])))')
    for t in $types; do run "ignore:$t"; done
    run vdso:0
    run vdso:1
    if [ "$w" = watch ]; then # who reads each entry: four hardware watchpoints a run
        set -- $types
        while [ $# -gt 0 ]; do
            g=$1; shift
            for _ in 1 2 3; do [ $# -gt 0 ] && { g="$g,$1"; shift; }; done
            run "watch:$g"
        done
    fi
    echo "probe: $s ($(echo "$types" | wc -w) entries)"
}
B=/stage/bore
probe bore-static-seq /work "$B/static/seq" "1 1000" watch
probe bore-static-sort /work "$B/static/sort" "/etc/passwd"
probe bore-static-sleep /work "$B/static/sleep" "0.01"
probe bore-dyn-seq /work "$B/dyn/seq" "1 1000" watch
probe bore-dyn-sort /work "$B/dyn/sort" "/etc/passwd"
probe bore-dyn-sleep /work "$B/dyn/sleep" "0.01"
probe lobo-t /work/reel /stage/lobo/lobo "-t" watch
probe dash /work /usr/bin/dash "-c 'echo hi; x=\$(echo sub); echo \$x'"
probe bash /work /usr/bin/bash "-c 'echo hi; x=\$(echo sub); echo \$x'"
probe pacman /work /usr/bin/pacman "-Q glibc"
probe make /work /usr/bin/make "-v"
probe curl /work /usr/bin/curl "-sS https://archlinux.org/" watch
probe sshd-t /work /usr/bin/sshd "-t"
python3 - <<'PY'
import csv, json
rows = [json.loads(l) for l in open("/out/auxv.jsonl")]
base = {r["subject"]: r for r in rows if r.get("mode") == "list"}
out = []
for r in rows:
    m = r.get("mode", "")
    if not m.startswith("ignore:"): continue
    b = base[r["subject"]]
    t = int(m.split(":")[1])
    name = dict((tt, n) for n, tt in b["entries"]).get(t, str(t))
    same = (r.get("exitcode") == b.get("exitcode") and r.get("stdout") == b.get("stdout")
            and "exitsignal" not in r)
    out.append([r["subject"], name, t, "tolerated" if same else "required",
                r.get("exitcode"), r.get("exitsignal", ""), r.get("stdout")])
with open("/out/auxv.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["subject", "entry", "type", "when_hidden", "exitcode", "exitsignal", "stdout16"])
    w.writerows(out)
with open("/out/vdso.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    calls = ["clock_gettime", "gettimeofday", "time", "getcpu", "clock_getres", "getrandom"]
    w.writerow(["subject", "vdso"] + calls + ["exitcode", "stdout16"])
    for r in rows:
        if r.get("mode", "").startswith("vdso:"):
            w.writerow([r["subject"], "hidden" if r["mode"].endswith("1") else "present"]
                       + [r.get("syscalls", {}).get(c, "") for c in calls]
                       + [r.get("exitcode"), r.get("stdout")])
reads = {}
for r in rows:
    if r.get("mode", "").startswith("watch:"):
        names = dict((t, n) for n, t in base[r["subject"]]["entries"])
        for t, who in r.get("reads", {}).items():
            reads.setdefault((r["subject"], names.get(int(t), t)), set()).update(who)
        for t in r["mode"].split(":")[1].split(","):
            reads.setdefault((r["subject"], names.get(int(t), t)), set())
with open("/out/auxv-reads.csv", "w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["subject", "entry", "read_by"])
    for (s, e), who in reads.items():
        w.writerow([s, e, " ".join(sorted(who))])
print("probe: wrote /out/auxv.csv, /out/vdso.csv and /out/auxv-reads.csv")
PY
