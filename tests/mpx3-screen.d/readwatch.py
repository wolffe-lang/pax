#!/usr/bin/env python3
"""readwatch.py - count the guest's reads of its framebuffer (px87, pax#253).

    readwatch.py --elf KERNEL.elf --firmware bios|uefi --serial LOG --port N
                 [--cap N] [--timeout SECS] [--qemu-run PATH] IMAGE

Boots IMAGE under TCG with QEMU's gdb stub (tools/qemu-run --gdb, the CPU
frozen at reset), and speaks the GDB remote serial protocol to it directly
(GDB's manual, "Remote Protocol": packets, `?`, `g`, `m`, `c`, `k`, and
`Z1`/`Z3` with their `z` twins): no gdb is needed.

1. A hardware breakpoint on the kernel's first `pax_fb_fill` (boot/screen.S's
   REP STOSQ; kernel/screen's attach clears the whole framebuffer with it
   before it draws anything): its System V arguments give the framebuffer's
   first byte (%rdi) and its length (%rdx quadwords).
2. ONE read watchpoint (`Z3`) over that range, and a hardware breakpoint on
   `pax_halt`, the kernel's end. Every stop the watchpoint makes is a guest
   instruction that read framebuffer memory; each is counted, the first few
   kept with the instruction's address and, inside `pax_fb_copy` (a leaf),
   its caller (the return address at %rsp). At --cap stops the watchpoint is
   removed and the boot runs on to its end, so the serial log is whole.
3. At `pax_halt`, QEMU is killed (`k`).

The emulator is the witness: under TCG QEMU checks every guest load against
the watchpoint, whatever instruction made it; the kernel under test reports
nothing. Read on QEMU 8.2.2 as a black box, never its source.

Prints `readwatch: ...` lines; the last is `readwatch: RESULT reads=N cap=C
scrolls-from-serial=...` Exit 0 when the boot reached pax_halt (whatever it
read), 1 when it did not, 2 on a usage or tool error.
"""
import argparse
import os
import socket
import subprocess
import sys
import time


def die(msg, code=2):
    sys.stderr.write("readwatch: %s\n" % msg)
    sys.exit(code)


def say(msg):
    sys.stdout.write("readwatch: %s\n" % msg)
    sys.stdout.flush()


class Remote:
    """One GDB remote-protocol connection, acknowledgements off once agreed."""

    def __init__(self, port, deadline):
        self.deadline = deadline
        self.buf = b""
        self.ack = True
        while True:
            try:
                self.s = socket.create_connection(("127.0.0.1", port), timeout=5)
                break
            except OSError:
                if time.time() > deadline:
                    die("the gdb stub on port %d never listened" % port)
                time.sleep(0.1)
        self.s.settimeout(5)

    def _read(self):
        while True:
            try:
                chunk = self.s.recv(65536)
            except socket.timeout:
                if time.time() > self.deadline:
                    die("timed out waiting for the stub", 1)
                continue
            if not chunk:
                return False
            self.buf += chunk
            return True

    def recv(self):
        """The next packet's payload (or None when the stub hung up)."""
        while True:
            while self.buf[:1] in (b"+", b"-"):
                self.buf = self.buf[1:]
            start = self.buf.find(b"$")
            if start >= 0:
                end = self.buf.find(b"#", start)
                if end >= 0 and len(self.buf) >= end + 3:
                    data = self.buf[start + 1:end]
                    self.buf = self.buf[end + 3:]
                    if self.ack:
                        self.s.sendall(b"+")
                    return data.decode("latin-1")
            if not self._read():
                return None

    def send(self, payload):
        body = payload.encode("latin-1")
        frame = b"$" + body + b"#" + ("%02x" % (sum(body) & 0xff)).encode()
        self.s.sendall(frame)

    def ask(self, payload):
        self.send(payload)
        return self.recv()


def symbols(elf):
    out = subprocess.run(["nm", "-n", elf], capture_output=True, text=True)
    if out.returncode != 0:
        die("nm failed on %s" % elf)
    rows = []
    for line in out.stdout.splitlines():
        f = line.split()
        if len(f) == 3 and f[1] in "tTwW":
            rows.append((int(f[0], 16), f[2]))
    return rows


def where(rows, addr):
    best = None
    for a, name in rows:
        if a <= addr:
            best = (a, name)
        else:
            break
    if best is None:
        return "0x%x" % addr
    return "%s+0x%x" % (best[1], addr - best[0])


