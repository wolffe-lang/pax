#!/usr/bin/env python3
# px38: what the traced tools asked of Linux, per tool and in all.
#
#   strace-summary.py STRACEDIR PAXROOT > summary.txt
#
# For every NN-name.strace (strace -f): the programs it ran, the calls
# that read or change identity (with their arguments and answers), the
# files it opened outside the libraries and locales, the PAM modules it
# loaded, and the calls it made that PAX at PAXROOT does not answer
# (PAXROOT/kernel/user/user.lu's `const SYS_…` numbers; names to numbers
# by PAXROOT/tools/census/syscall_64.csv, px04's copy of the table).
import glob
import os
import re
import sys

d, pax = sys.argv[1], sys.argv[2]
num = {}
for line in open(os.path.join(pax, "tools/census/syscall_64.csv")):
    row = line.strip().split(",")
    if len(row) == 3 and row[0].isdigit():
        num[row[2]] = int(row[0])
have = set(int(n) for n in re.findall(r"^const SYS_[A-Z0-9_]+: u64 = (\d+)", open(os.path.join(pax, "kernel/user/user.lu")).read(), re.M))
# px09/px10's two, dispatched before the table of constants
have |= {1, 60, 231}

IDENT = re.compile(r"^(set(re|res|fs)?[ug]id|get(res)?[ug]id|gete[ug]id|[gs]etgroups|cap[gs]et|setsid|setpgid|getpgrp|getpgid|getsid|"
                   r"f?chown(at)?|lchown|chroot|vhangup|keyctl|setpriority|umask)$")
LINE = re.compile(r"^(\d+)\s+(\w+)\((.*)$")
QUIET = re.compile(r"^(/lib|/usr/lib|/usr/share/locale|/usr/share/zoneinfo|/etc/ld\.so|/usr/lib/locale|/proc/self/maps|/sys/devices/system/cpu)")
HASH = re.compile(r"\$y\$j9T\$[./A-Za-z0-9]+\$[./A-Za-z0-9]+")

allcalls = {}
missing_all = {}
for path in sorted(glob.glob(os.path.join(d, "*.strace"))):
    name = os.path.basename(path)[:-7]
    outp = path[:-7] + ".out"
    cmd = rc = ""
    if os.path.exists(outp):
        for l in open(outp, errors="replace"):
            if l.startswith("$ "):
                cmd = l[2:].strip()
            if l.startswith("rc="):
                rc = l.strip()
    execs, ident, opened, absent, pam, calls, other = [], [], [], [], [], [], []
    pending = {}
    for raw in open(path, errors="replace"):
        raw = HASH.sub("$y$j9T$<cut>", raw.rstrip("\n"))
        m = re.match(r"^(\d+)\s+<\.\.\. (\w+) resumed>(.*)$", raw)
        if m:
            pid, call, rest = m.group(1), m.group(2), m.group(3)
            head = pending.pop((pid, call), "")
            raw = "%s %s(%s%s" % (pid, call, head, rest)
        m = LINE.match(raw)
        if not m:
            continue
        pid, call, rest = m.groups()
        if rest.endswith("<unfinished ...>"):
            pending[(pid, call)] = rest[:-len("<unfinished ...>")].rstrip()
            continue
        if call not in calls:
            calls.append(call)
        allcalls.setdefault(call, set()).add(name)
        res = rest.rsplit(" = ", 1)[-1] if " = " in rest else "?"
        if call == "execve" and res.startswith("0"):
            execs.append(rest.split('"')[1])
        elif call in ("openat", "open"):
            p = rest.split('"')[1] if '"' in rest else "?"
            if "/security/pam_" in p or "/libpam" in p:
                b = os.path.basename(p)
                if not res.startswith("-") and b not in pam:
                    pam.append(b)
            elif not QUIET.match(p):
                flags = re.search(r"O_(RDONLY|WRONLY|RDWR)[A-Z_|]*", rest)
                item = "%s [%s]" % (p, flags.group(0) if flags else "")
                (absent if res.startswith("-") else opened).append(item + (" " + res if res.startswith("-") else ""))
        elif IDENT.match(call):
            ident.append("%s(%s" % (call, rest))
        elif call in ("ioctl",) and re.search(r"TIOCSCTTY|TIOCNOTTY|TIOCSPGRP|TIOCGPGRP|TIOCVHANGUP|TCSETS|TCGETS|TIOCGWINSZ|TIOCSWINSZ", rest):
            k = re.search(r"T[A-Z]+", rest).group(0)
            s = "ioctl(%s) %s" % (k, res.split(" ")[0] if not res.startswith("-") else res)
            if s not in other:
                other.append(s)
        elif call in ("socket", "connect") and re.search(r"AF_UNIX|AF_NETLINK", rest):
            s = "%s(%s" % (call, rest)
            if len(other) < 40:
                other.append(s[:150])
        elif call in ("prctl",):
            other.append("prctl(%s" % rest[:110])
        elif call in ("rename", "renameat", "renameat2", "link", "linkat", "unlink", "unlinkat", "fchmod", "fchmodat", "chmod", "flock", "fsync", "fdatasync") or \
                (call == "fcntl" and re.search(r"F_SETLK|F_OFD", rest)):
            other.append("%s(%s" % (call, rest[:150]))
    uniq = lambda xs: list(dict.fromkeys(xs))
    lack = sorted((num.get(c, -1), c) for c in calls if num.get(c, -1) not in have)
    for n, c in lack:
        missing_all.setdefault((n, c), []).append(name)
    print("=" * 78)
    print("%s    $ %s    (%s)" % (name, cmd, rc))
    print("  ran: " + " -> ".join(execs))
    print("  identity calls:")
    for x in ident:
        print("    " + x[:230])
    print("  files opened: " + "; ".join(uniq(opened)))
    if absent:
        print("  files asked for and not there (or refused): " + "; ".join(uniq(absent)))
    if pam:
        print("  PAM: " + " ".join(pam))
    if other:
        print("  also:")
        for x in uniq(other):
            print("    " + x)
    print("  %d distinct calls: %s" % (len(calls), " ".join(calls)))
    print("  not answered by PAX today: " + (", ".join("%s (%d)" % (c, n) for n, c in lack) or "none"))
print("=" * 78)
print("EVERY CALL NO TRACE'S PAX COUNTERPART ANSWERS TODAY, and the traces that made it")
for (n, c), names in sorted(missing_all.items()):
    print("  %-22s %4d  %2d traces: %s" % (c, n, len(names), " ".join(x.split("-", 1)[0] for x in names)))
print("  (%d numbers)" % len(missing_all))
