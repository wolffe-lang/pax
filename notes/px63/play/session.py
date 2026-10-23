#!/usr/bin/env python3
"""px63, kasumi: the maintainer's session on the playground, typed at
COM1 (the console reads it as it reads the window's keyboard), on a
QEMU that is allowed to reset (no -no-reboot: reboot(2) restarts the
machine and the same disk boots again), CPUs 0-3, TCG:

    cd; cat > notes.txt (a line, Ctrl-D); ls -l; reboot;
    then, on the second boot: cat notes.txt; exit

    session.py ISO DISK LOG

DISK is a copy (the shipped pax-home.img stays pristine). Exit 0 when
every step's answer came; the checks on the transcript are the
caller's. QEMU is this script's child, killed by its pid at the end.
"""
import os
import re
import subprocess
import sys
import threading
import time

NOTE = "written on PAX, before the reboot"
iso, disk, logp = sys.argv[1:4]
cmd = ["taskset", "-c", "0-3", "qemu-system-x86_64", "-machine", "q35", "-cpu", "max", "-accel", "tcg",
       "-m", "512M", "-display", "none", "-serial", "stdio", "-monitor", "none", "-nic", "none",
       "-cdrom", iso, "-drive", "file=%s,if=none,id=d0,format=raw" % disk, "-device", "virtio-blk-pci,drive=d0"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
with open(logp + ".pid", "w") as f:
    f.write("%d\n" % p.pid)
buf = bytearray()
lock = threading.Lock()
log = open(logp, "wb")


def reader():
    while True:
        b = p.stdout.read1(4096)
        if not b:
            return
        with lock:
            buf.extend(b)
        log.write(b)
        log.flush()


threading.Thread(target=reader, daemon=True).start()


def text():
    with lock:
        return bytes(buf)


def wait(pred, what, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if pred(text()):
            return
        if p.poll() is not None:
            sys.exit("session: QEMU ended waiting for %s" % what)
        time.sleep(0.2)
    p.kill()
    sys.exit("session: no %s within %ds" % (what, timeout))


def typ(s, enter=True):
    for ch in s.encode():
        p.stdin.write(bytes([ch]))
        p.stdin.flush()
        time.sleep(0.02)
    if enter:
        p.stdin.write(b"\r")
        p.stdin.flush()


BANNER = b"PAX: the console"


def prompts_after_boot(n):
    # the prompt ($ ) counted after the n-th boot's banner
    def f(t):
        parts = t.split(BANNER)
        return len(parts) - 1 >= n and parts[n].count(b"$ ")
    return f


t0 = time.time()
step = 0


def at_prompt(boot, k, what):
    wait(lambda t: (prompts_after_boot(boot)(t) or 0) >= k, "prompt %d of boot %d (%s)" % (k, boot, what))
    print("session: %6.1fs boot %d prompt %d: %s" % (time.time() - t0, boot, k, what), flush=True)


at_prompt(1, 1, "cd")
typ("cd")
at_prompt(1, 2, "cat > notes.txt")
typ("cat > notes.txt")
time.sleep(2)
typ(NOTE)
time.sleep(1)
typ("\x04", enter=False)
at_prompt(1, 3, "ls -l")
typ("ls -l")
at_prompt(1, 4, "reboot")
typ("reboot")
wait(lambda t: b"marked clean; restarting" in t, "reboot(2)'s line")
print("session: %6.1fs reboot(2): restarting" % (time.time() - t0), flush=True)
at_prompt(2, 1, "cat notes.txt")
typ("cat notes.txt")
at_prompt(2, 2, "exit")
typ("exit")
wait(lambda t: re.search(rb"\r?\nhalt\r?\n", t.split(BANNER)[-1]) is not None, "the halt line")
print("session: %6.1fs halted" % (time.time() - t0), flush=True)
time.sleep(1)
p.kill()
p.wait()
log.close()
os.unlink(logp + ".pid")
