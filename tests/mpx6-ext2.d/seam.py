#!/usr/bin/env python3
"""The seam's two rows: kernel/volume is the one way into kernel/ext2 and kernel/journal.

  seam.py REPO

SEAM-CALLERS: every kernel source outside kernel/ext2, kernel/journal and
kernel/volume that imports ext2 or journal, or names `ext2.` or `journal.` in
code (comments and string literals are left out), is a site that bypasses the
seam. One test kernel is allowed by name: kmain_journal_guard.lu drives
kernel/ext2 directly on purpose (tests/mpx6-journal's guard rows are
white-box).

SEAM-CONSTS: each constant kernel/volume publishes has the value of the
constant of the same name in kernel/ext2. (wolf cannot yet give a module
constant another module's constant as its value, so kernel/volume spells each
value again, and this row keeps the two spellings equal.)

Prints one verdict line a row at column 0, `PASS <row>: …` or `FAIL <row>: …`,
each followed by its details two spaces in. Exit 0 when both pass, else 1.
"""
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1])
seam = ("kernel/ext2/", "kernel/journal/", "kernel/volume/")
allowed = {"kernel/kmain_journal_guard.lu": "a white-box test kernel of tests/mpx6-journal"}
code = re.compile(r'//[^\n]*|"(?:\\.|[^"\\])*"')
use = re.compile(r"^\s*use\s+(ext2|journal)\s*$")
ref = re.compile(r"\b(ext2|journal)\.([A-Za-z_][A-Za-z0-9_]*)")
const = re.compile(r"^pub const ([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\w+\s*=\s*(\S+)\s*$")


def stripped(path):
    return code.sub(lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), path.read_text(encoding="utf-8"))


worst = 0
sites, files = [], {}
for path in sorted((repo / "kernel").rglob("*.lu")):
    rel = path.relative_to(repo).as_posix()
    if rel.startswith(seam) or rel in allowed:
        continue
    for no, line in enumerate(stripped(path).splitlines(), 1):
        found = (["use " + use.match(line)[1]] if use.match(line) else []) + \
            [m[1] + "." + m[2] for m in ref.finditer(line)]
        for what in found:
            sites.append((rel, no, what))
            files[rel] = files.get(rel, 0) + 1
if sites:
    worst = 1
    print("FAIL SEAM-CALLERS: %d sites outside kernel/volume in %d files: %s" % (
        len(sites), len(files), ", ".join("%s (%d)" % kv for kv in sorted(files.items()))))
    for rel, no, what in sites:
        print("  %s:%d %s" % (rel, no, what))
else:
    print("PASS SEAM-CALLERS: only kernel/volume reaches kernel/ext2 and kernel/journal (allowed by name: %s)"
          % ", ".join(sorted(allowed)))

volume = repo / "kernel/volume/volume.lu"
if not volume.exists():
    worst = 1
    print("FAIL SEAM-CONSTS: there is no kernel/volume/volume.lu")
else:
    theirs = {m[1]: m[2] for m in map(const.match, stripped(repo / "kernel/ext2/ext2.lu").splitlines()) if m}
    ours = {m[1]: m[2] for m in map(const.match, stripped(volume).splitlines()) if m}
    wrong = ["%s: kernel/volume %s, kernel/ext2 %s" % (k, v, theirs.get(k, "(none)"))
             for k, v in sorted(ours.items()) if theirs.get(k) != v]
    if wrong:
        worst = 1
        print("FAIL SEAM-CONSTS: %d of kernel/volume's %d constants differ from kernel/ext2's" % (len(wrong), len(ours)))
        for w in wrong:
            print("  " + w)
    else:
        print("PASS SEAM-CONSTS: kernel/volume's %d constants are kernel/ext2's values (%s)"
              % (len(ours), ", ".join(sorted(ours))))
sys.exit(worst)
