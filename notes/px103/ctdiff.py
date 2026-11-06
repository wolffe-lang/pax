#!/usr/bin/env python3
"""ctdiff.py — px103: hold PAX's sudo's run of sudo-ct.sh to Ubuntu's.

    ctdiff.py UBUNTU.txt PAX.txt [-v ROW...]

Rows are split at `=== ROW name (who)` and `--- setup`/`##### configuration`
markers (a row is its name in its configuration group). A row is the same
when its text is equal after the named normalisations:
  - the container's host name and sudo's hash and version line;
  - log lines' time stamps (`Mon DD HH:MM:SS`);
and is listed otherwise. Prints `same N of M` and the differing rows.
"""
import re, sys

def rows(path):
    out, group, cur = {}, "start", None
    for line in open(path, errors="replace").read().split("\n"):
        if line.startswith("##### configuration"):
            group = line[19:].strip(); cur = None; continue
        if line.startswith("--- setup"):
            group = group.split(" /")[0] + " /" + line; cur = None; continue
        m = re.match(r"=== ROW (\S+) \((\w+)\)", line)
        if m:
            cur = "%s: %s" % (group, m.group(1)); out[cur] = []; continue
        if line.startswith("== /var/log/sudo.log"):
            cur = "%s: LOG" % group; out[cur] = []; continue
        if cur is not None:
            out[cur].append(line)
    return out

PAM = False

def norm(lines):
    t = "\n".join(l for l in lines if not l.startswith("light:"))
    if PAM:
        t = re.sub(r"^umask=\d+$", "umask=N", t, flags=re.M)
    t = re.sub(r"^[A-Z][a-z]{2} [ 0-9]\d \d\d:\d\d:\d\d ", "STAMP ", t, flags=re.M)
    return t.strip()

a, b = rows(sys.argv[1]), rows(sys.argv[2])
named = []
args = sys.argv[3:]
if args[:1] == ["--named"]:
    for l in open(args[1]).read().split("\n"):
        if l and not l.startswith("#"):
            r, why = l.split("\t", 1)
            named.append((r, why))
    args = args[2:]
verbose = args[:1] == ["-v"]
want = args[1:]
same = 0
diff = []
names = {}
for k in a:
    # PAX has no PAM: the configuration that installs it as Ubuntu does differs by its umask
    PAM = "pam as installed" in k
    equal = k in b and norm(a[k]) == norm(b[k])
    why = None
    for r, w in named:
        hit = re.search(r[5:], "\n".join(a[k])) if r.startswith("text:") else re.search(r, k)
        if hit:
            why = w
            break
    if why is not None:
        names[k] = why
        if equal:
            print("STALE name (the row is the same):", k)
            diff.append(k)
        continue
    if equal:
        same += 1
    else:
        diff.append(k)
print("same %d of %d rows; %d differ by name (each with its reason); %d unexplained (%d only in PAX's)" % (same, len(a), len(names), len(diff), len([k for k in b if k not in a])))
for k in diff:
    print("DIFF", k)
if diff:
    sys.exit(1)
if verbose:
    import difflib
    for k in diff:
        if want and not any(w in k for w in want):
            continue
        print("=====", k)
        for l in difflib.unified_diff(norm(a[k]).split("\n"), norm(b.get(k, [])) .split("\n") if k in b else [], "ubuntu", "pax", lineterm="", n=1):
            print(l)
