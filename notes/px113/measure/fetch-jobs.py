"""px113: every attempt's jobs of each pax run, in pages of 30, with step
timestamps kept (ghretry's jobs.py drops them). Writes raw/jobs-<run>.json.
Usage: python3 -I fetch-jobs.py OUTDIR RUN_ID...
"""
import json
import os
import subprocess
import sys
import time

GH = "gh"
out, rids = sys.argv[1], sys.argv[2:]
for rid in rids:
    path = os.path.join(out, "jobs-%s.json" % rid)
    if os.path.exists(path):
        continue
    jobs, page, total = [], 1, None
    while True:
        for attempt in range(6):
            p = subprocess.run([GH, "api", "repos/wolffe-lang/pax/actions/runs/%s/jobs?per_page=30&page=%d&filter=all" % (rid, page)],
                               capture_output=True, text=True)
            if p.returncode == 0:
                break
            time.sleep(3 * (attempt + 1))
        else:
            sys.stderr.write("run %s page %d: %s\n" % (rid, page, p.stderr))
            sys.exit(1)
        d = json.loads(p.stdout)
        total = d["total_count"]
        jobs += d["jobs"]
        if len(jobs) >= total or not d["jobs"]:
            break
        page += 1
    if len(jobs) != total:
        sys.stderr.write("run %s: read %d of %d\n" % (rid, len(jobs), total))
        sys.exit(1)
    with open(path, "w") as f:
        json.dump({"run": int(rid), "total": total, "jobs": jobs}, f)
    print("run %s: %d jobs" % (rid, total), flush=True)
