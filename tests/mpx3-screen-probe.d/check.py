#!/usr/bin/env python3
"""Validate the actual boot line, including every cost used by the selector."""
import re
import sys
from pathlib import Path

case, path, tier, firmware = sys.argv[1:]
try:
    text = Path(path).read_text(errors="replace").replace("\r", "")
    lines = [line for line in text.splitlines() if line.startswith("boot: ")]
    assert len(lines) == 1, "expected exactly one boot line"
    line = lines[0]
    if case in ("fbread", "fbwrite"):
        way = "copy" if case == "fbread" else "redraw"
        assert f"scrolls by {way} ({case})" in line, line
        assert "samples" not in line and "injected" not in line, line
    elif case == "none":
        assert "scrolls by none (no screen)" in line, line
        assert "samples" not in line and "injected" not in line, line
    else:
        m = re.search(
            r"scrolls by (copy|redraw) \(read (\d+), write (\d+) cycles; "
            r"copy when read <= 4 x write; minimum of 5 samples; reads "
            r"\[([0-9,]+)\]; writes \[([0-9,]+)\]; window (\d+) cycles, "
            r"(\d+) us(?:; injected (outlier|slow))?\)", line)
        assert m, "missing complete sample report: " + line
        way, r, w, rs, ws, window, micros, injected = m.groups()
        reads = [int(n) for n in rs.split(",")]
        writes = [int(n) for n in ws.split(",")]
        assert len(reads) == len(writes) == 5, (reads, writes)
        assert min(reads + writes) > 0, (reads, writes)
        assert int(r) == min(reads) and int(w) == min(writes), m.groups()
        expected = "copy" if int(r) <= 4 * int(w) else "redraw"
        assert way == expected, m.groups()
        assert int(window) > 0, "no measured window"
        if case == "outlier":
            assert injected == case, m.groups()
            assert reads == [1000, 100, 100, 100, 100], reads
            assert writes == [100] * 5 and way == "copy", m.groups()
        elif case == "slow":
            assert injected == case, m.groups()
            assert reads == [1000] * 5, reads
            assert writes == [100] * 5 and way == "redraw", m.groups()
        else:
            assert injected is None, m.groups()
    print(f"PASS P-{case} {tier} {firmware}: {line}")
except (AssertionError, OSError, ValueError) as exc:
    print(f"FAIL P-{case} {tier} {firmware}: {exc}")
    raise SystemExit(1)
