# px25: the maintainer's commands typed into a pseudo-terminal on nomad-1,
# exactly as written in the note (fish's first terminal: QEMU; second: curl).
import os, pty, subprocess, time, sys, re
iso = sys.argv[1]; out = sys.argv[2]
cmd = ["qemu-system-x86_64", "-machine", "q35", "-m", "256M", "-display", "none", "-serial", "mon:stdio",
       "-no-reboot", "-cdrom", iso, "-nic", "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:8380-:80"]
m, s = pty.openpty()
q = subprocess.Popen(cmd, stdin=s, stdout=s, stderr=s, close_fds=True)
log = open(out, "wb")
buf = b""
def pump(t):
    global buf
    end = time.time() + t
    while time.time() < end:
        import select
        r, _, _ = select.select([m], [], [], 0.1)
        if r:
            d = os.read(m, 65536); buf += d; log.write(d); log.flush()
def wait(rx, t=120):
    end = time.time() + t
    while time.time() < end:
        pump(0.2)
        if re.search(rx, buf): return True
    return False
def typ(line):
    for ch in (line + "\r").encode():
        os.write(m, bytes([ch])); time.sleep(0.02)
try:
    t0 = time.time()
    ok = wait(rb"\$ $", 120); print("prompt", ok, "%.1f s" % (time.time() - t0))
    typ("cd /srv"); typ("lobo -c conf/lobo.conf serve &")
    print("serving", wait(rb"generation-activated gen=1", 60))
    time.sleep(1)
    r = subprocess.run("curl -s http://127.0.0.1:8380/ | cmp - " + sys.argv[3] + " && echo same", shell=True, capture_output=True, text=True)
    print("curl:", r.stdout.strip(), r.stderr.strip())
    typ("cat logs/access.log"); pump(2)
    typ("lobo -s stop -c conf/lobo.conf"); print("stopped", wait(rb"stop: shutting down", 60))
    typ("exit"); print("halt", wait(rb"\nhalt", 60))
    os.write(m, b"\x01x")
    for _ in range(50):
        if q.poll() is not None: break
        time.sleep(0.1)
    print("Ctrl-A x: qemu", "ended by itself, status %s" % q.returncode if q.poll() is not None else "still running")
finally:
    q.kill(); q.wait(); print("qemu ended", q.returncode)
