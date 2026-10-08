#!/usr/bin/env python3
# ptysess.py OUT CMD... : run CMD on a fresh pseudo-terminal, type the
# lines of $KEYS (one per line; "^D" means Ctrl-D) after each "$ " prompt,
# record every byte the terminal shows in OUT.
import os, pty, sys, time, select
out = sys.argv[1]; cmd = sys.argv[2:]
keys = [l.rstrip("\n") for l in open(os.environ["KEYS"])]
pid, fd = pty.fork()
if pid == 0:
    os.execvp(cmd[0], cmd)
buf = b""
def pump(t):
    global buf
    end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try:
                d = os.read(fd, 4096)
            except OSError:
                return False
            if not d: return False
            buf += d
    return True
def wait_prompt(n):
    end = time.time() + 10
    while time.time() < end and buf.count(b"$ ") < n:
        if not pump(0.05): return
n = 1
wait_prompt(n)
for k in keys:
    data = b"\x04" if k == "^D" else (k + "\n").encode()
    for ch in data:
        os.write(fd, bytes([ch])); time.sleep(0.01)
    n += 1
    wait_prompt(n)
pump(1.0)
_, st = os.waitpid(pid, 0)
open(out, "wb").write(buf)
print("status", os.waitstatus_to_exitcode(st))
