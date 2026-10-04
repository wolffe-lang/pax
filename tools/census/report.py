#!/usr/bin/env python3
"""report.py — px04's census: tallies -> the ranked union, the milestone
sets, the P3 lane lists, and the generated tables in docs/CENSUS.md.

    python3 report.py OUT DOC            write OUT/union.csv, OUT/milestones.csv
                                         and DOC's generated blocks
    python3 report.py OUT DOC --check    regenerate in memory; exit 1 if any
                                         committed file differs (CI runs this)

DOC keeps its prose; only the text between `<!-- census:NAME -->` and
`<!-- /census:NAME -->` is generated.
"""
import csv, io, json, os, re, sys
from collections import Counter

# The milestone order (sprints/pax/index.md) and the contract's seven
# workloads; boreutils and the shell are each traced two ways.
WORKLOADS = ["boreutils-static", "boreutils-dynamic", "lobo", "dash", "bash",
             "pacman", "cc", "sshd", "curl"]
GROUP = {"boreutils-static": "boreutils", "boreutils-dynamic": "boreutils", "lobo": "lobo",
         "dash": "shell", "bash": "shell", "pacman": "pacman", "cc": "cc",
         "sshd": "sshd", "curl": "curl"}
GROUPS = ["boreutils", "lobo", "shell", "pacman", "cc", "sshd", "curl"]
MILESTONES = [  # (name, what, workloads whose calls it adds)
    ("M-PX3", "a static boreutils binary", ["boreutils-static"]),
    ("M-PX4", "lobo, built for Linux (dynamic: ld.so and glibc)", ["boreutils-dynamic", "lobo"]),
    ("M-PX5", "a shell, the package manager, cc", ["dash", "bash", "pacman", "cc"]),
    ("net", "the network floor: sshd and curl", ["sshd", "curl"]),
]
LANES = ["process and memory", "files", "time", "signals", "sockets"]
PM, FI, TI, SI, SO = LANES
LANE = {}
for n in """execve execveat exit exit_group brk mmap munmap mprotect mremap madvise
    mlock munlock msync mincore arch_prctl set_tid_address set_robust_list rseq
    prlimit64 getrlimit setrlimit getrandom sched_getaffinity sched_setaffinity
    sched_yield clone clone3 fork vfork wait4 waitid futex getpid getppid gettid
    getpgrp getpgid setpgid getsid setsid getuid geteuid getgid getegid getresuid
    getresgid setuid setgid setreuid setregid setresuid setresgid setfsuid setfsgid
    getgroups setgroups uname sysinfo getrusage getpriority setpriority prctl
    seccomp keyctl chroot capget capset personality membarrier
    process_vm_readv pidfd_open""".split():
    LANE[n] = PM
for n in """read write pread64 pwrite64 readv writev preadv pwritev open openat
    openat2 close close_range creat lseek stat fstat lstat newfstatat statx statfs
    fstatfs access faccessat faccessat2 getdents64 getcwd chdir fchdir mkdir mkdirat
    rmdir unlink unlinkat rename renameat renameat2 link linkat symlink symlinkat
    readlink readlinkat chmod fchmod fchmodat fchmodat2 chown fchown lchown fchownat
    umask truncate ftruncate fsync fdatasync sync syncfs utimensat futimesat utime
    dup dup2 dup3 fcntl ioctl pipe pipe2 flock fallocate sendfile copy_file_range
    splice tee name_to_handle_at mknod mknodat getxattr lgetxattr fgetxattr
    setxattr lsetxattr fsetxattr listxattr llistxattr flistxattr removexattr
    eventfd eventfd2 memfd_create inotify_init1 inotify_add_watch
    inotify_rm_watch mount umount2""".split():
    LANE[n] = FI
for n in """clock_gettime clock_getres clock_nanosleep nanosleep gettimeofday time
    setitimer getitimer alarm timer_create timer_settime timer_delete timerfd_create
    timerfd_settime timerfd_gettime times""".split():
    LANE[n] = TI
