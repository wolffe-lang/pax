# odd.py — what Linux answers three sends (px22): to a broadcast address without SO_BROADCAST,
# and from a socket bound to 127.0.0.1 to an address off the machine. In the tap namespace.
import os, sys, socket, errno, select
sys.dont_write_bytecode = True
sys.path.insert(0, "/pax/tools")
import importlib.machinery, importlib.util
l = importlib.machinery.SourceFileLoader("linux_net", "/pax/tools/linux-net"); spec = importlib.util.spec_from_loader("linux_net", l); m = importlib.util.module_from_spec(spec); l.exec_module(m)
tap = m.namespace()
def tryit(what, bind, dst):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if bind: s.bind(bind)
    try:
        r = s.sendto(b"x" * dst[2] if len(dst) > 2 else b"x", dst[:2]); res = str(r)
    except OSError as e:
        res = "-" + errno.errorcode[e.errno]
    frames = []
    while select.select([tap], [], [], 0.3)[0]:
        f = os.read(tap, 4096)
        if f[12:14] == b"\x08\x00": frames.append("%d bytes %s>%s" % (len(f), socket.inet_ntoa(f[26:30]), socket.inet_ntoa(f[30:34])))
    print("%s: %s; on the wire: %s" % (what, res, frames or "nothing"))
tryit("sendto 10.0.2.255 port 9", None, ("10.0.2.255", 9))
tryit("sendto 255.255.255.255 port 9", None, ("255.255.255.255", 9))
tryit("bound 127.0.0.1, sendto 10.0.2.2 port 9", ("127.0.0.1", 4444), ("10.0.2.2", 9))
tryit("bound 127.0.0.1, sendto 10.0.2.15 port 9", ("127.0.0.1", 4445), ("10.0.2.15", 9))
tryit("bound 10.0.2.15, sendto 127.0.0.1 port 9", ("10.0.2.15", 4446), ("127.0.0.1", 9))
tryit("sendto 0.0.0.0 port 9", None, ("0.0.0.0", 9))
tryit("1473 bytes to 127.0.0.1", None, ("127.0.0.1", 9, 1473))
tryit("1473 bytes to 10.0.2.2", None, ("10.0.2.2", 9, 1473))
