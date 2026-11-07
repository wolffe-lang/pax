#!/usr/bin/env python3
"""ttydiff.py — px106: hold one typed session's transcript to another.

    ttydiff.py A B [--named NAMED SESSION] [--cut TEXT] [--mask-tty]

A and B are what a terminal showed (tools/linux-tty's OUT, or a PAX
serial log's session). Both are normalised the same way: carriage returns
dropped, terminal escape sequences (pelt's `ESC [ 6 n`) removed, a sudo
log line's time stamp (`Mon DD HH:MM:SS`) as STAMP, a date (`YYYY-MM-DD`)
as DATE, a crypt string (`$7$...`, `$y$...`, `$6$...`) as HASH, and the
day field of a shadow line as DAY; with --mask-tty also `TTY=NAME` as
TTY=T (PAX's console is ttyS0, a pseudo-terminal pts/N). --cut TEXT keeps
each side up to the first line holding TEXT (that line included).

Without --named the two must be equal: exit 0, or 1 with the diff. With
--named, NAMED holds `SESSION<TAB>REGEX<TAB>REASON` lines; a hunk where the
two differ is allowed when a rule of SESSION matches the hunk's A text or
its B text (REGEX searched, multi-line), every rule of SESSION must match
some hunk (a stale name is a failure), and no other hunk may differ. It
prints `same: N lines; named: K hunks` and exits 0, or the unnamed hunks
and stale rules and 1.
"""
import difflib
import re
import sys

ESC = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]")


def norm(path, cut, mask_tty):
    raw = open(path, "rb").read()
    raw = ESC.sub(b"", raw).replace(b"\r", b"")
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"^[A-Z][a-z]{2} [ 0-9]\d \d\d:\d\d:\d\d ", "STAMP ", t, flags=re.M)
    t = re.sub(r"\b\d{4}-\d\d-\d\d\b", "DATE", t)
    t = re.sub(r"\$(7|y|6|5|2[abxy]|1)\$[^\s:]+", "HASH", t)
    t = re.sub(r"^([a-z_][a-z0-9_-]*:[^:\n]*:)\d+(:)", r"\1DAY\2", t, flags=re.M)
    if mask_tty:
        t = re.sub(r"TTY=\S+", "TTY=T", t)
    lines = t.split("\n")
    if cut:
        for i, l in enumerate(lines):
            if cut in l:
                lines = lines[: i + 1]
                break
    return lines


def main(argv):
    args = argv[1:]
    named = None
    session = None
    cut = None
    mask_tty = False
    files = []
    while args:
        a = args.pop(0)
        if a == "--named":
            named, session = args.pop(0), args.pop(0)
        elif a == "--cut":
            cut = args.pop(0)
        elif a == "--mask-tty":
            mask_tty = True
        else:
            files.append(a)
    if len(files) != 2:
        sys.stderr.write(__doc__)
        return 2
    a, b = norm(files[0], cut, mask_tty), norm(files[1], cut, mask_tty)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    hunks = [(i1, i2, j1, j2) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    same = sum(i2 - i1 for op, i1, i2, j1, j2 in sm.get_opcodes() if op == "equal")
    if named is None:
        if not hunks:
            print("equal: %d lines" % len(a))
            return 0
        for line in difflib.unified_diff(a, b, files[0], files[1], lineterm="", n=2):
            print(line)
        return 1
    rules = []
    for line in open(named).read().split("\n"):
        if not line or line.startswith("#"):
            continue
        s, rx, why = line.split("\t", 2)
        if s == session:
            rules.append([re.compile(rx, re.M), why, 0])
    bad = []
    for i1, i2, j1, j2 in hunks:
        ta, tb = "\n".join(a[i1:i2]), "\n".join(b[j1:j2])
        hit = None
        for r in rules:
            if r[0].search(ta) or r[0].search(tb):
                hit = r
                break
        if hit is None:
            bad.append("unnamed difference at %d/%d:\n- %s\n+ %s" % (i1 + 1, j1 + 1, ta.replace("\n", "\n- "), tb.replace("\n", "\n+ ")))
        else:
            hit[2] += 1
    for r in rules:
        if r[2] == 0:
            bad.append("stale name: %s (%s)" % (r[0].pattern, r[1]))
    if bad:
        print("\n".join(bad))
        return 1
    print("same: %d lines; named: %d hunks by %d rules" % (same, len(hunks), len(rules)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
