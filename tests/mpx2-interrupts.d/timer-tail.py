#!/usr/bin/env python3
"""I5's timer transcript check, also replayable without booting a guest."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HEX = r"0x[0-9a-f]{16}"
APIC = (r"apic: 0x00000000fee00000 at 0xffffb00000000000, id 0, svr "
        + HEX + r", lint0 " + HEX + r" -> 0x0000000000008700")
FINAL = [r"timer: LAPIC calibrated by (HPET|PM|PIT) divide16 [0-9]+ Hz, tick 100 Hz vector 32; PIT IRQ masked",
         r"timer: 20 ticks on vector 32, 0 spurious", r"halt"]


# kernel/timer's documented calibration diagnostics. Never discard a broad
# prefix: an unfamiliar diagnostic or one after recovery must still fail I5.
DIAGNOSTICS = [
    r"timer: LAPIC calibration: window [1-6] set aside: [0-9]+ Hz, the clock [0-9]+ us against the PM timer's [0-9]+ us",
    r"timer: LAPIC calibration: windows [1-6] and [1-6] disagree: [0-9]+ and [0-9]+ Hz",
    r"timer: LAPIC calibration: windows [1-6] and [1-6] of 6 agree",
    r"timer: LAPIC calibration: no two windows in a row agreed in 6; took [0-9]+ Hz",
    r"timer: LAPIC calibration: no second counter beside the HPET to hold each window to; two windows off alike in a row would pass",
]


def valid_tail(lines):
    if len(lines) < 4 or not all(re.fullmatch(pattern, line)
                                 for pattern, line in zip(FINAL, lines[-3:])):
        return False
    index = len(lines) - 4
    while index >= 0 and any(re.fullmatch(pattern, lines[index]) for pattern in DIAGNOSTICS):
        index -= 1
    return index >= 0 and re.fullmatch(APIC, lines[index]) is not None


def main():
    if len(sys.argv) != 2:
        print("usage: timer-tail.py LOG", file=sys.stderr)
        return 2
    # Share the firmware/CR normalization with every other serial assertion.
    normalized = subprocess.run(["bash", "-c", '. "$1"; serial_norm "$2"', "timer-tail",
                                 str(ROOT / "tools/lib.sh"), sys.argv[1]],
                                capture_output=True, text=True, check=False)
    if normalized.returncode:
        print(normalized.stderr, file=sys.stderr, end="")
        return 2
    lines = [line for line in normalized.stdout.splitlines() if line.strip()]
    if not valid_tail(lines):
        print("timer-tail: FAIL: expected APIC, documented calibration diagnostics, "
              "successful calibration, 20 ticks without spurious interrupts, halt", file=sys.stderr)
        print(normalized.stdout, file=sys.stderr, end="")
        return 1
    print("timer-tail: PASS: recovered calibration, exactly 20 ticks, 0 spurious, halt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
