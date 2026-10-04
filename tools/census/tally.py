#!/usr/bin/env python3
"""tally.py — px04's census: raw strace output -> per-workload tallies.

    python3 tally.py OUT W [W ...]

For each workload W, reads OUT/W/o/raw/t.<pid> (strace -ff -q -y -s 128),
attributes every system call to the PROCESS IMAGE that made it, keeps the
calls whose image matches the workload's SCOPE (tools/census/workloads/
W.sh), and writes:

    OUT/W/tally.json   calls, errors and errnos per syscall; images;
                       /proc and /dev paths; ioctl and other sub-operations;
                       the raw trace digest; strace -c's whole-tree names
    OUT/W.csv          syscall,number,calls,errors,errnos,first_workload

then OUT/union.csv, OUT/paths.csv, OUT/ops.csv across all workloads (in
the order given, which is the milestone order, so `first_workload` is the
first workload in that order to make the call).

Attribution. A process starts with the image of the process that cloned
it, read at the clone; a successful execve switches it, and the execve
itself belongs to the NEW image (it is how that program starts). A thread
inherits its creator's image the same way. Calls a process makes before
it execs (a fork child's dup2, close, execve attempts along PATH) belong
to the parent's image, so a python harness's fork-and-exec is never
counted as boreutils.

Only strace's own decoded output is read; nothing here is derived from
kernel or C library source.
"""
import csv, fnmatch, glob, hashlib, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
OPS = {  # syscall -> argument indexes whose decoded token is an "operation"
    "ioctl": (1,), "fcntl": (1,), "futex": (1,), "prctl": (0,),
    "arch_prctl": (0,), "socket": (0, 1), "setsockopt": (1, 2),
    "getsockopt": (1, 2), "madvise": (2,), "rt_sigaction": (0,),
    "clock_gettime": (0,), "clock_nanosleep": (0,), "socketpair": (0,),
}
# Calls whose arguments include a PATH (the /proc and /dev census reads
# only these, so a buffer that happens to start "/dev" is never a path).
PATHCALLS = set("""open openat openat2 creat stat lstat newfstatat statx access faccessat
    faccessat2 readlink readlinkat execve execveat chdir mkdir mkdirat rmdir unlink
    unlinkat rename renameat renameat2 link linkat symlink symlinkat chmod fchmodat
    fchmodat2 chown lchown fchownat truncate utimensat utime utimes statfs
    inotify_add_watch mknod mknodat getxattr lgetxattr setxattr lsetxattr listxattr
    llistxattr removexattr name_to_handle_at mount umount2 chroot swapon""".split())
RET = re.compile(r"\)\s+= ")
CALL = re.compile(r"^(\w+)\((.*)$")
RESUMED = re.compile(r"^<\.\.\. (\w+) resumed>(.*)$")
ERRNO = re.compile(r"^[A-Z][A-Z0-9_]+$")
FDDECOR = re.compile(r"<([^<>]*)>")


def load_table():
    nums = {}
    with open(os.path.join(HERE, "syscall_64.csv")) as f:
        rows = [l for l in f if not l.startswith("#")]
    for r in csv.DictReader(rows):
        nums[r["name"]] = int(r["number"])
    return nums


def scope_of(w):
    with open(os.path.join(HERE, "workloads", w + ".sh")) as f:
        for line in f:
            m = re.match(r"^SCOPE='([^']*)'", line)
            if m:
                return m.group(1).split()
    raise SystemExit(f"tally: workloads/{w}.sh has no SCOPE")


def split_args(s):
    """Split strace's argument text at top-level commas (quotes, brackets)."""
    out, depth, cur, q, esc = [], 0, [], False, False
    for ch in s:
        if q:
            cur.append(ch)
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': q = False
            continue
        if ch == '"': q = True; cur.append(ch); continue
        if ch in "([{": depth += 1
        elif ch in ")]}":
            if depth == 0: break
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip()); cur = []; continue
        cur.append(ch)
    tail = "".join(cur).strip()
    if tail: out.append(tail)
    return out


def parse_ret(rest):
    """rest is the text after ') = '. -> (value, errno or None)."""
    toks = rest.split()
    if not toks: return None, None
    val = FDDECOR.sub("", toks[0])
    err = toks[1] if len(toks) > 1 and ERRNO.match(toks[1]) else None
    if val not in ("-1", "?"):
        err = None
    return val, err


