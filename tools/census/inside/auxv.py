# auxv.py — a gdb script: what does a program need from the auxiliary
# vector, and what does it ask the vDSO for? Black-box: the program is
# stopped at its first instruction (`starti`: ld.so's entry for a dynamic
# binary, _start for a static one), the vector is found on the initial
# stack (argc, argv[], NULL, envp[], NULL, then (type, value) pairs to
# AT_NULL: the x86-64 psABI's process-entry layout), and one entry's TYPE
# is overwritten with AT_IGNORE (1) before the program continues.
#
#   CENSUS_PROBE=list           the vector as the kernel built it
#   CENSUS_PROBE=ignore:<type>  hide one entry; report the exit status
#   CENSUS_PROBE=vdso:<0|1>     1 hides AT_SYSINFO_EHDR; either way count
#                               the time/cpu/random system calls made
#   CENSUS_PROBE=watch:<t,t,..> up to four entries: a hardware access
#                               watchpoint on each one's VALUE word; every
#                               access is recorded with the object and
#                               symbol of the instruction that made it
#
#   CENSUS_PROBE_ARGS='ARGS < in > out' gdb -q -batch -nx -x auxv.py PROG
# (gdb starts the program through the shell, so the arguments and the
# redirections are shell words). Result: one JSON line appended to
# $CENSUS_PROBE_OUT. System call numbers come from syscall_64.csv.
import gdb, json, os, struct

mode = os.environ.get("CENSUS_PROBE", "list")
out = os.environ["CENSUS_PROBE_OUT"]
args = os.environ.get("CENSUS_PROBE_ARGS", "")
NUM = {}
with open(os.environ.get("CENSUS_TABLE", "/census/syscall_64.csv")) as f:
    for line in f:
        parts = line.strip().split(",")
        if len(parts) == 3 and parts[0].isdigit():
            NUM[parts[2]] = int(parts[0])
VDSO_CALLS = ["clock_gettime", "gettimeofday", "time", "getcpu", "clock_getres", "getrandom"]
inf = None


def rd(addr):
    return struct.unpack("<Q", bytes(inf.read_memory(addr, 8)))[0]


def auxv_entries():
    sp = int(gdb.parse_and_eval("$rsp"))
    argc = rd(sp)
    p = sp + 8 * (argc + 2)
    while rd(p) != 0:
        p += 8
    p += 8
    ents = []
    while True:
        t, v = rd(p), rd(p + 8)
        ents.append((p, t, v))
        if t == 0:
            break
        p += 16
    return ents


def names():
    txt = gdb.execute("info auxv", to_string=True)
    m = {}
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit():
            m[int(parts[0])] = parts[1]
    return m


gdb.execute("set pagination off")
gdb.execute("set confirm off")
gdb.execute(f"starti {args}", to_string=True)
inf = gdb.selected_inferior()
ents = auxv_entries()
nm = names()
res = {"mode": mode, "entries": [[nm.get(t, str(t)), t] for _, t, _ in ents if t]}
if mode.startswith("ignore:"):
    want = int(mode.split(":")[1])
    for addr, t, _ in ents:
        if t == want:
            inf.write_memory(addr, struct.pack("<Q", 1))
    res["hidden"] = all(t != want for _, t, _ in auxv_entries())
elif mode.startswith("vdso:"):
    if mode.endswith(":1"):
        for addr, t, _ in ents:
            if t == 33:
                inf.write_memory(addr, struct.pack("<Q", 1))
        res["hidden"] = all(t != 33 for _, t, _ in auxv_entries())
    gdb.execute("catch syscall " + " ".join(VDSO_CALLS), to_string=True)
counts = {}
status = None
reads = {}
wp = {}
last = {"ev": None}
gdb.events.stop.connect(lambda ev: last.__setitem__("ev", ev))
if mode.startswith("watch:"):
    gdb.execute("set can-use-hw-watchpoints 1")
    want = [int(x) for x in mode.split(":")[1].split(",") if x]
    for addr, t, _ in ents:
        if t in want:
            b = gdb.Breakpoint(f"*(unsigned long *){addr + 8}", gdb.BP_WATCHPOINT, gdb.WP_ACCESS, internal=False)
            wp[b.number] = t
hits = 0
while True:
    try:
        gdb.execute("continue", to_string=True)
    except gdb.error as e:
        res["gdb_error"] = str(e)[:200]
        break
    if not inf.pid:
        break
    ev = last["ev"]
    if wp and isinstance(ev, gdb.BreakpointEvent):
        pc = int(gdb.parse_and_eval("$pc"))
        obj = os.path.basename(gdb.solib_name(pc) or "(the executable)")
        sym = gdb.execute(f"info symbol {pc}", to_string=True).split(" in section")[0].split(" + ")[0].strip()
        if sym.startswith("No symbol"):
            sym = hex(pc)  # stripped: the address (gdb runs with ASLR off, so it is stable)
        for b in ev.breakpoints:
            if b.number in wp:
                reads.setdefault(wp[b.number], set()).add(f"{obj}:{sym}")
        hits += 1
        if hits > 400:
            for b in list(gdb.breakpoints() or []):
                b.delete()
            wp = {}
        continue
    # a stop: a syscall catchpoint (entry and return both stop), or a signal
    try:
        orig = int(gdb.parse_and_eval("$orig_rax"))
        rax = int(gdb.parse_and_eval("$rax"))
    except gdb.error:
        break
    if rax == -38 or rax == 0xffffffffffffffda:  # -ENOSYS in rax marks a syscall ENTRY on x86-64
        counts[orig] = counts.get(orig, 0) + 1
try:
    status = int(gdb.parse_and_eval("$_exitcode"))
except gdb.error:
    status = None
try:
    res["exitsignal"] = int(gdb.parse_and_eval("$_exitsignal"))
except gdb.error:
    pass
res["exitcode"] = status
if mode.startswith("watch:"):
    res["reads"] = {str(t): sorted(v) for t, v in reads.items()}
if mode.startswith("vdso:"):
    res["syscalls"] = {n: counts.get(NUM[n], 0) for n in VDSO_CALLS}
with open(out, "a") as f:
    f.write(json.dumps(res) + "\n")
