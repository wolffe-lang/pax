#!/usr/bin/env python3
"""tests/mpx3-conspeed.d/rows.py (px129): hold conspeed's table, read off the screen of one boot, to
its rows.

    rows.py TABLE.txt GRID ACCEL [uart]  (GRID: the cells conspeed must report, e.g. 256x90; ACCEL kvm or tcg;
                                          `uart`: the slow-UART leg, which holds C1, C8 and C9 alone)
    rows.py --selftest DIR          (each DIR/red-ACCEL[-HOST].txt must fail, each green-… pass)

Every row compares two `ms least` figures of the same boot (the least of a test's frames: a frame
that a host's other work slowed is never the least), never a wall-clock absolute; `unit` is
conspeed's 2^21 dependent multiply-adds in user mode, the CPU's own yardstick on that boot. A row
against the unit holds a test's drawing, not its bytes: the test's `ms least` less its byte count at
the rate of the `bytes` test (9,600 `ESC [ m`, 28,800 bytes that draw nothing) of the same boot. The
parse of a byte and the CPU's unit scale differently from one host to another (on a laptop's
i7-10870H, the fix's `sgr` read 13.3 units against a desktop i7-12700KF's 9.0, its drawing 3.9
against 2.8), so a bound on the raw figure held on one host and not the next.

  C1 the table: conspeed's header and every test's line, with at least one frame
  C8 the grid conspeed reports (TIOCGWINSZ) is GRID: at 2560 x 1440, 320 x 90 (pax#357: it was
     256 x 90, the right 512 pixels blank)
  C2 (a) a full screen of plain text, every cell changed:     plain's drawing    <= 3 units
  C3 (b) the same with an SGR before every cell:              sgr's drawing      <= 5 units
  C4 (c) one scrolled line from a full screen:                scroll1's drawing  <= 2.8 units
         ten lines in one write:                              scroll10 <= 3 x scroll1
  C5 (d) a clear and a repaint in one write:                  clear    <= 1.3 x plain
  C6 the cursor shown through a repaint:                      cursor   <= 1.3 x plain
     the same full screen written again:                      same     <= 0.7 x plain
  C7 (e) yew's F mode opening, as a frame:                    fussopen's drawing <= 2.3 units
         cub's step (about 81 KB, 14,000 cells):              cub's drawing      <= 2.3 units
         yew's Down or Up in F mode (about 170 bytes):        fuss's drawing     <= 0.05 units
  C9 (f) a slow UART (px129, R-px129-15: COM1's far end drained at 115200 baud, tests/mpx3-conspeed.d/uart.py):
         a write of 28,800 bytes that draw nothing:            bytes             <= 3 units
     a console write never waits on the UART (with a UART that sends one byte at a time and a kernel that
     waits for it, a byte costs about 87 us: bytes about 2.5 s, some 1,400 units). Only that leg holds it;
     there the other rows are SKIPPED by name (a slow UART slows every write, and conspeed skips a test
     whose write would outrun its budget).

The bounds sit between the trunk the rows were written at and the fix they hold, on both hosts'
tables (selftest/, notes/px129-console-speed.md): each about 1.3 times or more from both under KVM.
The KVM figures are the CPU's alone (QEMU's framebuffer is host memory); a slower framebuffer only
adds to what each cell drawn costs, which is what the rows hold down. Under TCG the CPU's unit is
the host's own speed (a chain of multiplies translates to one) while the kernel's memory accesses go
through QEMU's software TLB, so the rows against the unit (C2, C3, C4's first, C7) are SKIPPED by
name, and so is `same` (the parse of its 29 KB is most of both figures there); the rest hold with
TCG's own bounds: scroll10 <= 4 x scroll1, clear and cursor <= 1.4 x plain.

Prints `PASS Cn …`, `FAIL Cn …` or `SKIP Cn reason=…` a row; exit 0 when no row fails, 1
otherwise, 2 on a usage error.
"""
import os
import re
import sys

TESTS = ["unit", "bytes", "cell", "plain", "same", "sgr", "scroll1", "scroll10", "clear", "cursor",
         "fuss", "fussopen", "cub"]


def parse(text):
    head = re.search(r"^conspeed \d+ \(px129\): frames to (\S+), (\d+x\d+) cells", text, re.M)
    rows = {}
    for m in re.finditer(r"^(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s*$", text, re.M):
        rows[m.group(1)] = {"frames": int(m.group(2)), "bytes": int(m.group(3)), "cells": int(m.group(4)),
                            "mean": float(m.group(5)), "least": float(m.group(6))}
    return (head.group(2) if head else None), rows


