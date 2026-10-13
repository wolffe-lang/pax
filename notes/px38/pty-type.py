#!/usr/bin/env python3
# px38: type into a program that wants a terminal (login), waiting for
# each prompt before the answer, so the program's own flush of typed-ahead
# input loses nothing.
#
#   pty-type.py OUT 'PROMPT=ANSWER'... -- PROG [ARG...]
#
# Each PROMPT is waited for in what the terminal shows (in order), then
# ANSWER and a newline are typed. OUT gets what the terminal showed.
# Exit: the program's status.
import os
import pty
import select
import sys
import time

out = sys.argv[1]
i = sys.argv.index("--")
steps = [a.split("=", 1) for a in sys.argv[2:i]]
argv = sys.argv[i + 1:]
pid, fd = pty.fork()
if pid == 0:
    os.execvp(argv[0], argv)
seen = b""
shown = b""
deadline = time.time() + 90
while steps and time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 1.0)
    if r:
        try:
            d = os.read(fd, 4096)
        except OSError:
            break
        if not d:
            break
        seen += d
        shown += d
    if steps and steps[0][0].encode() in seen:
        time.sleep(0.3)
        os.write(fd, steps[0][1].encode() + b"\n")
        seen = b""
        steps.pop(0)
end = time.time() + 20
while time.time() < end:
    r, _, _ = select.select([fd], [], [], 1.0)
    if r:
        try:
            d = os.read(fd, 4096)
        except OSError:
            break
        if not d:
            break
        shown += d
    else:
        p, st = os.waitpid(pid, os.WNOHANG)
        if p:
            open(out, "wb").write(shown)
            sys.exit(os.waitstatus_to_exitcode(st))
open(out, "wb").write(shown)
# the terminal closed (the program ended) or the time ran out
for _ in range(50):
    p, st = os.waitpid(pid, os.WNOHANG)
    if p:
        sys.exit(os.waitstatus_to_exitcode(st))
    time.sleep(0.1)
os.kill(pid, 9)
os.waitpid(pid, 0)
sys.exit(124)
