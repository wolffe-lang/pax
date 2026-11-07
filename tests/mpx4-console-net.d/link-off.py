#!/usr/bin/env python3
"""tests/mpx4-console-net.d/link-off.py SOCKET LOG — the no-link way's
second QEMU monitor (px105).

The machine was started paused (-S) with a human monitor on the unix
socket SOCKET (`-chardev socket,…,server=on,wait=off -mon
chardev=…,mode=readline`), beside tools/qemu-halt's own. This waits for
the socket (30 s at most), then types `cont` and, 0.3 s later, while the
firmware still runs and long before the kernel resets the controller,
`set_link nic0 off`, `set_link n0 off` and `info network`, each answered
by the monitor's prompt. Measured (notes/px105/probe2.txt): QEMU's igb
with its link set down before `cont` shows a link again 1.5 s after the
driver's PHY restart; set down this way it shows none for the driver's
whole 10 s wait. Everything the monitor said goes to LOG. Exit 0 when
every command was answered, 1 otherwise.
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
    for cmd in ("cont", "sleep", "set_link nic0 off", "set_link n0 off", "info network"):
        if cmd == "sleep":
            time.sleep(0.3)
            continue
        s.sendall(cmd.encode() + b"\n")
        out.write(until_prompt())
except (OSError, EOFError) as e:
    out.write("\nlink-off: %s\n" % e)
    sys.exit(1)
s.close()
out.write("\nlink-off: cont, then set_link nic0 off and n0 off: done\n")
