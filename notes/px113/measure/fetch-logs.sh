#!/bin/bash
# px113: download each listed job's log once (logs/<job>.log), the API's
# raw text with its own timestamps. Reads job ids on stdin.
set -u
cd "$(dirname "$0")/.." || exit 2
mkdir -p logs
while read -r id; do
    [ -s "logs/$id.log" ] && continue
    ok=0
    for a in 1 2 3 4; do
        if gh api --allow-escape-sequences "repos/wolffe-lang/pax/actions/jobs/$id/logs" > "logs/$id.log.part" 2> "logs/$id.err"; then
            mv "logs/$id.log.part" "logs/$id.log"; rm -f "logs/$id.err"; ok=1; break
        fi
        sleep $((a * 3))
    done
    [ $ok = 1 ] && echo "log $id: $(wc -l < "logs/$id.log" | tr -d ' ') lines" || echo "log $id: FAILED ($(head -c 200 "logs/$id.err"))"
done
