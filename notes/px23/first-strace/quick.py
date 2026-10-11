# quick.py — a first strace of the TCP witnesses on Linux, before the design (px23): one
# network namespace whose loopback also holds 10.0.2.15 and 10.0.2.2, and socket-level
# stand-ins for the other ends.   quick.py BIN OUT
import os, fcntl, struct, socket, ctypes, sys, subprocess, threading, time, zlib
libc = ctypes.CDLL(None, use_errno=True)
assert libc.unshare(0x40000000) == 0
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def sa(ip): return struct.pack("H2s4s8x", socket.AF_INET, b"\0\0", socket.inet_aton(ip))
fl = struct.unpack("16sH22x", fcntl.ioctl(s, 0x8913, struct.pack("16sH22x", b"lo", 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sH22x", b"lo", fl | 1))
for i, ip in enumerate(("10.0.2.15", "10.0.2.2")):
    n = b"lo:%d" % (i + 1)
    fcntl.ioctl(s, 0x8916, struct.pack("16s16s", n, sa(ip)))
    fcntl.ioctl(s, 0x891c, struct.pack("16s16s", n, sa("255.255.255.255")))
out = sys.argv[2]
def pattern(off, n):
    b = bytearray(n)
    for i in range(n):
        o = off + i; r = o >> 10; j = o & 1023
        b[i] = (r >> (8 * j)) & 0xff if j < 8 else (r * 31 + j * 7) & 0xff
    return bytes(b)
def rd_all(c):
    d = b""
    while True:
        x = c.recv(65536)
        if not x: return d
        d += x
def echo_conn(c):
    n = 0; crc = 0
    while True:
        x = c.recv(65536)
        if not x: break
        n += len(x); crc = zlib.crc32(x, crc); c.sendall(x)
    c.sendall(b"eof after %d bytes, crc %08x\n" % (n, crc)); c.close()
def tcp_server(port, fn):
    l = socket.socket(); l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); l.bind(("10.0.2.2", port)); l.listen(16)
    def loop():
        while True:
            c, _ = l.accept(); fn(c)
    threading.Thread(target=loop, daemon=True).start()
def bulk_rx(c):
    d = rd_all(c); c.sendall(b"got %d bytes, crc %08x\n" % (len(d), zlib.crc32(d))); c.close()
def rst(c):
    c.recv(100); c.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)); c.close()
def ready():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.bind(("10.0.2.2", 9099))
    v = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); v.bind(("10.0.2.2", 9098))
    import select
    while True:
        r, _, _ = select.select([u, v], [], [])
        for x in r:
            d, a = x.recvfrom(100)
            if x is u:
                for p in (b"a", pattern(0, 3000), b"quit"):
                    c = socket.socket(); c.bind(("10.0.2.2", 0)); c.connect(("10.0.2.15", 7)); c.sendall(p); c.shutdown(socket.SHUT_WR); rd_all(c); c.close()
            else:
                c = socket.socket(); c.bind(("10.0.2.2", 0)); c.connect(("10.0.2.15", 7100)); c.sendall(pattern(0, 100000)); c.shutdown(socket.SHUT_WR); print("bulk rx says", rd_all(c)); c.close()
def gate(c):
    c.close()
def wolf_up(c):
    c.recv(100); c.close()
    w = socket.socket(); w.bind(("10.0.2.2", 0)); w.connect(("10.0.2.15", 7070)); w.sendall(b"hello wolf\n")
    tcp_server(9071, gate)
    print("wolf says", rd_all(w)); w.close()
tcp_server(9099, echo_conn); tcp_server(9100, bulk_rx); tcp_server(9301, rst); tcp_server(9070, wolf_up)
threading.Thread(target=ready, daemon=True).start()
time.sleep(0.2)
B = sys.argv[1]
for name, argv in (("tcperr", []), ("tcploop", []), ("tcpecho", ["7", "10.0.2.2", "9099"]), ("tcpecho", ["7", "10.0.2.2", "9099", "fork"]),
                   ("tcpclient", ["10.0.2.2", "9099"]), ("tcpbulk", ["send", "10.0.2.2", "9100", "300000"]), ("tcpbulk", ["recv", "7100", "10.0.2.2", "9098"]),
                   ("tcpbulk", ["loop", "300000"]), ("tcpsoak", ["to", "10.0.2.2", "9099", "20"]), ("tcpsoak", ["loop", "20"]),
                   ("tcpend", ["10.0.2.2", "9"]), ("tcpend", ["10.0.2.2", "9301"]), ("tcpfull", []), ("tcpwolf", []), ("tcpwolfd", [])):
    tag = name + ("-" + argv[0] if argv and not argv[0][0].isdigit() else "") + ("-fork" if "fork" in argv else "")
    p = subprocess.run(["strace", "-f", "-qq", "-s", "48", "-o", "%s/%s.strace" % (out, tag), B + "/" + name] + argv,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    open("%s/%s.out" % (out, tag), "wb").write(p.stdout)
    print("== %s %s -> %d" % (name, " ".join(argv), p.returncode)); sys.stdout.write(p.stdout.decode(errors="replace")); sys.stdout.flush()
