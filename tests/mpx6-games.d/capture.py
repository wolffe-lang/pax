#!/usr/bin/env python3
"""tests/mpx6-games' Linux side (gm01): a game's real binary on a Linux
pseudo-terminal, the frame it holds captured.

  capture.py OUT ROWS COLS QUIET HOME -- PROG [ARG...]

PROG runs on a fresh pseudo-terminal of ROWS by COLS, its own session
and the terminal's foreground (setsid and TIOCSCTTY, as a login does),
with PAX's console environment (`HOME=HOME TERM=linux PAX=1 PATH=/bin`,
nothing else: kernel/kmain_console.lu's). What it writes is read until
QUIET seconds pass with no byte (the frame it holds: a lair game writes
nothing while its frame does not change); OUT.frame gets those bytes.
Then `q` is typed (one byte into the terminal, never a signal), the rest
read to the program's end, and OUT the whole transcript, OUT.rc the exit
status. A program still running 60 s after the `q`, or one that never
goes quiet within 600 s, is a failure (exit 1; the program is left to the
container's end, never signalled from here). Exit 0 otherwise, 2 on a
usage error. Run inside a throwaway container (tests/mpx6-games): the
game writes under HOME and nowhere else."""
import fcntl
import os
import select
import struct
import sys
import termios
import time


def main():
    a = sys.argv[1:]
    if len(a) < 7 or a[5] != "--":
        sys.stderr.write(__doc__)
        sys.exit(2)
    out, rows, cols, quiet, home = a[0], int(a[1]), int(a[2]), float(a[3]), a[4]
    argv = a[6:]
    os.makedirs(home, exist_ok=True)
    env = {"HOME": home, "TERM": "linux", "PAX": "1", "PATH": "/bin"}
    master, slave = os.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    pid = os.fork()
    if pid == 0:
        os.close(master)
        os.setsid()
        fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
        for fd in (0, 1, 2):
            os.dup2(slave, fd)
        if slave > 2:
            os.close(slave)
        os.chdir(home)
        os.execve(argv[0], argv, env)
    os.close(slave)
    data = bytearray()
    last = time.monotonic()
    start = last
    frame = None
    typed_at = None
    status = None
    while True:
        r, _, _ = select.select([master], [], [], 0.05)
        if r:
            try:
                b = os.read(master, 65536)
            except OSError:
                b = b""
            if b:
                data += b
                last = time.monotonic()
        now = time.monotonic()
        if frame is None and data and now - last >= quiet:
            frame = bytes(data)
            os.write(master, b"q")
            typed_at = now
        if frame is None and now - start > 600:
            sys.stderr.write("capture: %s never went quiet for %.1f s in 600 s\n" % (argv[0], quiet))
            break
        done, st = os.waitpid(pid, os.WNOHANG)
        if done:
            status = st
            # what is left in the terminal's buffer
            while True:
                r, _, _ = select.select([master], [], [], 0.2)
                if not r:
                    break
                try:
                    b = os.read(master, 65536)
                except OSError:
                    break
                if not b:
                    break
                data += b
            break
        if typed_at is not None and now - typed_at > 60:
            sys.stderr.write("capture: %s still running 60 s after q\n" % argv[0])
            break
    open(out, "wb").write(bytes(data))
    if frame is not None:
        open(out + ".frame", "wb").write(frame)
    rc = None if status is None else (os.WEXITSTATUS(status) if os.WIFEXITED(status) else 128 + os.WTERMSIG(status))
    open(out + ".rc", "w").write("%s\n" % rc)
    print("capture: %s: %d bytes, the frame %s, status %s" % (
        " ".join(argv), len(data), "%d bytes" % len(frame) if frame is not None else "never quiet", rc))
    sys.exit(0 if frame is not None and rc == 0 else 1)


main()
