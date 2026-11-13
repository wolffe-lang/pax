#!/usr/bin/env python3
"""Hold T2's detailed probe mask to meaningful and meaningless differences."""
import subprocess
from pathlib import Path

mask = Path(__file__).with_name("probe-mask")
line = ("boot: N ms from the kernel's entry to its first program; the console drew for N ms "
        "of it (N scrolls by copy (read N, write N cycles; copy when read <= N x write; "
        "minimum of N samples; reads [N,N,N,N,N]; writes [N,N,N,N,N]; "
        "window N cycles, N us), N bytes)\n")

def norm(text):
    return subprocess.check_output(["bash", str(mask)], input=text, text=True)

try:
    assert norm(line) == norm(line.replace("by copy", "by redraw"))
    assert "the probe's way" in norm(line)
    for name, altered in [
        ("statistic", line.replace("minimum", "median")),
        ("sample-count", line.replace("reads [N,N,N,N,N]", "reads [N,N,N,N]")),
        ("units", line.replace("cycles, N us", "cycles, N ms")),
        ("injection", line.replace("N us)", "N us; injected slow)")),
        ("forced", line.replace(line[line.index("read N"):line.index("), N bytes")], "fbread")),
    ]:
        assert norm(line) != norm(altered), name
        assert altered == norm(altered), name
    assert norm("another line: copy read N\n") == "another line: copy read N\n"
    print("PASS P-mask: measured ways compare alike; statistic, shape, units, injection and overrides stay visible")
except (AssertionError, subprocess.CalledProcessError) as exc:
    print(f"FAIL P-mask: {exc}")
    raise SystemExit(1)