def check(text, grid, accel, out, uart=False):
    got, rows = parse(text)
    if uart:
        return check_uart(got, rows, grid, accel, out)
    fail = 0

    def row(name, ok, what):
        nonlocal fail
        out.append(f"{'PASS' if ok else 'FAIL'} {name} {what}")
        if not ok:
            fail = 1

    missing = [t for t in TESTS if t not in rows or rows[t]["frames"] < 1]
    row("C1", got is not None and not missing,
        f"the table: {'a header' if got else 'no header'}; "
        + (f"missing or empty: {' '.join(missing)}" if missing else f"{len(TESTS)} tests, each with frames"))
    row("C8", got == grid, f"the grid: {got or 'none'} cells (want {grid})")
    if missing or got is None:
        return 1
    least = {t: rows[t]["least"] for t in TESTS}
    unit = least["unit"]
    if unit <= 0:
        row("C2", False, "the unit read 0 ms")
        return 1

    kvm = accel == "kvm"

    def skip(row_name, what):
        out.append(f"SKIP {row_name} reason=tcg: {what}: its bound is stated under KVM")

    nb = rows["bytes"]["bytes"]
    rate = least["bytes"] / nb if nb > 0 else None  # ms a byte, at the bytes test's

    def units(t, bound, row_name, what):
        if not kvm:
            skip(row_name, what)
            return
        if rate is None:
            row(row_name, False, f"{what}: the bytes test wrote no bytes")
            return
        parse = rows[t]["bytes"] * rate
        drawn = least[t] - parse
        v = drawn / unit
        row(row_name, v <= bound,
            f"{what}: {t} {least[t]:.3f} ms least less its {rows[t]['bytes']} bytes at {rate * 1e6:.1f} ns "
            f"({parse:.3f} ms) is {drawn:.3f} ms drawn, {v:.2f} units of {unit:.3f} ms (bound {bound})")

    def times(t, base, bound, row_name, what):
        if bound is None:
            skip(row_name, what)
            return
        v = least[t] / least[base] if least[base] > 0 else float("inf")
        row(row_name, v <= bound, f"{what}: {t} {least[t]:.3f} ms least, {v:.2f} x {base} {least[base]:.3f} ms (bound {bound})")

    units("plain", 3, "C2", "(a) a full screen, every cell changed")
    units("sgr", 5, "C3", "(b) an SGR before every cell")
    units("scroll1", 2.8, "C4", "(c) one line scrolled from a full screen")
    times("scroll10", "scroll1", 3 if kvm else 4, "C4", "(c) ten lines in one write")
    times("clear", "plain", 1.3 if kvm else 1.4, "C5", "(d) a clear and a repaint in one write")
    times("cursor", "plain", 1.3 if kvm else 1.4, "C6", "the cursor shown through a repaint")
    times("same", "plain", 0.7 if kvm else None, "C6", "the same screen written again")
    units("fussopen", 2.3, "C7", "(e) yew's F mode opening")
    units("cub", 2.3, "C7", "(e) cub's step")
    units("fuss", 0.05, "C7", "(e) yew's Down or Up in F mode")
    return fail


def check_uart(got, rows, grid, accel, out):
    fail = 0

    def row(name, ok, what):
        nonlocal fail
        out.append(f"{'PASS' if ok else 'FAIL'} {name} {what}")
        if not ok:
            fail = 1

    have = [t for t in ("unit", "bytes") if t in rows and rows[t]["frames"] >= 1]
    row("C1", got is not None and len(have) == 2,
        f"the table: {'a header' if got else 'no header'}; " + ("unit and bytes, each with frames" if len(have) == 2 else "no unit or no bytes"))
    row("C8", got == grid, f"the grid: {got or 'none'} cells (want {grid})")
    for r in ("C2", "C3", "C4", "C5", "C6", "C7"):
        out.append(f"SKIP {r} reason=uart: the slow-UART leg holds C9 alone")
    if len(have) < 2 or rows["unit"]["least"] <= 0:
        return 1
    if accel != "kvm":
        out.append("SKIP C9 reason=tcg: (f) a slow UART: its bound is stated under KVM")
        return fail
    u = rows["unit"]["least"]
    b = rows["bytes"]["least"]
    v = b / u
    row("C9", v <= 3, f"(f) a slow UART: bytes {b:.3f} ms least for {rows['bytes']['bytes']} bytes, {v:.2f} units of {u:.3f} ms "
        f"(bound 3; {b * 1e3 / max(rows['bytes']['bytes'], 1):.3f} us a byte)")
    return fail


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        d = sys.argv[2]
        ok = True
        said = []
        names = sorted(n for n in os.listdir(d) if re.fullmatch(r"(red|green)-(kvm|tcg)(-[a-z0-9]+)?\.txt", n))
        for n in names:
            want, accel = re.match(r"(red|green)-(kvm|tcg)", n).groups()
            out = []
            rc = check(open(os.path.join(d, n)).read(), "320x90", accel, out)
            print("\n".join(f"  {n}: " + x for x in out))
            good = rc == (1 if want == "red" else 0)
            ok = ok and good
            said.append(f"{n} {'fails' if want == 'red' else 'passes'} "
                        f"{sum(x.startswith('FAIL' if want == 'red' else 'PASS') for x in out)}"
                        + ("" if good else " (WRONG)"))
        for want in ("red", "green"):
            for accel in ("kvm", "tcg"):
                if f"{want}-{accel}.txt" not in names:
                    ok = False
                    said.append(f"no {want}-{accel}.txt")
        print(f"{'PASS' if ok else 'FAIL'} selftest: " + "; ".join(said))
        sys.exit(0 if ok else 1)
    if len(sys.argv) not in (4, 5) or sys.argv[3] not in ("kvm", "tcg") or (len(sys.argv) == 5 and sys.argv[4] != "uart"):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    out = []
    rc = check(open(sys.argv[1]).read(), sys.argv[2], sys.argv[3], out, uart=len(sys.argv) == 5)
    print("\n".join(out))
    sys.exit(rc)


if __name__ == "__main__":
    main()
