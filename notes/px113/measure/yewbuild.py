"""px113: yew's build in every log that has one, all three jobs that build
it (mpx5-yew, mpx5-screen, mpx6-install): from `mkyew: yew <sha> pins wolf V`
to the `yew <version>` line its `--version` prints after the build, so a
build cut by a cancel is never counted. One TSV line per build.

    python3 -I yewbuild.py jobs.json LOGDIR > yew-builds.tsv
"""
import datetime
import json
import os
import re
import sys

jobs = json.load(open(sys.argv[1]))
seen = set()
t = lambda l: datetime.datetime.strptime(l[:26], "%Y-%m-%dT%H:%M:%S.%f")
print("run\tattempt\tjob\thead\tyew_pin\twolf\tseconds")
for j in jobs:
    key = (j["name"], j["started"], j["completed"])
    if key in seen:
        continue
    seen.add(key)
    path = os.path.join(sys.argv[2], "%d.log" % j["job"])
    if not os.path.exists(path):
        continue
    lines = [l for l in open(path, "rb").read().decode("utf-8", "replace").splitlines() if re.match(r"^\d{4}-\d\d-\d\dT", l)]
    for i, l in enumerate(lines):
        m = re.match(r"^\S+Z mkyew: yew ([0-9a-f]{8})[0-9a-f]* pins wolf (\S+)", l)
        if not m:
            continue
        end = next((k for k in range(i + 1, len(lines)) if re.match(r"^\S+Z yew \d", lines[k])), None)
        if end is None or any(re.match(r"^\S+Z mkyew: yew ", lines[k]) for k in range(i + 1, end)):
            continue
        print("%d\t%s\t%s\t%s\t%s\t%s\t%.0f" % (j["run"], j["attempt"], j["name"], j["head"], m.group(1), m.group(2),
                                                 (t(lines[end]) - t(l)).total_seconds() + 0.4999))
