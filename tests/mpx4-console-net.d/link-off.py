#!/usr/bin/env python3
"""tests/mpx4-console-net.d/link-off.py SOCKET LOG — the no-link way's
second QEMU monitor (px105).

The machine was started paused (-S) with a human monitor on the unix
socket SOCKET (`-chardev socket,…,server=on,wait=off -mon
chardev=…,mode=readline`), beside tools/qemu-halt's own. This waits for
the socket (30 s at most), then types `set_link n0 off`, `info network`
and `cont`, each answered by the monitor's prompt, so the guest's first
cycle runs with the network's link already down. Everything the monitor
said goes to LOG. Exit 0 when all three were answered, 1 otherwise.
"""
import socket
import sys
import time

path, log = sys.argv[1], sys.argv[2]
out = open(log, "w")
s = None
for _ in range(300):
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(path)
        break
    except OSError:
        s = None
        time.sleep(0.1)
if s is None:
    out.write("link-off: no monitor socket at %s\n" % path)
    sys.exit(1)
s.settimeout(10)


def until_prompt():
    got = b""
    while not got.endswith(b"(qemu) "):
        b = s.recv(4096)
        if not b:
            raise EOFError("the monitor closed")
        got += b
    return got.decode("latin-1")


try:
    out.write(until_prompt())
    for cmd in ("set_link n0 off", "info network", "cont"):
        s.sendall(cmd.encode() + b"\n")
        out.write(until_prompt())
except (OSError, EOFError) as e:
    out.write("\nlink-off: %s\n" % e)
    sys.exit(1)
s.close()
out.write("\nlink-off: set_link n0 off, cont: done\n")
