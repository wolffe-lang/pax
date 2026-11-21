#!/usr/bin/env python3
"""tests/mpx7-mux.d/screen.py — px125: read back what the console drew for
cases.py's screens, and what it answered and sent.

    screen.py judge LOG DIR EXPECT     every case: what PAX did, against
                                       EXPECT (the committed verdicts);
                                       exit 1 on any difference
    screen.py show LOG DIR             the same lines, nothing held

DIR is tools/ps2-session's (`NAME.ppm` a dump, `dumps.txt`); LOG the
serial log (vtcases' `QUERY` lines, `muxprobe keys`'s `key` lines and
`muxprobe paint`'s line). A dump is read cell by cell: each 8x16 cell's
pixels matched to the glyph the screen draws for a code point (tools/
screen-ref's font: Spleen below U+0100, font/extent.txt above) in two of
its colours, the colours named by the console's 16-colour palette; a
uniform cell is a space. Lines printed, one a case:

    B1 NAME: xterm's | not xterm's (row R: 'pax' want 'xterm')
    B2 LABEL: fg F bg B, exact | approximated | ignored
    B3 LABEL: N of M drawn (the missing: U+XXXX ...)
    B3 width-NAME: the cursor after it at column C
    B4 NAME: answered HEX | no answer
    B5 KEY: HEX
    ~B7 paint: ...

EXPECT holds the verdict part (after `NAME: `) of each line but B7's, a
line `ROW NAME<TAB>VERDICT`; a line PAX prints that EXPECT does not hold
is a FAIL by name, as is one EXPECT holds that PAX did not print.
"""
import pathlib
import re
import runpy
import sys

here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
ref = runpy.run_path(str(root / "tools/screen-ref"))
cases = runpy.run_path(str(here / "cases.py"))
PALETTE = ref["PALETTE"]

# What xterm does with the SGR samples: the colour it means in the
# 16-colour palette, or a note that it draws something no colour shows.
SGR_INTENT = {
    "plain": (7, 0), "red": (1, 0), "bright-red": (9, 0), "red-bg": (7, 1), "reverse": (0, 7), "fg-default": (7, 0),
    "reverse-off": (7, 0), "bold-then-22": (7, 0),
}
# Renditions xterm draws as a change no 16-colour cell can show (a weight,
# a slant, a line, a blink): PAX's colour change is an approximation, no
# change is ignored.
SGR_STYLE = {"bold", "dim", "italic", "underline", "curly", "double-underline", "blink", "strike", "overline",
             "underline-colour", "bold-red"}
# Renditions xterm maps to a colour PAX's palette lacks (256 and true
# colour): PAX's nearest of the 16 is an approximation.
SGR_COLOUR = {"256-196", "256-46", "256-21", "256-244", "256-bg-22", "rgb-orange", "rgb-navy", "rgb-bg-teal", "rgb-colon"}


def glyph_table():
    table = {}
    for cp, rows in sorted(ref["font_glyphs"]().items()):
        if len(rows) == 16:
            table.setdefault(tuple(rows), cp)
    return table


