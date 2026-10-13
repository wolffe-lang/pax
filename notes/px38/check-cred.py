#!/usr/bin/env python3
# px38: the credential rules as a model, held against every measured row
# of probes/cred.c.
#
#   check-cred.py RESULTS.txt...
#
# The model is what notes/px38-the-users.md proposes PAX implement. It
# was written from setuid(2), setreuid(2), setresuid(2), setfsuid(2) and
# credentials(7), then corrected where a row disagreed (the note says
# where). A caller is PRIVILEGED for these calls when its effective user
# id is 0; PAX has no capabilities, so that is the whole rule there.
# Prints the row count, every row the model gets wrong, and the counts
# the note's prediction named. Exit 0 when no row disagrees.
import re
import sys

M1 = 0xFFFFFFFF
EPERM, EINVAL = -1, -22
# the capabilities that follow the file-system user id (capabilities(7),
# "Effect of user ID changes on capabilities"): CHOWN, DAC_OVERRIDE,
# DAC_READ_SEARCH, FOWNER, FSETID, LINUX_IMMUTABLE(9)?, MKNOD(27), MAC_OVERRIDE(32)
FS_LOW = 0x1F


def u(x):
    return x & M1


def model(call, args, st, fs, priv):
    """(answer, (r, e, s), fs). st: (r, e, s). priv: effective USER id 0."""
    r, e, s = st
    a = [u(x) for x in args]
    kind = call[:-3]  # set, setfs, setre, setres
    if kind == "set":
        x = a[0]
        if x == M1:
            return EINVAL, st, fs
        if priv:
            return 0, (x, x, x), x
        if x in (r, s):
            return 0, (r, x, s), x
        return EPERM, st, fs
    if kind == "setfs":
        x = a[0]
        if x != M1 and (priv or x in (r, e, s, fs)):
            return fs, st, x
        return fs, st, fs
    if kind == "setre":
        nr, ne = r, e
        if a[0] != M1:
            if not priv and a[0] not in (r, e):
                return EPERM, st, fs
            nr = a[0]
        if a[1] != M1:
            if not priv and a[1] not in (r, e, s):
                return EPERM, st, fs
            ne = a[1]
        ns = s
        if a[0] != M1 or (a[1] != M1 and a[1] != r):
            ns = ne
        return 0, (nr, ne, ns), ne
    if kind == "setres":
        new = [r, e, s]
        for i in range(3):
            if a[i] != M1:
                if not priv and a[i] not in (r, e, s):
                    return EPERM, st, fs
                new[i] = a[i]
        return 0, tuple(new), new[1]
    raise ValueError(call)


ROW = re.compile(r"^(u1000 )?\((\d+) (\d+) (\d+)\) (set\w+)\(([-\d, ]+)\) = (-?\d+) -> (\d+) (\d+) (\d+) (\d+) cap (\S+)$")


def check(path):
    rows = bad = 0
    counts = {}
    capbad = 0
    section_user0 = True  # which user ids the group rows' caller has
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("== group ids, the caller's user ids (0 0 0)"):
            section_user0 = True
        m = ROW.match(line)
        if not m:
            continue
        rows += 1
        tagged, st = m.group(1), tuple(int(m.group(i)) for i in (2, 3, 4))
        call, args = m.group(5), [int(x) for x in m.group(6).split(",")]
        ans, after = int(m.group(7)), tuple(int(m.group(i)) for i in (8, 9, 10, 11))
        cap = m.group(12)
        is_user = call.endswith("uid")
        if is_user:
            priv = st[1] == 0
        else:
            priv = not tagged  # the group matrices: the caller's user ids are (0 0 0), or (1000 1000 1000) when tagged
        want = model(call, args, st, st[1], priv)
        got = (ans, after[:3], after[3])
        if want != got:
            bad += 1
            print("  MODEL WRONG %s: %s  (model: %s -> %s fs %s)" % (path, line, want[0], want[1], want[2]))
        # the two classes of privilege, where the capability mask can show them (user rows)
        if is_user and cap not in ("?",):
            mask = 0 if cap == "none" else None if cap == "full" else int(cap, 16)
            e, f = after[1], after[3]
            if cap == "full":
                ok = e == 0 and f == 0
            else:
                ok = ((mask & FS_LOW) != 0) == (f == 0 and 0 in after[:3]) and ((mask & ~0x10800021F) != 0) == (e == 0)
            if not ok:
                capbad += 1
                print("  PRIVILEGE CLASS WRONG %s: %s" % (path, line))
        key = (bool(tagged), st, call)
        z, p, o = counts.get(key, (0, 0, 0))
        counts[key] = (z + (ans == 0), p + (ans == EPERM), o + (ans not in (0, EPERM)))
        if call == "setresuid" and st == (1000, 1001, 1002) and all(x != 1002 for x in args):
            z, p, o = counts.get("p2", (0, 0, 0))
            counts["p2"] = (z + (ans == 0), p + (ans == EPERM), o + (ans not in (0, EPERM)))
        if call == "setresuid" and st == (0, 0, 0) and all(x != 1002 for x in args):
            z, p, o = counts.get("p2root", (0, 0, 0))
            counts["p2root"] = (z + (ans == 0), p + (ans == EPERM), o + (ans not in (0, EPERM)))
    print("%s: %d rows, %d the model gets wrong, %d where the capability mask is not what (effective id 0, file-system id 0) predicts" % (path, rows, bad, capbad))
    for k in ("p2", "p2root"):
        if k in counts:
            print("  %s: setresuid over {-1, 0, 1000, 1001, 1003}^3 as %s: %d answers of 0, %d of -EPERM, %d other" % (
                path, "(1000 1001 1002)" if k == "p2" else "(0 0 0)", *counts[k]))
    for k in sorted(x for x in counts if not isinstance(x, str)):
        print("  %s%s %-9s: 0 x %d, -EPERM x %d, other x %d" % ("u1000 " if k[0] else "", k[1], k[2], *counts[k]))
    return bad + capbad


if __name__ == "__main__":
    sys.exit(1 if sum(check(p) for p in sys.argv[1:]) else 0)
