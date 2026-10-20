#!/usr/bin/env python3
"""tl29: the last N `tier full` runs of pax, and which legs each red named.

    legs_table.py RUNS_JSON LOGDIR [N]

RUNS_JSON: fetch_repo.py's runs-pax.json (jobs: the latest attempt).
LOGDIR: <job id>.log for every failed suite job (gh api .../jobs/ID/logs),
including the first attempt of a re-run (ATTEMPT1 below). Prints one TSV row
a run: id, created, event, branch, conclusion, suites run, the failed jobs
and, for each, the legs its FAIL lines name (legs.py)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from legs import legs_of
# A re-run's first attempt is hidden from filter=latest: its failed jobs, read
# with `gh api repos/wolffe-lang/pax/actions/runs/ID/attempts/1/jobs`.
ATTEMPT1 = {38475501062: [(115565184433, "mpx4-lobo")], 38344726280: [(115123415157, "mpx1")]}
runs = json.load(open(sys.argv[1])); logdir = sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
def tier(r):
    return next((j["name"] for j in r["jobs"] if j["name"].startswith("tier ")), None)
full = sorted([r for r in runs if tier(r) == "tier full" and r["status"] == "completed"], key=lambda r: r["created_at"], reverse=True)[:n]
print("run\tcreated\tevent\tbranch\tconclusion\tattempts\tsuites\tfailed (job: legs named)")
for r in full:
    ran = [j for j in r["jobs"] if j.get("runner_name") and j["name"] != "plan" and not j["name"].startswith("tier")]
    bad = [(j["id"], j["name"]) for j in r["jobs"] if j["conclusion"] in ("failure", "timed_out") and j["name"] != "plan" and not j["name"].startswith("tier")]
    bad = [(i, nm, "") for i, nm in bad] + [(i, nm, "attempt 1 ") for i, nm in ATTEMPT1.get(r["id"], [])]
    cells = []
    for jid, nm, att in bad:
        p = os.path.join(logdir, "%d.log" % jid)
        if os.path.exists(p) and os.path.getsize(p):
            legs, unattr, nf = legs_of(p)
            what = " ".join(sorted(legs)) or ("no FAIL line" if not nf else "unattributed")
        else:
            what = "log not read"
        cells.append("%s%s %d: %s" % (att, nm, jid, what))
    print("%d\t%s\t%s\t%s\t%s\t%d\t%d\t%s" % (r["id"], r["created_at"][:16], r["event"], r["head_branch"], r["conclusion"], r["run_attempt"], len(ran), "; ".join(cells) or "-"))
