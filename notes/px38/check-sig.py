#!/usr/bin/env python3
# px38: who may signal whom, as a rule, held against every row of
# probes/sig.c.
#
#   check-sig.py RESULTS.txt...
#
# The rule (kill(2); what the note proposes PAX implement): a signal is
# sent when the sender's effective user id is 0, or the sender's real or
# effective user id equals the target's real or saved user id; otherwise
# -EPERM. SIGCONT is also sent to any process of the sender's session.
# Exit 0 when no row disagrees.
import re
import sys

T = re.compile(r"^target (.*?): uid (\d+) (\d+) (\d+) (\d+)$")
S = re.compile(r"^sender \( *(\d+) +(\d+) +(\d+)\) -> target (.*?): kill\(pid, 0\) (-?\d+), tgkill\(pid, pid, 0\) (-?\d+), SIGCONT (-?\d+), SIGURG (-?\d+)$")


def check(path):
    targets, rows, bad = {}, 0, 0
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = T.match(line)
        if m:
            targets[m.group(1).strip()] = tuple(int(x) for x in m.groups()[1:])
            continue
        m = S.match(line)
        if not m:
            continue
        rows += 1
        r, e, s = (int(m.group(i)) for i in (1, 2, 3))
        tr, te, ts, tf = targets[m.group(4).strip()]
        ok = e == 0 or r in (tr, ts) or e in (tr, ts)
        want = (0 if ok else -1, 0 if ok else -1, 0, 0 if ok else -1)
        got = tuple(int(m.group(i)) for i in (5, 6, 7, 8))
        if want != got:
            bad += 1
            print("  RULE WRONG %s: %s" % (path, line))
    print("%s: %d sender rows against %d targets, %d the rule gets wrong" % (path, rows, len(targets), bad))
    return bad


if __name__ == "__main__":
    sys.exit(1 if sum(check(p) for p in sys.argv[1:]) else 0)
