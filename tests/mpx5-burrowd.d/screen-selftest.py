#!/usr/bin/env python3
"""The screendump reader's self-test: tests/mpx5-burrowd.d/rows.py's settled() against pictures written here.

    python3 -I -B tests/mpx5-burrowd.d/screen-selftest.py

B40 and B43 compare QEMU screendumps byte for byte, so a picture read before QEMU has finished writing it makes a
screen that did not change look changed. Each case writes a P6 picture the way a slow writer might, and reads it with
settled() while the writing goes on:
  SD1 written at once: the whole picture
  SD2 written in two halves with a pause longer than the reader's steady wait between them: the whole picture,
      never the first half
  SD3 the first half only, never finished: nothing (b''), never the half
  SD4 bytes that are no P6 picture: nothing
  SD5 no file: nothing
  SD6 a header that declares more than is ever written: nothing
Each case prints one PASS or FAIL line by name; the exit is 0 only when every case passed.
"""
import importlib.util
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('burrowd_rows', HERE / 'rows.py')
rows = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rows)

W, H = 64, 40
HEADER = b'P6\n%d %d\n255\n' % (W, H)
PIXELS = bytes((i * 7) % 251 for i in range(W * H * 3))
WHOLE = HEADER + PIXELS
STEADY = 0.3
TIMEOUT = 3.0
failed = []


def writer(path, parts, pause):
    """Write PARTS to PATH in order, PAUSE seconds between them, as one open file (QEMU writes one stream)."""
    def run():
        with open(path, 'wb') as f:
            for i, part in enumerate(parts):
                if i:
                    time.sleep(pause)
                f.write(part)
                f.flush()
    t = threading.Thread(target=run)
    t.start()
    return t


def case(name, what, want, parts=None, pause=0.0):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / 'shot.ppm'
        t = writer(path, parts, pause) if parts is not None else None
        time.sleep(0.05)
        got = rows.settled(path, timeout=TIMEOUT, steady=STEADY)
        if t is not None:
            t.join()
    held = got == want
    told = 'the whole picture' if got == WHOLE else 'nothing' if got == b'' else '%d bytes of %d' % (len(got), len(WHOLE))
    print('%s %s %s: read %s' % ('PASS' if held else 'FAIL', name, what, told), flush=True)
    if not held:
        failed.append(name)


half = len(WHOLE) // 2
case('SD1', 'written at once', WHOLE, [WHOLE])
case('SD2', 'two halves, %.1f s apart' % (3 * STEADY), WHOLE, [WHOLE[:half], WHOLE[half:]], pause=3 * STEADY)
case('SD3', 'the first half, never finished', b'', [WHOLE[:half]])
case('SD4', 'no P6 picture', b'', [b'not a picture at all\n' * 40])
case('SD5', 'no file', b'')
case('SD6', 'a header declaring more than is written', b'', [b'P6\n%d %d\n255\n' % (W, H + 1) + PIXELS])
print('screen-selftest: %s' % ('FAIL ' + ' '.join(failed) if failed else 'PASS, 6 cases'), flush=True)
raise SystemExit(1 if failed else 0)
