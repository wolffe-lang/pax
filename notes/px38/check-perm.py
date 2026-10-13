#!/usr/bin/env python3
# px38: the permission rule as a model, held against every row of
# sections A and B of probes/perm.c (a file's and a directory's three
# classes, five actors each).
#
#   check-perm.py RESULTS.txt...
#
# The rule (path_resolution(7), inode(7); what the note proposes PAX
# implement): the caller's file-system user id picks ONE class — the
# owner's bits if it owns the node, else the group's if its file-system
# group id or a supplementary group is the node's group, else the
# others' — and only that class's bits are read. A file-system user id
# of 0 reads and writes anything, searches any directory, and executes
# a file only when some execute bit is set. Exit 0 when no row disagrees.
import re
import sys

EACCES = -13
ACT = {"own": (1000, {2999}), "grp": (1001, {2000}), "sup": (1001, {2999, 2000}), "oth": (1002, {2999}), "root": (0, {0})}
OWNER, GROUP = 1000, 2000


def bits(mode, who):
    uid, gs = ACT[who]
    if uid == OWNER:
        return (mode >> 6) & 7
    if GROUP in gs:
        return (mode >> 3) & 7
    return mode & 7


def may(mode, who, want, is_dir):
    """want: a mask of 4 (read), 2 (write), 1 (execute or search)."""
    if ACT[who][0] == 0:
        if want & 1 and not is_dir and mode & 0o111 == 0:
            return False
        return True
    return bits(mode, who) & want == want


def a(ok):
    return 0 if ok else EACCES


F = re.compile(r"^file (\d+) (\w+) *: open r (-?\d+), w (-?\d+), rw (-?\d+); execve (-?\d+); access r (-?\d+) w (-?\d+) x (-?\d+); truncate (-?\d+)$")
D = re.compile(r"^dir (\d+) (\w+) *: list (-?\d+), stat of a name (-?\d+), chdir (-?\d+), create (-?\d+), unlink (-?\d+), rename (-?\d+), mkdir (-?\d+), rmdir (-?\d+)$")


def check(path):
    rows = bad = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = F.match(line)
        if m:
            mode, who = int(m.group(1), 8), m.group(2)
            got = tuple(int(x) for x in m.groups()[2:])
            r, w, x = may(mode, who, 4, False), may(mode, who, 2, False), may(mode, who, 1, False)
            # execve needs the execute bit alone (the kernel, not the caller, reads the file)
            want = (a(r), a(w), a(r and w), a(x), a(r), a(w), a(x), a(w))
        else:
            m = D.match(line)
            if not m:
                continue
            mode, who = int(m.group(1), 8), m.group(2)
            got = tuple(int(x) for x in m.groups()[2:])
            r, wx, x = may(mode, who, 4, True), may(mode, who, 3, True), may(mode, who, 1, True)
            # to change a directory's names: write AND search; the file's own mode (0000, root's) is not asked
            want = (a(r), a(x), a(x), a(wx), a(wx), a(wx), a(wx), a(wx))
        rows += 1
        if got != want:
            bad += 1
            print("  MODEL WRONG %s: %s  (model %s)" % (path, line, want))
    print("%s: %d rows of sections A and B, %d the model gets wrong" % (path, rows, bad))
    return bad


if __name__ == "__main__":
    sys.exit(1 if sum(check(p) for p in sys.argv[1:]) else 0)