def read_cells(w, h, px, glyphs):
    idx = {v: i for i, v in enumerate(PALETTE)}
    out = []
    for r in range(h // 16):
        row = []
        for c in range(w // 8):
            seen = {}
            for y in range(16):
                o = ((r * 16 + y) * w + c * 8) * 3
                for x in range(8):
                    v = (px[o + x * 3] << 16) | (px[o + x * 3 + 1] << 8) | px[o + x * 3 + 2]
                    seen[v] = seen.get(v, 0) + 1
            if len(seen) == 1:
                row.append((32, None, idx.get(next(iter(seen)))))
                continue
            found = None
            for fg in seen:
                for bg in seen:
                    if fg == bg or found:
                        continue
                    bits = []
                    for y in range(16):
                        o = ((r * 16 + y) * w + c * 8) * 3
                        b = 0
                        for x in range(8):
                            v = (px[o + x * 3] << 16) | (px[o + x * 3 + 1] << 8) | px[o + x * 3 + 2]
                            if v == fg:
                                b |= 0x80 >> x
                            elif v != bg:
                                b = -1
                                break
                        if b < 0:
                            break
                        bits.append(b)
                    if len(bits) == 16 and tuple(bits) in glyphs:
                        found = (glyphs[tuple(bits)], idx.get(fg), idx.get(bg))
            row.append(found or (-1, None, None))
        out.append(row)
    return out


def cell_bits(w, px, r, c, fgv, bgv):
    """Cell (r, c)'s 16 rows as bytes, a bit set where the pixel is fgv;
    None when a pixel is neither fgv nor bgv."""
    rows = []
    for y in range(16):
        o = ((r * 16 + y) * w + c * 8) * 3
        b = 0
        for x in range(8):
            v = (px[o + x * 3] << 16) | (px[o + x * 3 + 1] << 8) | px[o + x * 3 + 2]
            if v == fgv:
                b |= 0x80 >> x
            elif v != bgv:
                return None
        rows.append(b)
    return rows


def text(row, n):
    s = ""
    for cp, _, _ in row[:n]:
        s += "▯" if cp < 0 else chr(cp)
    return s.rstrip(" ")


def cursor_at(cells, w):
    """The cell drawn inverted: the one whose background is the
    foreground the screen uses for text (7) on a blank screen."""
    for r, row in enumerate(cells):
        for c, (cp, fg, bg) in enumerate(row):
            if bg == 7 and cp in (32,) and fg is None:
                return r, c
    return None


def judge_screens(d, glyphs):
    out = []
    dumps = {}
    if (d / "dumps.txt").exists():
        for line in (d / "dumps.txt").read_text().splitlines():
            name, off = line.split()
            dumps[name] = int(off)
    for case in cases["SCREEN"]:
        name, rows = case[0], case[2]
        ppm = d / (name + ".ppm")
        if name not in dumps or not ppm.exists():
            out.append("B1 %s: no screen" % name)
            continue
        w, h, px = ref["read_ppm"](str(ppm))
        cells = read_cells(w, h, px, glyphs)
        width = max([len(x) for x in rows] + [8]) + 8
        diff = None
        for r, want in enumerate(rows):
            got = text(cells[r], width)
            if got != want:
                diff = "row %d: %r want %r" % (r, got[:40], want[:40])
                break
        tag = "B4" if name.startswith("b4") else "B5" if name.startswith("b5") else "B6" if name.startswith("b6") else "B1"
        if name in ("b4-cursor-shown", "b4-cursor-hidden", "b4-decscusr-bar", "b4-decscusr-reset"):
            cur = cursor_at(cells, w)
            out.append("%s %s: %s; the cursor %s" % (tag, name, "xterm's" if diff is None else "not xterm's (%s)" % diff,
                                                    "drawn at row %d column %d" % cur if cur else "not drawn"))
        else:
            out.append("%s %s: %s" % (tag, name, "xterm's" if diff is None else "not xterm's (%s)" % diff))
    # B2
    ppm = d / "b2-sgr.ppm"
    if ppm.exists():
        w, h, px = ref["read_ppm"](str(ppm))
        cells = read_cells(w, h, px, glyphs)
        plain = None
        for r, (label, _) in enumerate(cases["SGR"]):
            cp, fg, bg = cells[r][18]
            if label == "plain":
                plain = (fg, bg)
            seen = "fg %s bg %s%s" % (fg, bg, "" if cp == 88 else " (the glyph %s)" % ("unread" if cp < 0 else "U+%04X" % cp))
            if cp != 88:
                verdict = "hidden" if cp == 32 else "garbled"
            elif label in SGR_INTENT:
                verdict = "exact" if (fg, bg) == SGR_INTENT[label] else "not xterm's"
            elif label in SGR_COLOUR:
                verdict = "approximated (one of the 16)"
            elif (fg, bg) == plain:
                verdict = "ignored"
            elif label in SGR_STYLE:
                verdict = "approximated (a colour)"
            else:
                verdict = "?"
            out.append("B2 %s: %s, %s" % (label, seen, verdict))
    else:
        out.append("B2 sgr: no screen")
    # B3
    ppm = d / "b3-glyphs.ppm"
    if ppm.exists():
        w, h, px = ref["read_ppm"](str(ppm))
        cells = read_cells(w, h, px, glyphs)
        font = ref["font_glyphs"]()
        fgv, bgv = PALETTE[7], PALETTE[0]
        for r, (label, cps) in enumerate(cases["GLYPH"]):
            miss = []
            for i, c in enumerate(cps):
                bits = cell_bits(w, px, r, 11 + i, fgv, bgv)
                if c not in font or bits != list(font[c]):
                    miss.append(c)
            out.append("B3 %s: %d of %d drawn%s" % (label, len(cps) - len(miss), len(cps),
                                                    "" if not miss else " (not: %s)" % " ".join("U+%04X" % c for c in miss[:12]) + (" …" if len(miss) > 12 else "")))
    else:
        out.append("B3 glyphs: no screen")
    return out


def judge_log(log):
    out = []
    data = pathlib.Path(log).read_bytes().replace(b"\r", b"").decode("utf-8", "replace")
    data = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", data)
    answers = {}
    for m in re.finditer(r"QUERY (\S+)((?: [0-9a-f]{2})*| none)$", data, re.M):
        answers[m.group(1)] = m.group(2).strip()
    for name, _ in cases["ANSWER"]:
        a = answers.get(name)
        if name.startswith("width-"):
            m = re.fullmatch(r"1b 5b ((?:3[0-9] )+)3b ((?:3[0-9] )+)52", a or "")
            col = bytes.fromhex(m.group(2).replace(" ", "")).decode() if m else None
            out.append("B3 %s: %s" % (name, "the cursor after it at column %s" % col if col else "no answer" if a in (None, "none") else "answered %s" % a))
        else:
            out.append("B4 %s: %s" % (name, "no answer" if a in (None, "none") else "answered %s" % a))
    keys = re.search(r"^keys: ready$(.*?)^keys: done$", data, re.M | re.S)
    stream = " ".join(g.strip() for g in re.findall(r"^key((?: [0-9a-f]{2})+)$", keys.group(1), re.M)) if keys else ""
    # each key is typed, then `z` (7a): the bytes between two 7a are one key's
    got = [[]]
    for t in stream.split():
        if t == "7a":
            got.append([])
        else:
            got[-1].append(t)
    got = [" ".join(g) for g in got]
    for i, (name, _) in enumerate(cases["KEYS"]):
        out.append("B5 %s: %s" % (name, (got[i] or "nothing") if i < len(got) - 1 else "nothing"))
    if len(got) - 1 > len(cases["KEYS"]):
        out.append("B5 extra: %s" % " | ".join(got[len(cases["KEYS"]):]))
    m = re.search(r"paint: (\d+ x \d+.*)$", data, re.M)
    out.append("~B7 paint: %s" % (m.group(1) if m else "no line"))
    return out


def main(argv):
    if len(argv) >= 4 and argv[1] in ("judge", "show"):
        log, d = argv[2], pathlib.Path(argv[3])
        lines = judge_screens(d, glyph_table()) + judge_log(log)
        if argv[1] == "show":
            print("\n".join(lines))
            return 0
        want = {}
        for raw in open(argv[4], encoding="utf-8"):
            ln = raw.rstrip("\n")
            if not ln.strip() or ln.startswith("#"):
                continue
            head, _, v = ln.partition("\t")
            want[head] = v
        bad = 0
        seen = set()
        for ln in lines:
            if ln.startswith("~"):
                print(ln)
                continue
            head, _, v = ln.partition(": ")
            seen.add(head)
            if head not in want:
                print("FAIL %s: not in the expectations: %s" % (head, v))
                bad += 1
            elif want[head] != v:
                print("FAIL %s: %s; expected %s" % (head, v, want[head]))
                bad += 1
            else:
                print("PASS %s: %s" % (head, v))
        for head in want:
            if head not in seen:
                print("FAIL %s: not printed" % head)
                bad += 1
        print("screen.py: %d lines, %d differ" % (len(lines), bad))
        return 1 if bad else 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
