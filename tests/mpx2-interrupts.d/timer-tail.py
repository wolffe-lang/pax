#!/usr/bin/env python3
"""I5's timer transcript check, also replayable without booting a guest."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HEX = r"0x[0-9a-f]{16}"
APIC = (r"apic: 0x00000000fee00000 at 0xffffb00000000000, id 0, svr "
        + HEX + r", lint0 " + HEX + r" -> 0x0000000000008700")
FINAL = [r"timer: LAPIC calibrated by (HPET|PM|PIT) divide16 [0-9]+ Hz, tick 100 Hz vector 32; PIT IRQ masked",
         r"timer: 20 ticks on vector 32, 0 spurious", r"halt"]


def main():
    if len(sys.argv) != 2:
        print("usage: timer-tail.py LOG", file=sys.stderr)
        return 2
    return subprocess.run([str(ROOT / "tools/expect-serial"), "--tail", "--regex",
                           sys.argv[1], APIC, *FINAL], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
