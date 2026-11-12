#!/usr/bin/env python3
"""tests/mpx3-conspeed.d/uart.py (px129, R-px129-15): the far end of a UART that sends at a real line rate.

    uart.py PATH [BAUD]       (BAUD 115200 by default: 11,520 bytes a second, ten bits a byte)

Makes PATH.in and PATH.out (FIFOs) for QEMU's `-chardev pipe,path=PATH` (tools/qemu-run's
--serial-chardev), shrinks PATH.out to one page (fcntl F_SETPIPE_SZ), and reads it at BAUD/10 bytes a
second, a little every 10 ms, until it is ended (SIGTERM): the emulated 16550's transmit FIFO then
fills and its THRE stays clear while the pipe is full, as a real transmitter's does while it sends, so
a kernel that waits on THRE before each byte waits about 87 us a byte, as on a machine with COM1 at
115200. PATH.in is held open and never written (no input). Prints `uart: <bytes> bytes read in <s> s`
when it ends. Written from pipe(7) and fcntl(2) (F_SETPIPE_SZ); QEMU's documentation of its pipe
character device.
"""
import fcntl
import os
import signal
import sys
import time

F_SETPIPE_SZ = 1031


def main():
    path = sys.argv[1]
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    rate = baud / 10.0
    for p in (path + ".in", path + ".out"):
        if not os.path.exists(p):
            os.mkfifo(p, 0o600)
    fin = os.open(path + ".in", os.O_RDWR)  # held, never written: QEMU sees no input and no EOF
    fout = os.open(path + ".out", os.O_RDWR | os.O_NONBLOCK)
    try:
        fcntl.fcntl(fout, F_SETPIPE_SZ, 4096)
    except OSError:
        pass
    done = [False]
    signal.signal(signal.SIGTERM, lambda *_: done.__setitem__(0, True))
    total = 0
    owed = 0.0
    t0 = last = time.monotonic()
    while not done[0]:
        time.sleep(0.01)
        now = time.monotonic()
        owed += (now - last) * rate
        last = now
        want = int(owed)
        if want <= 0:
            continue
        try:
            b = os.read(fout, want)
        except BlockingIOError:
            b = b""
        total += len(b)
        owed = min(owed - len(b), rate * 0.02)  # nothing banked beyond 20 ms: an idle line does not save up
    print(f"uart: {total} bytes read in {time.monotonic() - t0:.1f} s", flush=True)
    os.close(fin)
    os.close(fout)


if __name__ == "__main__":
    main()
