"""px113: the mpx5-yew and mpx5-screen jobs (every attempt) of the fetched
runs, one JSON list: run, attempt, job id, name, conclusion, the job's and
the main step's seconds from the API's timestamps.

    python3 -I list-jobs.py RUNS_JSON JOBDIR... > jobs.json
"""
import datetime
import glob
import json
import os
import sys

NAMES = ("mpx5-yew", "mpx5-screen", "mpx6-install")
runs = {r["id"]: r for r in json.load(open(sys.argv[1]))}


def t(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None


def secs(a, b):
    a, b = t(a), t(b)
    return (b - a).total_seconds() if a and b else None


out = []
seen = set()
for d in sys.argv[2:]:
    for path in sorted(glob.glob(os.path.join(d, "jobs-*.json"))):
        j = json.load(open(path))
        rid = j["run"]
        if rid in seen:
            continue
        seen.add(rid)
        r = runs.get(rid, {})
        for job in j["jobs"]:
            if job["name"] not in NAMES:
                continue
            main = [s for s in job.get("steps") or [] if s["name"].startswith(("the probe, the screen", "screen-ref against", "guided installer"))]
            m = main[0] if main else None
            out.append({
                "run": rid, "attempt": job.get("run_attempt"), "job": job["id"], "name": job["name"],
                "event": r.get("event"), "branch": r.get("branch"), "head": job["head_sha"][:8],
                "status": job["status"], "conclusion": job["conclusion"],
                "started": job["started_at"], "completed": job["completed_at"],
                "seconds": secs(job["started_at"], job["completed_at"]) if job["status"] == "completed" else None,
                "main": None if m is None else {"name": m["name"][:40], "conclusion": m["conclusion"],
                                                "seconds": secs(m.get("started_at"), m.get("completed_at"))},
            })
out.sort(key=lambda x: (x["started"] or "", x["name"]))
json.dump(out, sys.stdout, indent=1)
print()
sys.stderr.write("%d runs read, %d jobs\n" % (len(seen), len(out)))
