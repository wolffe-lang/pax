#!/usr/bin/env python3
"""notes/px64/dev-iso/check-scent-session.py PAX_ROOT SERIAL-LOG — px64:
the dev ISO's replay of mpx5-scent's session, as root and then as pax,
held to the suite's own rows (tests/mpx5-scent.d/rows.py), each session's
rows in order, the pax session's after root's. The kernel's own lines
(`user: …`; under `quiet` only its refusals and faults) are left out as
the suite leaves them out, and printed. One row is the suite image's and
not this one's, and is restated: `ls -l` (the dev image has /etc/passwd,
so owners read `root`). Exit 1 when a row is not held."""
import re
import runpy
import sys

root, log = sys.argv[1], sys.argv[2]
mod = runpy.run_path(root + "/tests/mpx5-scent.d/rows.py")
text = open(log, "rb").read().decode("utf-8", "replace")
text = re.sub(r"\x1b\[[0-9;?=<>]*[A-Za-z]|\x1b[()][A-Za-z0-9]|\x1b[c78DEHM=>]", "", text).replace("\r", "")
lines = []
for l in text.split("\n"):
    if l.startswith("user: "):
        print("the kernel's line: %s" % l)
        continue
    lines.append(l)
rows = []
for name, want in mod["ROWS"]:
    if name.startswith("the image: "):
        want = [want[0]] + [w.replace(" 0 0{_}", " root root{_}") for w in want[1:]]
    rows.append((name, want))
mod["ROWS"][:] = rows + [(n + " (pax)", w) for n, w in rows]
missing = mod["held"](lines)
for n in missing:
    print("FAIL no %r" % n)
print("%s dev ISO: mpx5-scent's %d rows, as root and as pax, %d not held" % ("PASS" if not missing else "FAIL", len(rows), len(missing)))
sys.exit(1 if missing else 0)
