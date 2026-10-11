# zero.py — a datagram sent to 0.0.0.0 on Linux (px22): who receives it, and from whom. In the tap namespace.
import os, sys, socket, errno
sys.dont_write_bytecode = True
sys.path.insert(0, "/pax/tools")
import importlib.machinery, importlib.util
l = importlib.machinery.SourceFileLoader("linux_net", "/pax/tools/linux-net"); spec = importlib.util.spec_from_loader("linux_net", l); m = importlib.util.module_from_spec(spec); l.exec_module(m)
tap = m.namespace()
for bind in ("0.0.0.0", "127.0.0.1", "10.0.2.15"):
    r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); r.bind((bind, 4500)); r.settimeout(0.5)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b"x", ("0.0.0.0", 4500))
    try: d, a = r.recvfrom(10); got = "from %s:%s" % (a[0], "ephemeral" if a[1] >= 32768 else a[1])
    except OSError as e: got = "nothing"
    print("receiver bound %s: %s; the sender is now %s" % (bind, got, s.getsockname()[0]))
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); c.connect(("0.0.0.0", 4500)); print("  connect(0.0.0.0): local %s peer %s" % (c.getsockname()[0], c.getpeername()[0]))
    r.close()
