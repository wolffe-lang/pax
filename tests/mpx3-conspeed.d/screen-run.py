#!/usr/bin/env python3
"""tests/mpx3-conspeed.d/screen-run.py (px129): run a PAX image under QEMU with no COM1 and read what
its screen says at the end.

    screen-run.py --qemu-run TOOLS/qemu-run --iso ISO --mode WxH --accel kvm|tcg --font BDF
                  --out PREFIX [--firmware bios|uefi] [--serial FILE] [--timeout SECS] [--every SECS]

With no COM1 the kernel keeps only the first 64 KiB of its console in memory, and a timing program
writes megabytes, so its table is read off the screen instead: tools/qemu-run boots ISO (UEFI unless
--firmware bios, a VGA
device whose mode is WxH, QEMU's human monitor on a Unix socket), and every --every seconds the
monitor's `screendump` is taken and read back into text by matching each 8x16 cell (16x32 above
2560 pixels wide, PAX's scale) against the BDF font's printable ASCII glyphs (either polarity; a cell
of one colour is a space, a cell that matches nothing `?`). When the text says `nothing left to run`
(init ended), `PANIC` or `NOT HALTED`, or at --timeout, the last picture and its text are kept as
PREFIX.ppm and PREFIX.txt, QEMU is told `quit`, and the exit is 0 (init ended) or 1.
--serial FILE boots with COM1 to FILE instead (the harness's usual machine).
"""
import argparse
import os
import socket
import subprocess
import sys
import time


def load_font(path):
    glyphs = {}
    enc = None
    rows = None
    for ln in open(path, encoding="latin-1"):
        ln = ln.strip()
        if ln.startswith("ENCODING "):
            enc = int(ln.split()[1])
        elif ln == "BITMAP":
            rows = []
        elif ln == "ENDCHAR":
            if enc is not None and 32 <= enc <= 126 and rows is not None and len(rows) == 16:
                glyphs[tuple(rows)] = chr(enc)
            enc, rows = None, None
        elif rows is not None:
            rows.append(int(ln, 16))
    return glyphs


def read_ppm(path):
    data = open(path, "rb").read()
    parts = []
    i = 0
    while len(parts) < 4:
        while data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b"#":
            while data[i:i + 1] != b"\n":
                i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        parts.append(data[i:j])
        i = j
    i += 1
    assert parts[0] == b"P6", parts[0]
    w, h = int(parts[1]), int(parts[2])
    return w, h, data[i:i + w * h * 3]


def screen_text(path, glyphs):
    w, h, px = read_ppm(path)
    scale = 2 if w > 2560 else 1
    cw, ch = 8 * scale, 16 * scale
    cols, rows = min(w // cw, 256), min(h // ch, 128)
    lines = []
    for r in range(rows):
        line = []
        for c in range(cols):
            x0, y0 = c * cw, r * ch
            first = None
            bits = []
            two = True
            for gy in range(16):
                y = y0 + gy * scale
                off = (y * w + x0) * 3
                row = 0
                for gx in range(8):
                    p = px[off + gx * scale * 3: off + gx * scale * 3 + 3]
                    if first is None:
                        first = p
                    row = (row << 1) | (1 if p != first else 0)
                bits.append(row)
            if not any(bits):
                line.append(" ")
                continue
            t = tuple(bits)
            inv = tuple((~b) & 0xff for b in bits)
            line.append(glyphs.get(t) or glyphs.get(inv) or "?")
        lines.append("".join(line).rstrip())
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


class Monitor:
    def __init__(self, path, wait):
        t0 = time.monotonic()
        while True:
            try:
                self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.s.connect(path)
                break
            except OSError:
                if time.monotonic() - t0 > wait:
                    raise
                time.sleep(0.2)
        self.s.settimeout(120)
        self.read_prompt()

    def read_prompt(self):
        buf = b""
        while not buf.endswith(b"(qemu) "):
            chunk = self.s.recv(65536)
            if not chunk:
                raise EOFError("monitor closed")
            buf += chunk
        return buf

    def cmd(self, c):
        self.s.sendall(c.encode() + b"\n")
        return self.read_prompt()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu-run", required=True)
    ap.add_argument("--iso", required=True)
    ap.add_argument("--mode", required=True)
    ap.add_argument("--accel", required=True)
    ap.add_argument("--firmware", default="uefi")
    ap.add_argument("--font", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--serial")
    ap.add_argument("--timeout", type=float, default=1500)
    ap.add_argument("--every", type=float, default=3)
    a = ap.parse_args()
    w, h = a.mode.split("x")
    glyphs = load_font(a.font)
    sock = a.out + ".mon"
    if os.path.exists(sock):
        os.unlink(sock)
    ser = ["--serial", a.serial] if a.serial else ["--no-serial"]
    argv = [a.qemu_run, "--firmware", a.firmware, "--accel", a.accel, *ser, "--timeout", str(int(a.timeout) + 60), a.iso,
            "--", "-m", "512M", "-vga", "none", "-device", f"VGA,vgamem_mb=64,xres={w},yres={h}",
            "-monitor", f"unix:{sock},server=on,wait=off"]
    log = open(a.out + ".qemu.log", "wb")
    t0 = time.monotonic()
    p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
    print(f"screen-run: pid {p.pid}: {' '.join(argv)}", flush=True)
    rc = 1
    text = ""
    shot = a.out + ".shot.ppm"
    try:
        m = Monitor(sock, 60)
        while time.monotonic() - t0 < a.timeout and p.poll() is None:
            time.sleep(a.every)
            if os.path.exists(shot):
                os.unlink(shot)
            m.cmd(f"screendump {shot}")
            for _ in range(50):
                if os.path.exists(shot) and os.path.getsize(shot) >= int(w) * int(h) * 3:
                    break
                time.sleep(0.1)
            try:
                text = screen_text(shot, glyphs)
            except Exception as e:  # a half-written picture: the next look reads it
                print(f"screen-run: unreadable picture ({e})", flush=True)
                continue
            if "nothing left to run" in text:
                rc = 0
                break
            if "PANIC" in text or "NOT HALTED" in text:
                break
        os.replace(shot, a.out + ".ppm")
        open(a.out + ".txt", "w").write(text)
        print(f"screen-run: {'init ended' if rc == 0 else 'no end seen'} after {time.monotonic() - t0:.0f} s", flush=True)
        try:
            m.cmd("quit")
        except (EOFError, OSError):
            pass
    finally:
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
    sys.exit(rc)


if __name__ == "__main__":
    main()
