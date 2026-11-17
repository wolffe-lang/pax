#!/usr/bin/env python3
"""Check real console pixels against Spleen, independently of extent.txt."""
import pathlib
import re
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = runpy.run_path(str(ROOT / "tools/screen-ref"))


def cell_bits(width, height, pixels, row, col):
    if width < (col + 1) * 8 or height < (row + 1) * 16:
        return None
    bits = []
    for y in range(16):
        value = 0
        for x in range(8):
            off = ((row * 16 + y) * width + col * 8 + x) * 3
            pixel = int.from_bytes(pixels[off:off + 3], "big")
            if pixel == REF["PALETTE"][7]:
                value |= 0x80 >> x
            elif pixel != REF["PALETTE"][0]:
                return None
        bits.append(value)
    return bits


def judge(log, screenshot):
    failed = False
    data = pathlib.Path(log).read_bytes().replace(b"\r", b"")
    keys = re.findall(rb"^extent: keys((?: [0-9a-f]{2})*)$", data, re.M)
    if keys == [b" 00 7a"] and b"extent: done\n" in data:
        print("PASS console-ctrl-space: raw input is 00 7a")
    else:
        print("FAIL console-ctrl-space: expected 00 7a; got %r" % keys)
        failed = True
    # BDF pixels, not the current extent or the generated assembly table:
    # a missing glyph must fail, even when the fallback is drawn correctly.
    font = REF["read_bdf"](ROOT / "font/spleen-8x16.bdf")
    cells = [(0x2500 + i, i // 16, i % 16) for i in range(128)]
    cells += [(0x2190 + i, 8, i) for i in range(4)]
    cells += [(0xe0b0 + i, 9, i) for i in range(4)]
    cells += [(0xe0a0 + i, 10, i) for i in range(3)]
    try:
        w, h, pixels = REF["read_ppm"](str(screenshot))
        missing, fallback = [], []
        for cp, row, col in cells:
            actual = cell_bits(w, h, pixels, row, col)
            if cp not in font or actual != font[cp]:
                missing.append("U+%04X" % cp)
                if actual == font[ord("?")]:
                    fallback.append("U+%04X" % cp)
        if missing:
            print("FAIL console-glyph-extent: %d/139 differ: %s; fallback: %s" %
                  (len(missing), " ".join(missing), " ".join(fallback)))
            failed = True
        else:
            print("PASS console-glyph-extent: all 139 glyphs match Spleen pixels")
    except (OSError, ValueError) as error:
        print("FAIL console-glyph-extent: no readable framebuffer: %s" % error)
        failed = True
    return int(failed)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: check.py SERIAL SCREEN.ppm")
    sys.exit(judge(*sys.argv[1:]))