def norm_path(p):
    p = re.sub(r"^/proc/\d+", "/proc/[pid]", p)
    p = re.sub(r"/task/\d+", "/task/[tid]", p)
    p = re.sub(r"/fd/\d+$", "/fd/[n]", p)
    p = re.sub(r"/fdinfo/\d+$", "/fdinfo/[n]", p)
    p = re.sub(r"^/dev/pts/\d+$", "/dev/pts/[n]", p)
    p = re.sub(r"^/dev/fd/\d+$", "/dev/fd/[n]", p)
    p = re.sub(r"^/dev/tty\d+$", "/dev/tty[n]", p)
    return p


def fd_class(decor):
    if decor.startswith("socket:"): return "socket"
    if decor.startswith("pipe:"): return "pipe"
    if decor.startswith("anon_inode:"): return decor.split("[")[0]
    if decor.startswith("/dev/") or decor.startswith("/proc/"): return norm_path(decor)
    if decor.startswith("/"): return "a regular file"
    return decor or "?"


def parse_file(path):
    """-> list of events: (kind, name, args, value, errno)."""
    ev, pending = [], {}
    with open(path, errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("+++") or line.startswith("---"):
                ev.append(("note", line, "", None, None)); continue
            m = RESUMED.match(line)
            if m:
                name, rest = m.group(1), m.group(2)
                i = pending.pop(name, None)
                ms = list(RET.finditer(rest))
                val, err = parse_ret(rest[ms[-1].end():]) if ms else (None, None)
                if i is not None:
                    k, n, a, _, _ = ev[i]
                    ev[i] = (k, n, a + rest, val, err)
                continue
            m = CALL.match(line)
            if not m:
                continue
            name, rest = m.group(1), m.group(2)
            if "<unfinished ...>" in rest:
                pending[name] = len(ev)
                ev.append(("call", name, rest.replace("<unfinished ...>", ""), None, None))
                continue
            ms = list(RET.finditer(line))
            val, err = parse_ret(line[ms[-1].end():]) if ms else (None, None)
            ev.append(("call", name, rest, val, err))
    return ev


def tally(out, w, nums):
    raw = sorted(glob.glob(os.path.join(out, w, "o", "raw", "t.*")),
                 key=lambda p: int(p.rsplit(".", 1)[1]))
    if not raw:
        raise SystemExit(f"tally: no raw trace for {w}")
    manifest = hashlib.sha256()
    procs = {}
    for p in raw:
        with open(p, "rb") as f:
            manifest.update(f"{os.path.basename(p)} {hashlib.sha256(f.read()).hexdigest()}\n".encode())
        procs[int(p.rsplit(".", 1)[1])] = parse_file(p)

    # Who cloned whom, and at which event.
    parent = {}
    reused = 0
    for pid, ev in procs.items():
        for i, (k, name, args, val, err) in enumerate(ev):
            if k == "call" and name in ("clone", "clone3", "fork", "vfork") and val and val.isdigit():
                child = int(val)
                if child in parent:
                    reused += 1
                parent[child] = (pid, i)
    for pid, ev in procs.items():
        exits = [i for i, e in enumerate(ev) if e[0] == "note" and e[1].startswith("+++")]
        if exits and exits[0] < len(ev) - 1 and any(e[0] == "call" for e in ev[exits[0]:]):
            reused += 1

    memo = {}

    def image_at(pid, idx):
        ev = procs.get(pid, [])
        img = None
        for i in range(min(idx, len(ev)) - 1, -1, -1):
            k, name, args, val, err = ev[i]
            if k == "call" and name in ("execve", "execveat") and val == "0":
                img = exec_path(name, args)
                break
        if img is None:
            img = initial(pid)
        return img

    def initial(pid):
        if pid in memo:
            return memo[pid]
        memo[pid] = "<root>"
        if pid in parent:
            pp, i = parent[pid]
            memo[pid] = image_at(pp, i)
        return memo[pid]

    scope = scope_of(w)
    inscope = lambda img: any(fnmatch.fnmatchcase(img, g) for g in scope)
    sc = defaultdict(lambda: {"calls": 0, "errors": 0, "errnos": Counter()})
    images, excluded = Counter(), Counter()
    paths = defaultdict(Counter)
    ops = defaultdict(Counter)
    nprocs = set()
    for pid, ev in procs.items():
        img = initial(pid)
        for k, name, args, val, err in ev:
            if k != "call":
                continue
            if name in ("execve", "execveat") and val == "0":
                img = exec_path(name, args)
            if not inscope(img):
                excluded[img] += 1
                continue
            nprocs.add(pid)
            images[img] += 1
            s = sc[name]
            s["calls"] += 1
            if err:
                s["errors"] += 1
                s["errnos"][err] += 1
            a = split_args(args)
            for arg in (a if name in PATHCALLS else ()):
                if arg.startswith('"/proc') or arg.startswith('"/dev'):
                    paths[norm_path(arg.strip('"').rstrip("."))][name] += 1
            if name in OPS:
                for j in OPS[name]:
                    if j < len(a):
                        tok = FDDECOR.sub("", a[j]) if j else a[j]
                        if name == "ioctl" and j == 1:
                            m = FDDECOR.search(a[0])
                            tok = f"{tok} on {fd_class(m.group(1)) if m else '?'}"
                        if name == "rt_sigaction" and not tok.startswith("SIG"):
                            continue
                        ops[name][tok[:80]] += 1
    tree = Counter()
    for sp in glob.glob(os.path.join(out, w, "c", "c", "summary.*")):
        with open(sp) as f:
            for line in f:
                t = line.split()
                if len(t) >= 5 and re.match(r"^\d+\.\d+$", t[0]) and t[-1] not in ("total",):
                    calls = int(t[3])
                    tree[t[-1]] += calls
    unknown = sorted(n for n in sc if n not in nums)
    res = {
        "workload": w, "scope": scope, "processes_in_scope": len(nprocs),
        "processes_traced": len(procs), "pid_reuse": reused,
        "raw_files": len(raw), "raw_manifest_sha256": manifest.hexdigest(),
        "syscalls": {n: {"number": nums.get(n), "calls": v["calls"], "errors": v["errors"],
                         "errnos": dict(v["errnos"].most_common())} for n, v in sorted(sc.items())},
        "images": dict(images.most_common()), "excluded_images": dict(excluded.most_common(40)),
        "paths": {p: dict(c) for p, c in sorted(paths.items())},
        "ops": {n: dict(c.most_common()) for n, c in sorted(ops.items())},
        "tree_c": dict(tree.most_common()),
        "scoped_not_in_tree_c": sorted(n for n in sc if tree and n not in tree
                                       and n not in ("exit", "exit_group")),  # strace -c lists no call that never returns
        "unknown_names": unknown,
    }
    with open(os.path.join(out, w, "tally.json"), "w") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    return res


def exec_path(name, args):
    a = split_args(args)
    i = 1 if name == "execveat" else 0
    return a[i].strip('"') if len(a) > i else "?"


def main(argv):
    out, ws = argv[0], argv[1:]
    nums = load_table()
    res = {}
    for w in ws:
        if not os.path.isdir(os.path.join(out, w, "o", "raw")):
            print(f"tally: {w}: no trace, skipped")
            continue
        r = tally(out, w, nums)
        res[w] = r
        print(f"tally: {w}: {len(r['syscalls'])} distinct, "
              f"{sum(v['calls'] for v in r['syscalls'].values())} calls in scope, "
              f"{r['processes_in_scope']}/{r['processes_traced']} processes, "
              f"reuse={r['pid_reuse']}, unknown={r['unknown_names']}, "
              f"not-in-c={r['scoped_not_in_tree_c']}")
    first = {}
    for w in ws:
        for n in res.get(w, {}).get("syscalls", {}):
            first.setdefault(n, w)
    for w, r in res.items():
        with open(os.path.join(out, w + ".csv"), "w", newline="") as f:
            cw = csv.writer(f, lineterminator="\n")
            cw.writerow(["syscall", "number", "calls", "errors", "errnos", "first_workload"])
            rows = sorted(r["syscalls"].items(), key=lambda kv: (-kv[1]["calls"], kv[0]))
            for n, v in rows:
                cw.writerow([n, v["number"] if v["number"] is not None else "", v["calls"], v["errors"],
                             " ".join(f"{e}:{c}" for e, c in v["errnos"].items()), first[n]])
    with open(os.path.join(out, "paths.csv"), "w", newline="") as f:
        cw = csv.writer(f, lineterminator="\n")
        cw.writerow(["workload", "path", "syscalls"])
        for w, r in res.items():
            for p, c in r["paths"].items():
                cw.writerow([w, p, " ".join(f"{n}:{k}" for n, k in sorted(c.items()))])
    with open(os.path.join(out, "ops.csv"), "w", newline="") as f:
        cw = csv.writer(f, lineterminator="\n")
        cw.writerow(["workload", "syscall", "operation", "calls"])
        for w, r in res.items():
            for n, c in r["ops"].items():
                for op, k in c.items():
                    cw.writerow([w, n, op, k])


if __name__ == "__main__":
    main(sys.argv[1:])
