#!/bin/bash
# px64, kasumi: the prediction's time, measured from outside the guest:
# poll a suite's serial log every 0.2 s and stamp the moment its count of
# prompts (`$ `) reaches each value; then the time from each session's
# first prompt to the prompt after its last typed grep command (key 52
# of 53: the prompt that follows it is the session's 53rd).
#   timing.sh SERIAL-LOG OUT [KEYS-PER-SESSION]
set -u
log=$1; out=$2; per=${3:-53}
: > "$out.raw"
last=-1
for i in $(seq 1 9000); do
    if [ -f "$log" ]; then
        c=$(grep -ao '\$ ' "$log" | wc -l)
        if [ "$c" != "$last" ]; then printf '%s %s\n' "$(date +%s.%N)" "$c" >> "$out.raw"; last=$c; fi
        [ -f "$log.verdict" ] && [ -s "$log.verdict" ] && break
    fi
    sleep 0.2
done
python3 - "$out.raw" "$per" > "$out" <<'PY'
import sys
rows = [l.split() for l in open(sys.argv[1])]
per = int(sys.argv[2])
at = {}
for t, c in rows:
    c = int(c)
    for k in range(min(at) if at else 1, c + 1):
        at.setdefault(k, float(t))
for s, base in (("root", 0), ("pax", per)):
    a, b = at.get(base + 1), at.get(base + per)
    if a and b:
        print("%s: first prompt to the prompt after the last typed grep command: %.1f s" % (s, b - a))
    else:
        print("%s: not measured (prompts seen: %d)" % (s, max(at) if at else 0))
PY
cat "$out"
