#!/usr/bin/env python3
"""tests/mpx3-conspeed.d/rows.py (px129): hold conspeed's table, read off the screen of one boot, to
its rows.

    rows.py TABLE.txt GRID ACCEL    (GRID: the cells conspeed must report, e.g. 256x90; ACCEL kvm or tcg)
    rows.py --selftest DIR          (DIR/red-ACCEL.txt must fail, DIR/green-ACCEL.txt pass, for both)

Every row compares two `ms least` figures of the same boot (the least of a test's frames: a frame
that a host's other work slowed is never the least), never a wall-clock absolute; `unit` is
conspeed's 2^21 dependent multiply-adds in user mode, the CPU's own yardstick on that boot.

  C1 the table: conspeed's header and every test's line, with at least one frame
  C8 the grid conspeed reports (TIOCGWINSZ) is GRID: at 2560 x 1440, 320 x 90 (pax#357: it was
     256 x 90, the right 512 pixels blank)
  C2 (a) a full screen of plain text, every cell changed:     plain    <= 3.4 units
  C3 (b) the same with an SGR before every cell:              sgr      <= 11.5 units
  C4 (c) one scrolled line from a full screen:                scroll1  <= 2.3 units
         ten lines in one write:                              scroll10 <= 3 x scroll1
  C5 (d) a clear and a repaint in one write:                  clear    <= 1.3 x plain
  C6 the cursor shown through a repaint:                      cursor   <= 1.3 x plain
     the same full screen written again:                      same     <= 0.7 x plain
  C7 (e) yew's F mode opening, as a frame:                    fussopen <= 2.3 units
         cub's step (about 81 KB, 14,000 cells):              cub      <= 4.3 units
         yew's Down or Up in F mode (about 170 bytes):        fuss     <= 0.05 units

The bounds sit between the trunk the rows were written at and the fix they hold (notes/px129-
console-speed.md): each about 1.4 times or more from both under KVM. The KVM figures are the CPU's
alone (QEMU's framebuffer is host memory); a slower framebuffer only adds to what each cell drawn
costs, which is what the rows hold down. Under TCG the CPU's unit is the host's own speed (a chain
of multiplies translates to one) while the kernel's memory accesses go through QEMU's software
TLB, so the rows against the unit (C2, C3, C4's first, C7) are SKIPPED by name, and so is `same`
(the parse of its 23 KB is most of both figures there); the rest hold with TCG's own bounds:
scroll10 <= 4 x scroll1, clear and cursor <= 1.4 x plain.

Prints `PASS Cn …`, `FAIL Cn …` or `SKIP Cn reason=…` a row; exit 0 when no row fails, 1
otherwise, 2 on a usage error.
"""
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


def check(text, grid, accel, out):
    got, rows = parse(text)
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

    def units(t, bound, row_name, what):
        if not kvm:
            skip(row_name, what)
            return
        v = least[t] / unit
        row(row_name, v <= bound, f"{what}: {t} {least[t]:.3f} ms least, {v:.2f} units of {unit:.3f} ms (bound {bound})")

    def times(t, base, bound, row_name, what):
        if bound is None:
            skip(row_name, what)
            return
        v = least[t] / least[base] if least[base] > 0 else float("inf")
        row(row_name, v <= bound, f"{what}: {t} {least[t]:.3f} ms least, {v:.2f} x {base} {least[base]:.3f} ms (bound {bound})")

    units("plain", 3.4, "C2", "(a) a full screen, every cell changed")
    units("sgr", 11.5, "C3", "(b) an SGR before every cell")
    units("scroll1", 2.3, "C4", "(c) one line scrolled from a full screen")
    times("scroll10", "scroll1", 3 if kvm else 4, "C4", "(c) ten lines in one write")
    times("clear", "plain", 1.3 if kvm else 1.4, "C5", "(d) a clear and a repaint in one write")
    times("cursor", "plain", 1.3 if kvm else 1.4, "C6", "the cursor shown through a repaint")
    times("same", "plain", 0.7 if kvm else None, "C6", "the same screen written again")
    units("fussopen", 2.3, "C7", "(e) yew's F mode opening")
    units("cub", 4.3, "C7", "(e) cub's step")
    units("fuss", 0.05, "C7", "(e) yew's Down or Up in F mode")
    return fail


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--selftest":
        d = sys.argv[2]
        ok = True
        said = []
        for accel in ("kvm", "tcg"):
            out_r, out_g = [], []
            r = check(open(f"{d}/red-{accel}.txt").read(), "320x90", accel, out_r)
            g = check(open(f"{d}/green-{accel}.txt").read(), "320x90", accel, out_g)
            print("\n".join(f"  red {accel}: " + x for x in out_r))
            print("\n".join(f"  green {accel}: " + x for x in out_g))
            ok = ok and r == 1 and g == 0
            said.append(f"{accel}: the red table fails {sum(x.startswith('FAIL') for x in out_r)} rows, "
                        f"the green one passes {sum(x.startswith('PASS') for x in out_g)}")
        print(f"{'PASS' if ok else 'FAIL'} selftest: " + "; ".join(said))
        sys.exit(0 if ok else 1)
    if len(sys.argv) != 4 or sys.argv[3] not in ("kvm", "tcg"):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        sys.exit(2)
    out = []
    rc = check(open(sys.argv[1]).read(), sys.argv[2], sys.argv[3], out)
    print("\n".join(out))
    sys.exit(rc)


if __name__ == "__main__":
    main()
