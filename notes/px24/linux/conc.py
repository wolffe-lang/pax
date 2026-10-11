import re,sys
# peak number of live threads/processes in a strace -f file
for path in sys.argv[1:]:
    live=set(); peak=0; made=0; first=None
    for raw in open(path, errors="replace"):
        m=re.match(r"^(\d+)\s+(.*)", raw)
        if not m: continue
        pid,rest=m.groups()
        if first is None: first=pid
        if pid not in live:
            live.add(pid); made+=1; peak=max(peak,len(live))
        if rest.startswith("+++ exited") or rest.startswith("+++ killed"): live.discard(pid)
    print(path, "tasks seen", made, "peak live", peak)
