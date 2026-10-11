# quick.py — a first strace of the witnesses on Linux, before the design (px22): one
# network namespace whose loopback also holds 10.0.2.15, 10.0.2.2 and 10.0.2.3, and
# socket-level stand-ins for the echo client, the reversing server and the DNS server.
import os, fcntl, struct, socket, ctypes, sys, subprocess, threading, time
libc = ctypes.CDLL(None, use_errno=True)
assert libc.unshare(0x40000000) == 0
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def sa(ip): return struct.pack("H2s4s8x", socket.AF_INET, b"\0\0", socket.inet_aton(ip))
fl = struct.unpack("16sH22x", fcntl.ioctl(s, 0x8913, struct.pack("16sH22x", b"lo", 0)))[1]
fcntl.ioctl(s, 0x8914, struct.pack("16sH22x", b"lo", fl | 1))
for i, ip in enumerate(("10.0.2.15", "10.0.2.2", "10.0.2.3")):
    n = b"lo:%d" % (i + 1)
    fcntl.ioctl(s, 0x8916, struct.pack("16s16s", n, sa(ip)))
    fcntl.ioctl(s, 0x891c, struct.pack("16s16s", n, sa("255.255.255.255")))
out = sys.argv[2]
def server():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.bind(("10.0.2.2", 9099))
    while True:
        d, a = u.recvfrom(4096)
        if d == b"ready":
            c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); c.bind(("10.0.2.2", 40000)); c.settimeout(5)
            for p in (b"a", b"bc", b"x" * 64, b"quit"):
                c.sendto(p, ("10.0.2.15", 7)); c.recvfrom(4096)
            c.close()
        else:
            u.sendto(d[::-1], a)
def dns():
    u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); u.bind(("10.0.2.3", 53))
    while True:
        q, a = u.recvfrom(4096)
        r = q[:2] + b"\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00" + q[12:] + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + bytes([192, 0, 2, 53])
        u.sendto(r, a)
threading.Thread(target=server, daemon=True).start()
threading.Thread(target=dns, daemon=True).start()
time.sleep(0.2)
for name, argv in (("sockerr", []), ("udploop", []), ("udpecho", ["7", "10.0.2.2", "9099"]), ("udpclient", ["10.0.2.2", "9099"]),
                   ("udpsoak", ["10.0.2.2", "9099", "20"]), ("udpfill", []), ("resolve", ["10.0.2.3", "pax.test"])):
    p = subprocess.run(["strace", "-f", "-qq", "-s", "48", "-o", "%s/%s.strace" % (out, name), sys.argv[1] + "/" + name] + argv,
                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    open("%s/%s.out" % (out, name), "wb").write(p.stdout)
    print("== %s %s -> %d" % (name, " ".join(argv), p.returncode)); sys.stdout.write(p.stdout.decode(errors="replace"))
