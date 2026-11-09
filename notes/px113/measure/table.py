"""px113: jobs.json + logs/ -> measure.json and a table per job, per leg.

    python3 -I table.py jobs.json LOGDIR > table.txt   (measure.json beside jobs.json)

Every completed attempt of mpx5-yew and mpx5-screen with a log; mpx6-install
only for yew's build inside it (its own `mkyew` lines). An attempt that a
re-run copied (same name, start and end) counts once. The plan's tier is
read from the log's PAX_LEGS (empty: all, every leg).
"""
import json
import os
import re
import subprocess
import sys

jobs = json.load(open(sys.argv[1]))
logdir = sys.argv[2]
here = os.path.dirname(os.path.abspath(__file__))
seen, rows = set(), []
for j in jobs:
    key = (j["name"], j["started"], j["completed"])
    if key in seen or j["conclusion"] not in ("success", "failure", "cancelled") or (j["seconds"] or 0) <= 120:
        continue
    seen.add(key)
    log = os.path.join(logdir, "%d.log" % j["job"])
    if not os.path.exists(log):
        continue
    text = open(log, "rb").read().decode("utf-8", "replace")
    m = re.search(r"^\S+Z   PAX_LEGS: ?(.*)$", text, re.M)
    legs = m.group(1).strip() if m else None
    tier = "all" if legs == "" else ("native-bios" if legs == "--tier native --firmware bios" else legs)
    suite = j["name"]
    p = json.loads(subprocess.run([sys.executable, "-I", os.path.join(here, "phases.py"), suite, log],
                                  capture_output=True, text=True).stdout or "{}")
    if suite == "mpx6-install":
        # only yew's build: from `mkyew: yew` to the next line of another tool
        lines = [l for l in text.splitlines() if re.match(r"^\d{4}-", l)]
        y = [i for i, l in enumerate(lines) if " mkyew: yew " in l]
        if y:
            import datetime
            t = lambda l: datetime.datetime.strptime(l[:26], "%Y-%m-%dT%H:%M:%S.%f")
            i = y[0]
            k = next((k for k in range(i + 1, len(lines)) if not re.match(r"^\S+Z (mkyew: |yew |modules: |\s)", lines[k])), None)
            pin = re.search(r"mkyew: yew ([0-9a-f]{8})\S* pins wolf (\S+)", lines[i])
            p = {"yew": (t(lines[k]) - t(lines[i])).total_seconds() if k else None,
                 "yew_pin": pin.group(1) if pin else None, "yew_wolf": pin.group(2) if pin else None}
        else:
            p = {}
    rows.append(dict(j, tier=tier, phases=p))
json.dump(rows, open(os.path.join(os.path.dirname(sys.argv[1]), "measure.json"), "w"), indent=1)


def f(x):
    return "-" if x is None else "%d" % x


for suite in ("mpx5-yew", "mpx5-screen"):
    print("## %s (seconds; C cancelled at the limit, F failed; legs in boot order; * an unfinished leg)" % suite)
    print("%-12s %-3s %-13s %-8s %-8s %-4s %6s %6s | %5s %5s %5s %5s %5s %5s | %5s %5s %5s %5s | %5s %5s %6s" % (
        "run", "att", "event", "head", "pin", "tier", "job", "step", "setup", "yew", "progs", "nat", "rel", "s0",
        "n-bio", "r-bio", "n-uef", "r-uef", "tail", "post", "logjob") + " fails")
    for r in rows:
        if r["name"] != suite:
            continue
        p = r["phases"]
        lg = p.get("legs", {})

        def leg(n):
            x = lg.get(n)
            return "-" if not x else ("%d%s" % (x["seconds"], "" if x["complete"] else "*"))
        c = {"success": "", "cancelled": "C", "failure": "F"}[r["conclusion"]]
        yew = p.get("yew") if p.get("yew") is not None else p.get("yew_open")
        print("%-12d %-3s %-13s %-8s %-8s %-4s %5d%s %6s | %5s %5s %5s %5s %5s %5s | %5s %5s %5s %5s | %5s %5s %6s" % (
            r["run"], r["attempt"], (r["event"] or "")[:13], r["head"], p.get("yew_pin", "-"), r["tier"][:4], r["seconds"], c or " ",
            f(r["main"]["seconds"] if r["main"] else None), f(p.get("setup")), f(yew) + ("" if p.get("yew") is not None or yew is None else "*"),
            f(p.get("programs")), f(p.get("native")), f(p.get("release")), f(p.get("s0")),
            leg("native bios"), leg("release bios"), leg("native uefi"), leg("release uefi"), f(p.get("tail")), f(p.get("post")), f(p.get("job"))) + (" %d" % len(p.get("fails", [])) if p.get("fails") else ""))
    print()
print("## yew's build inside mpx6-install")
for r in rows:
    if r["name"] == "mpx6-install" and r["phases"].get("yew") is not None:
        print("%-12d %-3s %-13s %-8s %-8s %-6s %5d" % (r["run"], r["attempt"], r["event"][:13], r["head"], r["phases"]["yew_pin"], r["phases"]["yew_wolf"], r["phases"]["yew"]))
