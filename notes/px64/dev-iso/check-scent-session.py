#!/usr/bin/env python3
"""notes/px64/dev-iso/check-scent-session.py PAX_ROOT SERIAL-LOG — px64:
the dev ISO's replay of mpx5-scent's session, as root and then as pax,
held to the suite's own rows (tests/mpx5-scent.d/rows.py), each session's
rows in order, the pax session's after root's. Two rows are the suite
image's and not this one's, and are replaced: `ls -l` (the dev image has
/etc/passwd, so owners read `root`; its /bin/sh is the stripped pelt) and
`grep` by name with PATH emptied of /bin (the dev image's /etc/shrc
installs lope's hook, so a command not found goes to lope's
command_not_found_handle: only the status, 127 or not, is the image's,
and it is printed, not held). Exit 1 when a row is not held."""
import re
import runpy
import sys

root, log = sys.argv[1], sys.argv[2]
mod = runpy.run_path(root + "/tests/mpx5-scent.d/rows.py")
text = open(log, "rb").read().decode("utf-8", "replace")
text = re.sub(r"\x1b\[[0-9;?=<>]*[A-Za-z]|\x1b[()][A-Za-z0-9]|\x1b[c78DEHM=>]", "", text).replace("\r", "")
lines = text.split("\n")
rows = []
for name, want in mod["ROWS"]:
    if name.startswith("the image: "):
        want = [want[0]] + [w.replace(" 0 0{_}", " root root{_}") for w in want[1:]]
    if name.startswith("grep by name with PATH emptied of /bin"):
        print("REPLACED %r: the dev image's lope hook answers a command not found" % name)
        want = [want[0]]
    rows.append((name, want))
mod["ROWS"][:] = rows + [(n + " (pax)", w) for n, w in rows]
missing = mod["held"](lines)
for n in missing:
    print("FAIL no %r" % n)
k = [i for i, l in enumerate(lines) if l.startswith("$ PATH=/nowhere grep -c cat words.txt")]
for i in k:
    print("the dev image's answer: %r" % lines[i + 1:i + 3])
print("%s dev ISO: mpx5-scent's %d rows, as root and as pax, %d not held" % ("PASS" if not missing else "FAIL", len(rows), len(missing)))
sys.exit(1 if missing else 0)