for n in """rt_sigaction rt_sigprocmask rt_sigreturn rt_sigsuspend rt_sigtimedwait
    rt_sigpending rt_sigqueueinfo sigaltstack kill tkill tgkill pause signalfd
    signalfd4 pidfd_send_signal""".split():
    LANE[n] = SI
for n in """socket socketpair bind listen accept accept4 connect getsockname
    getpeername sendto recvfrom sendmsg recvmsg sendmmsg recvmmsg setsockopt
    getsockopt shutdown poll ppoll select pselect6 epoll_create epoll_create1
    epoll_ctl epoll_wait epoll_pwait epoll_pwait2""".split():
    LANE[n] = SO


def load(out):
    t = {}
    for w in WORKLOADS:
        p = os.path.join(out, w, "tally.json")
        if os.path.exists(p):
            t[w] = json.load(open(p))
    return t


def read_csv(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def meta(out, w):
    p = os.path.join(out, w, "o", "meta.txt")
    if not os.path.exists(p):
        return {}
    return dict(kv.split("=", 1) for kv in open(p).read().split() if "=" in kv)


def build(out):
    t = load(out)
    names = sorted({n for r in t.values() for n in r["syscalls"]})
    unassigned = [n for n in names if n not in LANE]
    first_ms = {}
    for ms, _, ws in MILESTONES:
        for w in ws:
            for n in t.get(w, {}).get("syscalls", {}):
                first_ms.setdefault(n, ms)
    inj = {k: {r["syscall"]: r for r in read_csv(os.path.join(out, f"inject-{k}.csv"))}
           for k in ("static", "dynamic")}
    rows = []
    for n in names:
        groups = [g for g in GROUPS if any(n in t[w]["syscalls"] for w in t if GROUP[w] == g)]
        calls = sum(t[w]["syscalls"].get(n, {}).get("calls", 0) for w in t)
        errs = sum(t[w]["syscalls"].get(n, {}).get("errors", 0) for w in t)
        en = Counter()
        for w in t:
            en.update(t[w]["syscalls"].get(n, {}).get("errnos", {}))
        num = next(t[w]["syscalls"][n]["number"] for w in t if n in t[w]["syscalls"])
        rows.append({"syscall": n, "number": num, "workloads": len(groups),
                     "which": " ".join(groups), "calls": calls, "errors": errs,
                     "errnos": " ".join(f"{e}:{c}" for e, c in en.most_common()),
                     "milestone": first_ms[n], "lane": LANE.get(n, "UNASSIGNED"),
                     "enosys_static": inj["static"].get(n, {}).get("verdict", ""),
                     "enosys_dynamic": inj["dynamic"].get(n, {}).get("verdict", "")})
    rows.sort(key=lambda r: (-r["workloads"], -r["calls"], r["syscall"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return t, rows, unassigned, inj


def csv_text(rows, cols):
    b = io.StringIO()
    w = csv.writer(b, lineterminator="\n")
    w.writerow(cols)
    for r in rows:
        w.writerow([r[c] for c in cols])
    return b.getvalue()


def md_table(head, rows):
    s = "| " + " | ".join(head) + " |\n|" + "---|" * len(head) + "\n"
    for r in rows:
        s += "| " + " | ".join(str(c) for c in r) + " |\n"
    return s


def blocks(out, t, rows, inj):
    B = {}
    # summary: one row per traced workload
    s = []
    for w in WORKLOADS:
        if w not in t:
            continue
        r, m = t[w], meta(out, w)
        s.append([f"`{w}`", " ".join(f"`{g}`" for g in r["scope"]), f"{r['processes_in_scope']}/{r['processes_traced']}",
                  len(r["syscalls"]), sum(v["calls"] for v in r["syscalls"].values()),
                  m.get("rc", "?"), r["raw_files"], f"`{r['raw_manifest_sha256'][:12]}…`"])
    union = {n for r in t.values() for n in r["syscalls"]}
    B["summary"] = md_table(["workload", "scope (process images counted)", "processes in scope / traced",
                             "distinct", "calls", "workload rc", "raw files", "raw manifest sha256"], s) + \
        f"\n**Union: {len(union)} distinct system calls** of the {count_table()} the x86-64 table names.\n"
    # the ranked union
    B["union"] = md_table(["#", "syscall", "nr", "workloads", "which", "calls", "errors (errnos)",
                           "first needed", "lane"],
                          [[r["rank"], f"`{r['syscall']}`", r["number"], r["workloads"], r["which"],
                            r["calls"], f"{r['errors']}" + (f" ({short(r['errnos'])})" if r["errnos"] else ""),
                            r["milestone"], r["lane"]] for r in rows])
    # milestones
    seen, ms_rows = set(), []
    for ms, what, ws in MILESTONES:
        new = sorted({n for w in ws for n in t.get(w, {}).get("syscalls", {})} - seen,
                     key=lambda n: (LANES.index(LANE.get(n, PM)) if n in LANE else 9, n))
        seen |= set(new)
        by = {}
        for n in new:
            by.setdefault(LANE.get(n, "UNASSIGNED"), []).append(n)
        ms_rows.append([ms, what, len(new), len(seen),
                        "; ".join(f"**{l}**: " + ", ".join(f"`{n}`" for n in by[l]) for l in LANES + ["UNASSIGNED"] if l in by)])
    B["milestones"] = md_table(["milestone", "workloads", "new calls", "cumulative", "the new calls, by lane"], ms_rows)
    # M-PX3 under ENOSYS
    st = t.get("boreutils-static", {}).get("syscalls", {})
    mrows = []
    for n in sorted(st, key=lambda n: (LANES.index(LANE.get(n, PM)), -st[n]["calls"])):
        v = inj["static"].get(n, {})
        verdict = v.get("verdict", "")
        if n == "execve":
            verdict = "required (the program's own start; strace does not inject it)"
        mrows.append([f"`{n}`", st[n]["number"], LANE.get(n), st[n]["calls"],
                      verdict, f"{v.get('passed', '')}/{v.get('baseline_passed', '')}",
                      v.get("first_failures", "")[:90]])
    B["mpx3"] = md_table(["syscall", "nr", "lane", "calls in the suite", "answered ENOSYS",
                          "cases passing", "first cases lost"], mrows)
    # lanes
    lrows = []
    for l in LANES:
        cell = []
        for ms, _, _ in MILESTONES:
            ns = [r["syscall"] for r in rows if r["lane"] == l and r["milestone"] == ms]
            cell.append(", ".join(f"`{n}`" for n in sorted(ns)) or "—")
        lrows.append([l] + cell + [sum(1 for r in rows if r["lane"] == l)])
    B["lanes"] = md_table(["lane"] + [m for m, _, _ in MILESTONES] + ["total"], lrows)
    # paths
    pr = read_csv(os.path.join(out, "paths.csv"))
    paths = {}
    for r in pr:
        paths.setdefault(r["path"], set()).add(GROUP.get(r["workload"], r["workload"]))
    B["paths"] = md_table(["path", "workloads"], [[f"`{p}`", " ".join(g for g in GROUPS if g in ws)]
                                                  for p, ws in sorted(paths.items())])
    # ioctls and other operations
    ops = read_csv(os.path.join(out, "ops.csv"))
    agg = {}
    for r in ops:
        k = (r["syscall"], r["operation"])
        a = agg.setdefault(k, [0, set()])
        a[0] += int(r["calls"])
        a[1].add(GROUP.get(r["workload"], r["workload"]))
    B["ioctls"] = md_table(["request on", "calls", "workloads"],
                           [[f"`{op}`", a[0], " ".join(g for g in GROUPS if g in a[1])]
                            for (sc, op), a in sorted(agg.items(), key=lambda kv: (-kv[1][0], kv[0])) if sc == "ioctl"])
    other = {}
    for (sc, op), a in agg.items():
        if sc == "ioctl":
            continue
        other.setdefault(sc, []).append((op, a[0]))
    B["ops"] = md_table(["syscall", "operations seen (calls)"],
                        [[f"`{sc}`", ", ".join(f"`{op}` {c}" for op, c in sorted(v, key=lambda x: -x[1])[:14])
                          + (f", … {len(v) - 14} more" if len(v) > 14 else "")]
                         for sc, v in sorted(other.items())])
    # auxv
    ax = read_csv(os.path.join(out, "auxv.csv"))
    subjects = []
    for r in ax:
        if r["subject"] not in subjects:
            subjects.append(r["subject"])
    entries = []
    for r in ax:
        if r["entry"] not in entries:
            entries.append(r["entry"])
    cell = {(r["subject"], r["entry"]): r for r in ax}
    arows = []
    for e in entries:
        need = [s for s in subjects if cell.get((s, e), {}).get("when_hidden") == "required"]
        how = []
        for s in need:
            c = cell[(s, e)]
            how.append(f"{s} ({'signal ' + c['exitsignal'] if c['exitsignal'] else 'exit ' + str(c['exitcode'])})")
        arows.append([f"`{e}`", len(need), ", ".join(how) or "—"])
    arows.sort(key=lambda r: (-r[1], r[0]))
    B["auxv"] = md_table(["entry", "subjects that fail without it", "which (how they fail)"], arows) + \
        f"\nSubjects ({len(subjects)}): " + ", ".join(f"`{s}`" for s in subjects) + ".\n"
    vd = read_csv(os.path.join(out, "vdso.csv"))
    vrows = []
    calls = ["clock_gettime", "gettimeofday", "time", "getcpu", "clock_getres", "getrandom"]
    for s in subjects:
        pres = next((r for r in vd if r["subject"] == s and r["vdso"] == "present"), None)
        hid = next((r for r in vd if r["subject"] == s and r["vdso"] == "hidden"), None)
        if not pres or not hid:
            continue
        diff = [f"`{c}` {pres[c]} → {hid[c]}" for c in calls if pres[c] != hid[c]]
        same = pres["stdout16"] == hid["stdout16"] and pres["exitcode"] == hid["exitcode"]
        vrows.append([f"`{s}`", ", ".join(diff) or "no change", "same" if same else f"differs (exit {hid['exitcode']})"])
    B["vdso"] = md_table(["subject", "system calls with the vDSO → without it", "result without it"], vrows)
    return B


def short(errnos, k=3):
    parts = errnos.split()
    return " ".join(parts[:k]) + (" …" if len(parts) > k else "")


def count_table():
    here = os.path.dirname(os.path.abspath(__file__))
    return sum(1 for l in open(os.path.join(here, "syscall_64.csv")) if l[:1].isdigit())


def render_doc(doc_text, B):
    def sub(m):
        name = m.group(1)
        if name not in B:
            raise SystemExit(f"report: DOC has a block `{name}` this script does not make")
        return f"<!-- census:{name} -->\n{B[name]}<!-- /census:{name} -->"
    return re.sub(r"<!-- census:([a-z0-9]+) -->\n.*?<!-- /census:\1 -->", sub, doc_text, flags=re.S)


def main(argv):
    out, doc = argv[0], argv[1]
    check = "--check" in argv
    t, rows, unassigned, inj = build(out)
    if unassigned:
        raise SystemExit(f"report: no lane for {unassigned}")
    files = {
        os.path.join(out, "union.csv"): csv_text(rows, ["rank", "syscall", "number", "workloads", "which",
                                                       "calls", "errors", "errnos", "milestone", "lane",
                                                       "enosys_static", "enosys_dynamic"]),
    }
    B = blocks(out, t, rows, inj)
    files[doc] = render_doc(open(doc).read(), B)
    bad = 0
    for p, text in files.items():
        if check:
            have = open(p).read() if os.path.exists(p) else None
            if have != text:
                print(f"report: {p} is STALE (regenerate: python3 tools/census/report.py {out} {doc})")
                bad = 1
            else:
                print(f"report: {p} matches")
        else:
            with open(p, "w") as f:
                f.write(text)
            print(f"report: wrote {p}")
    print(f"report: {len(rows)} distinct; top 5: " + ", ".join(r["syscall"] for r in rows[:5]))
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
