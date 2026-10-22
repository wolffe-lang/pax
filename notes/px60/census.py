#!/usr/bin/env python3
"""Trace the dev image compiler in a container; retain every raw observation."""
import pathlib
import hashlib
import os
import pty
import select
import time
import re
import subprocess
import sys

root, output, launcher = sys.argv[1:]
out = pathlib.Path(output)
out.mkdir(parents=True, exist_ok=True)
(out / "wolf.sha256").write_text(hashlib.sha256((pathlib.Path(root) / "usr/bin/wolf").read_bytes()).hexdigest() + "\n")
commands = [("version", ["--version"])]
for name in ("hello", "loop", "signal", "spawn", "exec", "fork", "host", "std"):
    source = f"/usr/share/wolf/{name}.lu"
    commands += [(f"{name}-check", ["check", source]),
                 (f"{name}-typecheck", ["conform-run", "--json", "--phase=typecheck", source]),
                 (f"{name}-fmt", ["fmt", "--check", source]),
                 (f"{name}-run", ["conform-run", "--json", "--checked", source])]
union = {}
for name, args in commands:
    print(f"TRACE {name}", flush=True)
    trace = out / f"{name}.trace"
    master, slave = pty.openpty()
    child = subprocess.Popen(["strace", "-f", "-n", "-s", "256", "-o", str(trace),
                              "python3", "-I", launcher, root, "/usr/bin/wolf", *args],
                             stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    deadline = time.monotonic() + 120
    with (out / f"{name}.out").open("wb") as stdout:
        while True:
            if time.monotonic() > deadline:
                child.kill()  # this process only, inside the container
                child.wait()
                raise TimeoutError(name)
            if not select.select([master], [], [], 1)[0]:
                continue
            try:
                data = os.read(master, 65536)
            except OSError:
                break  # Linux PTY EOF is EIO after the slave closes.
            if not data:
                break
            stdout.write(data)
    os.close(master)
    rc = child.wait(timeout=10)
    (out / f"{name}.err").write_text("stderr is merged into the pseudo-terminal transcript\n")
    (out / f"{name}.rc").write_text(f"{rc}\n")
    active = False
    calls = {}
    for line in trace.read_text().splitlines():
        if 'execve("/usr/bin/wolf"' in line:
            active = True
        if not active:
            continue
        m = re.search(r"\[\s*(\d+)\]\s+(\w+)\(", line)
        if m:
            nr, call = int(m[1]), m[2]
            calls[nr] = call
            union[nr] = call
    (out / f"{name}.calls").write_text("".join(f"{nr} {calls[nr]}\n" for nr in sorted(calls)))
(out / "union.txt").write_text("".join(f"{nr} {union[nr]}\n" for nr in sorted(union)))
print(f"UNION {len(union)} syscalls", flush=True)
