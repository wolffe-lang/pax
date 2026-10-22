#!/usr/bin/env python3
"""Linux-only feasibility front end for the wolf driver's cc argument set."""
import os
import sys
root = "/work/m2/sysroot"
args = []
for arg in sys.argv[1:]:
    if arg in ("-lpthread", "-ldl", "-lm") or arg.startswith("-fuse-ld="):
        continue  # musl provides these interfaces in libc.a.
    if arg.startswith("-Wl,"):
        args.extend(arg[4:].split(","))
    else:
        args.append(arg)
cmd = ["ld.lld", "-static", f"{root}/crt1.o", f"{root}/crti.o",
       "--start-group", *args, f"{root}/libc.a", f"{root}/libunwind.a",
       "--end-group", f"{root}/crtn.o"]
print("M2 LINK " + repr(cmd), file=sys.stderr)
os.execv("/usr/bin/ld.lld", cmd)
