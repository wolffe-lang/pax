# px62 debug only: sample RIP and CR3 through QEMU's monitor socket,
# with the serial log's size, until the socket goes away.
import socket, sys, time, re, os
sock_path, serial, out = sys.argv[1], sys.argv[2], sys.argv[3]
for _ in range(600):
    try:
        s = socket.socket(socket.AF_UNIX); s.connect(sock_path); break
    except OSError:
        time.sleep(0.1)
else:
    sys.exit("no socket")
s.settimeout(2)
f = open(out, "w")
buf = b""
def cmd(c):
    global buf
    s.sendall(c.encode() + b"\n")
    data = b""
    t0 = time.time()
    while b"HLT=" not in data and time.time() - t0 < 2:
        try:
            ch = s.recv(65536)
        except socket.timeout:
            break
        if not ch:
            raise EOFError
        data += ch
    return data.decode("latin1")
try:
    cmd("")
    while True:
        d = cmd("info registers")
        rip = re.search(r"RIP=([0-9a-f]+)", d); cr3 = re.search(r"CR3=([0-9a-f]+)", d); rfl = re.search(r"RFL=([0-9a-f]+)", d)
        try:
            sz = os.path.getsize(serial)
        except OSError:
            sz = -1
        f.write("%.3f %s %s %s %d\n" % (time.monotonic(), rip.group(1) if rip else "-", cr3.group(1) if cr3 else "-", rfl.group(1) if rfl else "-", sz))
        f.flush()
        time.sleep(0.02)
except (EOFError, OSError, BrokenPipeError):
    pass
