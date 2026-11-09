"""px113: measure.json -> pax's tests/ci-budgets.d/yew-screen.json, the
committed observations the budget check reads.

    python3 -I to-repo.py measure.json OUT.json
"""
import json
import math
import sys

rows = json.load(open(sys.argv[1]))
LEGS = ["native bios", "release bios", "native uefi", "release uefi"]
out = {
    "jobs": ["mpx5-yew", "mpx5-screen"],
    "note": ("px113 (pax#305). Every completed attempt of the two jobs in the ci workflow's runs created "
             "2026-11-01 to 2026-11-09 (121 runs, read in pages of 30), each phase read from the job log's own "
             "line timestamps, in seconds rounded up. setup: the job's first line to the suite's step "
             "(checkout, apt, the pins' fetches, docker pull). programs: the step's start to its first "
             "`program:` line, every program built (yew_build: `mkyew: yew` to the next tool's first line, "
             "inside programs). native, release: to the last `built native`/`built release` line (kmain_console "
             "and the images). s0: to the Y0/S0 verdict (the Linux side; screen-ref's rows). Each leg, in boot "
             "order: to its last row line. post: the step's end to the log's end (the artifact upload, the "
             "runner's cleanup). legs: the plan's legs, `all` (every leg) or `native bios` (pr and full). A "
             "cancelled attempt's last phase reached is `cut` (a lower bound of that phase, never a completion); "
             "phases after it are absent, never zero. `red` lists an attempt's FAIL rows: a red of its own (a "
             "build or a session failed), never a timing sample. An attempt a re-run copied counts once."),
    "ci": [],
}
for r in rows:
    if r["name"] not in ("mpx5-yew", "mpx5-screen"):
        continue
    p = r["phases"]
    if "step" not in p:
        continue
    ph = {}
    wide = r["tier"] == "all"
    order = ["setup", "programs", "native", "release", "s0"] + LEGS if wide else ["setup", "programs", "native", "s0", "native bios"]
    for k in ("setup", "programs", "native", "release", "s0"):
        if p.get(k) is not None:
            ph[k] = math.ceil(p[k])
    cut = None
    for leg in LEGS:
        x = p.get("legs", {}).get(leg)
        if x:
            ph[leg] = math.ceil(x["seconds"])
            if not x["complete"]:
                cut = leg
    if r["conclusion"] == "cancelled" and cut is None:
        # cut before any leg: the last phase reached runs to the step's end
        reached = [k for k in order if k in ph]
        last = reached[-1] if reached else None
        nxt = order[order.index(last) + 1] if last and order.index(last) + 1 < len(order) else (None if last else "programs")
        if nxt and (not reached or p.get("tail", 0) > 1):
            ph[nxt] = math.ceil(p.get("tail") or p.get("step"))
            cut = nxt
    elif cut is not None and p.get("tail"):
        ph[cut] += math.ceil(p["tail"])
    if r["conclusion"] == "success":
        cut = None
    ph["post"] = math.ceil(p.get("post", 0))
    e = {
        "run": r["run"], "attempt": r["attempt"], "job_id": r["job"], "job": r["name"], "head": r["head"],
        "yew_pin": p.get("yew_pin"), "legs": "all" if r["tier"] == "all" else "native bios",
        "conclusion": r["conclusion"], "seconds": math.ceil(p["job"]),
        "phases": ph,
    }
    if p.get("yew") is not None:
        e["yew_build"] = math.ceil(p["yew"])
    if cut:
        e["cut"] = cut
    if p.get("fails"):
        e["red"] = p["fails"]
    out["ci"].append(e)
out["ci"].sort(key=lambda e: (e["job"] != "mpx5-yew", e["run"], e["attempt"]))
with open(sys.argv[2], "w") as f:
    json.dump(out, f, indent=1)
    f.write("\n")
print("%d observations" % len(out["ci"]))