def regs(r):
    """rax rbx rcx rdx rsi rdi rbp rsp r8-r15 rip from a `g` reply."""
    g = r.ask("g")
    if g is None or len(g) < 17 * 16:
        die("short register reply %r" % g, 1)
    names = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp"] + ["r%d" % i for i in range(8, 16)] + ["rip"]
    return {n: int.from_bytes(bytes.fromhex(g[i * 16:(i + 1) * 16]), "little") for i, n in enumerate(names)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", required=True)
    ap.add_argument("--firmware", default="bios")
    ap.add_argument("--serial", required=True)
    ap.add_argument("--port", type=int, default=1234)
    ap.add_argument("--cap", type=int, default=256)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--qemu-run", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools", "qemu-run"))
    ap.add_argument("image")
    a = ap.parse_args()

    rows = symbols(a.elf)
    sym = {name: addr for addr, name in rows}
    for need in ("pax_fb_fill", "pax_fb_copy", "pax_halt"):
        if need not in sym:
            die("no %s in %s" % (need, a.elf))
    deadline = time.time() + a.timeout
    qemu = subprocess.Popen([a.qemu_run, "--firmware", a.firmware, "--accel", "tcg", "--serial", a.serial,
                             "--timeout", str(a.timeout), "--gdb", str(a.port), a.image],
                            stdout=subprocess.DEVNULL, stderr=open(a.serial + ".readwatch.qemu-run.log", "w"))
    halted = False
    reads = 0
    first = []
    try:
        r = Remote(a.port, deadline)
        stop = r.ask("?")
        if r.ask("QStartNoAckMode") == "OK":
            r.ack = False
        fill = sym["pax_fb_fill"]
        if r.ask("Z1,%x,1" % fill) != "OK":
            die("the stub refused a hardware breakpoint at pax_fb_fill", 1)
        stop = r.ask("c")
        if stop is None or not stop.startswith("T"):
            die("no stop at pax_fb_fill (%r)" % stop, 1)
        g = regs(r)
        if g["rip"] != fill:
            die("stopped at 0x%x, not pax_fb_fill 0x%x" % (g["rip"], fill), 1)
        fb, length = g["rdi"], g["rdx"] * 8
        r.ask("z1,%x,1" % fill)
        say("framebuffer 0x%x, %d bytes (the first pax_fb_fill, from %s)" % (fb, length, where(rows, int.from_bytes(bytes.fromhex(r.ask("m%x,8" % g["rsp"])), "little"))))
        if r.ask("Z1,%x,1" % sym["pax_halt"]) != "OK":
            die("the stub refused a hardware breakpoint at pax_halt", 1)
        z3 = r.ask("Z3,%x,%x" % (fb, length))
        say("read watchpoint over the whole range: %s" % (z3 or "unsupported (empty reply)"))
        if z3 != "OK":
            die("the stub refused a read watchpoint of %d bytes" % length, 1)
        watching = True
        while True:
            stop = r.ask("c")
            if stop is None or stop[:1] in ("W", "X"):
                say("the machine ended without reaching pax_halt (%r)" % stop)
                break
            g = regs(r)
            if g["rip"] == sym["pax_halt"] and "watch" not in stop:
                halted = True
                break
            if "watch" not in stop:
                say("an unexpected stop %r at %s" % (stop, where(rows, g["rip"])))
                continue
            reads += 1
            if len(first) < 4:
                addr = stop.split("watch:", 1)[1].split(";", 1)[0]
                line = "read %d: 0x%s by %s" % (reads, addr, where(rows, g["rip"]))
                if sym["pax_fb_copy"] <= g["rip"] < sym["pax_fb_copy"] + 32:
                    ret = int.from_bytes(bytes.fromhex(r.ask("m%x,8" % g["rsp"])), "little")
                    line += " called from %s" % where(rows, ret)
                first.append(line)
            if watching and reads >= a.cap:
                r.ask("z3,%x,%x" % (fb, length))
                watching = False
                say("the cap's %d reads: the watchpoint removed, the boot run on to its end" % a.cap)
        for line in first:
            say(line)
        if halted:
            say("the kernel reached pax_halt")
            r.send("k")
    finally:
        try:
            qemu.wait(timeout=30)
        except subprocess.TimeoutExpired:
            qemu.kill()
            qemu.wait()
    scrolls = "none"
    try:
        for line in open(a.serial, "rb").read().decode("latin-1").splitlines():
            if line.startswith("scroll: "):
                scrolls = line.strip()
    except OSError:
        pass
    say("RESULT reads=%d%s cap=%d halted=%s serial='%s'" % (reads, "+" if reads >= a.cap else "", a.cap, "yes" if halted else "no", scrolls))
    sys.exit(0 if halted else 1)


if __name__ == "__main__":
    main()
