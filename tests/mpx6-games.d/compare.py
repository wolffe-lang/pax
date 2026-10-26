#!/usr/bin/env python3
"""tests/mpx6-games' comparisons (gm01): PAX's screen, taken by QEMU's
`screendump`, held to the container's frame of the same game, cell by
cell.

A golden frame is a lair game's cell grid: `NAME.txt` (the glyphs, one
line a row) and `NAME.sty` (runs of `fg,bg,attrs*count` a row; a colour
0-255 or 256 for the terminal's own; attrs 1 bold, 2 dim, 4 inverse),
as the game's headless path writes it, or the text, `--`, styles, `--`
the game's `--apply` writes for a captured byte stream. The frame is
turned into the bytes the game's renderer sends for those cells (lair's
`grid.push_sgr` rule, read from the engine's src/grid/grid.lu: `ESC [ 0`,
`;1` `;2` `;7` for the attributes, `39`/`49` for the terminal's colour,
30-37 90-97 40-47 100-107 for 0-15, `38;5;n` `48;5;n` above), placed at
ROW, COL of a blank screen with the cursor hidden, and drawn by
tools/screen-ref's terminal (held to a Linux VT's cells by
tests/mpx5-screen) in PAX's font: the picture PAX's screen must be, the
256 colours mapped to the sixteen as the VT maps them. Each 8 x 16 cell
of the dump is held to that picture pixel for pixel (`pixels`), and its
glyph alone to the golden's (`glyphs`: the cell's two colours read back
as the golden glyph's bitmap or its complement; a one-colour cell as a
glyph with no pixel or every pixel lit).

  compare.py frame NAME PPM GOLDEN [ROW COL]
      GOLDEN is DIR/final (a headless frame, .txt and .sty) or an
      `--apply` output file (`.apply`).
  compare.py oneof NAME PPM DIR FIRST LAST [ROW COL]
      the dump equals DIR/frame-NNNN for one NNNN in FIRST..LAST (an
      animated frame: cub's opening); which one is said.
  compare.py glyphs PPM LOG FROM OFFSET LIST
      the glyph screen (G1): LOG's bytes from FROM to OFFSET through
      screen-ref's terminal hold each code point LIST names (font/
      games-glyphs.txt) one cell, in order, every other column, after a
      line `gm01 glyphs`; the dump equals that picture pixel for pixel.
  compare.py probe LOG GAME LIST
      the game's `--probe-glyphs` table in LOG (its last run): every code
      point LIST names for GAME measured, each width 1.
  compare.py withheld NAME PPM GOLDEN [ROW COL]
      the font row withheld (G6): the dump is the golden's picture with
      every code point above U+00FF drawn `?`, and at least one is.
  compare.py ref LOG FROM DIR [latin1]
      every dump DIR/dumps.txt names (tools/ps2-session's `NAME OFFSET`)
      equals screen-ref's picture of LOG from FROM to its offset, pixel
      for pixel (`latin1`: the font row withheld, as screen-ref --latin1).
  compare.py table LIST
      every code point LIST names is in PAX's font (tools/screen-ref's
      reading of the BDFs and font/extent.txt, which tools/mkfont
      --check holds boot/font.S to): its own glyph, not `?`'s, not blank,
      and no two alike.
  compare.py after LOG FROM OFFSET NAME
      at the offset (a dump's), the main screen is back (the alternate
      screen left) and the cursor shown: the terminal restored.
  compare.py record LOG NAME WORD...
      the last `t TICK WORD` lines LOG shows from `cat NAME` name each
      WORD in order: the keys reached the game.
  compare.py plain LOG MARK
      the bytes after the line holding MARK to the next prompt: no
      `38;5;` colour and no code point above U+00FF (the plain tier);
      `rich` instead of `plain` as the first word asks the opposite.
Each prints PASS or FAIL lines and exits 0 when every row held, 1
otherwise, 2 on a usage error."""
import pathlib
import re
import runpy
import sys

here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
ref = runpy.run_path(str(root / 'tools/screen-ref'))
GLYPHS = ref['font_glyphs']()


def die(msg):
    sys.stderr.write('compare.py: %s\n' % msg)
    sys.exit(2)


def parse_sty(line):
    out = []
    for run in line.split():
        style, count = run.rsplit('*', 1)
        fg, bg, attrs = (int(x) for x in style.split(','))
        out.extend([(fg, bg, attrs)] * int(count))
    return out


def read_golden(path):
    """(text rows, style rows) of a headless frame or an --apply file."""
    p = pathlib.Path(path)
    if p.suffix == '.apply':
        parts = p.read_text(encoding='utf-8').split('--\n')
        if len(parts) < 3:
            die('%s: not text, --, styles, --' % path)
        text = parts[0].split('\n')[:-1]
        sty = parts[1].split('\n')[:-1]
    else:
        text = pathlib.Path(str(path) + '.txt').read_text(encoding='utf-8').split('\n')
        sty = pathlib.Path(str(path) + '.sty').read_text(encoding='utf-8').split('\n')
        if text and text[-1] == '':
            text = text[:-1]
        if sty and sty[-1] == '':
            sty = sty[:-1]
    if len(text) != len(sty):
        die('%s: %d text rows, %d style rows' % (path, len(text), len(sty)))
    cells = []
    for t, s in zip(text, sty):
        st = parse_sty(s)
        if len(st) != len(t):
            die('%s: a row of %d glyphs and %d styles' % (path, len(t), len(st)))
        cells.append([(ord(ch), f, b, a) for ch, (f, b, a) in zip(t, st)])
    return cells


def color(index, bg):
    if index == 256:
        return '49' if bg else '39'
    if index <= 15:
        base = 40 if bg else 30
        return str(base + 60 + index - 8 if index >= 8 else base + index)
    return '%d;5;%d' % (48 if bg else 38, index)


def sgr(fg, bg, attrs):
    s = '\x1b[0'
    if attrs & 1:
        s += ';1'
    if attrs & 2:
        s += ';2'
    if attrs & 4:
        s += ';7'
    return (s + ';' + color(fg, False) + ';' + color(bg, True) + 'm').encode()


def golden_bytes(cells, at_r, at_c):
    out = bytearray(b'\x1b[?25l\x1b[0m\x1b[H\x1b[2J')
    for r, row in enumerate(cells):
        out += b'\x1b[%d;%dH' % (at_r + r + 1, at_c + 1)
        for cp, f, b, a in row:
            out += sgr(f, b, a) + chr(cp).encode('utf-8')
    out += b'\x1b[0m'
    return bytes(out)


def picture(data, w, h):
    term = ref['Term'](min(w // 8, 256), min(h // 16, 128))
    for b in data:
        term.feed(b)
    return term, bytes(ref['render'](term, GLYPHS, w, h))


def cell_px(px, w, r, c):
    return [px[((r * 16 + y) * w + c * 8) * 3:((r * 16 + y) * w + c * 8) * 3 + 24] for y in range(16)]


def glyph_ok(block, cp):
    """The dump's cell shows glyph `cp` in some two colours (or one)."""
    rows = GLYPHS.get(cp, GLYPHS[63])
    colours = set()
    for line in block:
        for x in range(8):
            colours.add(line[x * 3:x * 3 + 3])
    if len(colours) == 1:
        return all(r == 0 for r in rows) or all(r == 0xFF for r in rows)
    if len(colours) != 2:
        return False
    a, b = sorted(colours)
    bits = [sum(0x80 >> x for x in range(8) if line[x * 3:x * 3 + 3] == a) for line in block]
    return bits == list(rows) or [0xFF ^ v for v in bits] == list(rows)


def held(name, ppm, cells, at_r, at_c, quiet=False):
    w, h, px = ref['read_ppm'](ppm)
    _term, want = picture(golden_bytes(cells, at_r, at_c), w, h)
    cols, rows = min(w // 8, 256), min(h // 16, 128)
    pix = gly = 0
    first = None
    golden_at = {(at_r + r, at_c + c): cell[0] for r, row in enumerate(cells) for c, cell in enumerate(row)}
    for r in range(rows):
        for c in range(cols):
            a, b = cell_px(px, w, r, c), cell_px(want, w, r, c)
            if a == b:
                pix += 1
            elif first is None:
                first = (r, c)
            if glyph_ok(a, golden_at.get((r, c), 32)):
                gly += 1
    total = cols * rows
    ok = pix == total
    if not quiet:
        line = '%s %s: %d of %d cells the golden\'s pixel for pixel, %d of %d its glyph' % (
            'PASS' if ok else 'FAIL', name, pix, total, gly, total)
        if first is not None:
            r, c = first
            line += '; first differing cell row %d column %d, the golden\'s %r' % (r + 1, c + 1, chr(golden_at.get((r, c), 32)))
        print(line)
    return ok, pix, gly


def ref_screens(log, frm, d, latin1):
    data = pathlib.Path(log).read_bytes()
    at = data.find(frm.encode())
    glyphs = ref['font_glyphs'](None, latin1)
    drawn = set(c for c in glyphs if c >= 256)
    n = same = 0
    bad = []
    for line in (pathlib.Path(d) / 'dumps.txt').read_text().splitlines():
        name, off = line.split()
        off = int(off)
        w, h, px = ref['read_ppm'](str(pathlib.Path(d) / (name + '.ppm')))
        term = ref['Term'](min(w // 8, 256), min(h // 16, 128), drawn)
        for b in data[at:off]:
            term.feed(b)
        mine = bytes(ref['render'](term, glyphs, w, h))
        n += 1
        if at >= 0 and mine == px:
            same += 1
            print('PASS %s: at byte %d, screen-ref\'s picture of the bytes, %d pixels' % (name, off, w * h))
        else:
            bad.append(name)
            print('FAIL %s: at byte %d, not screen-ref\'s picture of the bytes' % (name, off))
    print('ref: %d dumps, %d screen-ref\'s picture%s' % (n, same, ' (the font row withheld)' if latin1 else ''))
    return n > 0 and not bad


def main():
    a = sys.argv[1:]
    if not a:
        die(__doc__)
    if a[0] == 'frame' and len(a) in (4, 6):
        at = (int(a[4]), int(a[5])) if len(a) == 6 else (0, 0)
        ok, _, _ = held(a[1], a[2], read_golden(a[3]), *at)
    elif a[0] == 'oneof' and len(a) in (6, 8):
        at = (int(a[6]), int(a[7])) if len(a) == 8 else (0, 0)
        found = []
        best = (-1, None)
        for n in range(int(a[4]), int(a[5]) + 1):
            g = pathlib.Path(a[3]) / ('frame-%04d' % n)
            if not pathlib.Path(str(g) + '.txt').exists():
                continue
            ok, pix, _ = held(a[1], a[2], read_golden(g), *at, quiet=True)
            if ok:
                found.append(n)
            if pix > best[0]:
                best = (pix, n)
        ok = bool(found)
        if ok:
            print('PASS %s: the golden\'s frame %s pixel for pixel (of %s..%s)' % (a[1], ','.join(map(str, found)), a[4], a[5]))
        else:
            print('FAIL %s: no golden frame of %s..%s; the nearest, frame %s, %d cells' % (a[1], a[4], a[5], best[1], best[0]))
    elif a[0] == 'glyphs' and len(a) == 6:
        ppm, log, frm, off, lst = a[1], a[2], a[3], int(a[4]), a[5]
        data = pathlib.Path(log).read_bytes()
        at = data.find(frm.encode())
        if at < 0:
            die('%r is not in %s' % (frm, log))
        w, h, px = ref['read_ppm'](ppm)
        term, want = picture(data[at:off], w, h)
        cps = [int(l.split()[0][2:], 16) for l in pathlib.Path(lst).read_text().splitlines() if l.startswith('U+')]
        text = [''.join(chr(c[0]) for c in row) for row in term.cells]
        start = next((i for i, t in enumerate(text) if t.startswith('gm01 glyphs')), None)
        why = []
        if want != px:
            why.append('the dump is not screen-ref\'s picture of the bytes')
        if start is None:
            why.append('no `gm01 glyphs` line on the screen')
        else:
            got = []
            for row in term.cells[start + 1:]:
                got += [c[0] for c in row[0::2] if c[0] != 32]
                if len(got) >= len(cps):
                    break
            got = got[:len(cps)]
            if got != cps:
                k = next((i for i, (x, y) in enumerate(zip(got, cps)) if x != y), min(len(got), len(cps)))
                why.append('code point %d is %s on the screen, U+%04X in the list' % (
                    k + 1, 'U+%04X' % got[k] if k < len(got) else 'missing', cps[k] if k < len(cps) else 0))
            q = [c for c in cps if c >= 256 and c not in GLYPHS]
            if q:
                why.append('%d drawn as `?`' % len(q))
        ok = not why
        print('%s G1 glyphs: %d code points, one cell each in the list\'s order, each its own glyph; the dump screen-ref\'s picture%s'
              % ('PASS' if ok else 'FAIL', len(cps), '' if ok else ': ' + '; '.join(why)))
    elif a[0] == 'probe' and len(a) == 4:
        log, game, lst = a[1], a[2], a[3]
        text = pathlib.Path(log).read_bytes().decode('utf-8', 'replace').replace('\r', '')
        runs = text.split('code point | width | terminal ')
        want = [int(l.split()[0][2:], 16) for l in pathlib.Path(lst).read_text().splitlines()
                if l.startswith('U+') and game in l.split()[1:]]
        table = {}
        for part in runs[1:]:
            rows = re.findall(r'^U\+([0-9A-F]{4,6}) \| (-?\d+) \| ', part, re.M)
            if {int(c, 16) for c, _ in rows} == set(want):
                table = {int(c, 16): int(n) for c, n in rows}
        why = []
        if not table:
            why.append('no table of exactly the %d code points' % len(want))
        bad = sorted(c for c, n in table.items() if n != 1)
        if bad:
            why.append('%d not one cell (U+%04X first: %d)' % (len(bad), bad[0], table[bad[0]]))
        ok = not why
        print('%s G2 %s --probe-glyphs: %d code points, every width 1 on PAX\'s console%s'
              % ('PASS' if ok else 'FAIL', game, len(table), '' if ok else ': ' + '; '.join(why)))
        for c in sorted(table):
            print('  U+%04X | %d | %s' % (c, table[c], chr(c)))
    elif a[0] == 'withheld' and len(a) in (4, 6):
        at = (int(a[4]), int(a[5])) if len(a) == 6 else (0, 0)
        cells = read_golden(a[3])
        high = sum(1 for row in cells for c in row if c[0] > 255)
        cells = [[(c[0] if c[0] < 256 else 63,) + c[1:] for c in row] for row in cells]
        ok, _, _ = held(a[1] + ' (the golden with its %d cells above U+00FF as `?`)' % high, a[2], cells, *at)
        ok = ok and high > 0
    elif a[0] == 'ref' and len(a) in (4, 5):
        ok = ref_screens(a[1], a[2], a[3], a[4:] == ['latin1'])
    elif a[0] == 'table' and len(a) == 2:
        cps = [int(l.split()[0][2:], 16) for l in pathlib.Path(a[1]).read_text().splitlines() if l.startswith('U+')]
        missing = [c for c in cps if c not in GLYPHS]
        blank = [c for c in cps if c in GLYPHS and not any(GLYPHS[c])]
        q = [c for c in cps if c != 63 and GLYPHS.get(c) == GLYPHS[63]]
        seen = {}
        dup = []
        for c in cps:
            k = tuple(GLYPHS.get(c, ()))
            if k in seen:
                dup.append((seen[k], c))
            seen[k] = c
        ok = not (missing or blank or q or dup)
        print('%s G0 table: %d code points, each in PAX\'s font, none blank, none `?`\'s, no two alike%s' % (
            'PASS' if ok else 'FAIL', len(cps), '' if ok else ': missing %s blank %s ?-like %s alike %s' % (
                ['U+%04X' % c for c in missing[:5]], ['U+%04X' % c for c in blank[:5]],
                ['U+%04X' % c for c in q[:5]], ['U+%04X/U+%04X' % d for d in dup[:5]])))
    elif a[0] == 'after' and len(a) == 5:
        data = pathlib.Path(a[1]).read_bytes()
        at = data.find(a[2].encode())
        term = ref['Term'](160, 50)
        for b in data[at:int(a[3])]:
            term.feed(b)
        ok = at >= 0 and term.primary is None and term.visible
        print('%s %s: at byte %s the %s screen, the cursor %s' % (
            'PASS' if ok else 'FAIL', a[4], a[3], 'main' if term.primary is None else 'ALTERNATE',
            'shown' if term.visible else 'HIDDEN'))
    elif a[0] == 'record' and len(a) >= 4:
        text = pathlib.Path(a[1]).read_bytes().decode('utf-8', 'replace').replace('\r', '')
        i = text.rfind('cat ' + a[2] + '\n')
        seg = text[i:] if i >= 0 else ''
        e = seg.find('$ ', 1)
        seg = seg[:e] if e >= 0 else seg
        words = re.findall(r'^t (\d+) (\S+)', seg, re.M)
        got = [w for _t, w in words]
        k = 0
        for w in got:
            if k < len(a) - 3 and w == a[3 + k]:
                k += 1
        ok = i >= 0 and k == len(a) - 3
        print('%s %s: %d events recorded (%s); %s' % (
            'PASS' if ok else 'FAIL', a[2], len(got), ' '.join(got[:12]),
            'each of %s in order' % ' '.join(a[3:]) if ok else 'not %s in order' % ' '.join(a[3:])))
    elif a[0] in ('plain', 'rich') and len(a) == 3:
        log, mark = a[1], a[2].encode()
        data = pathlib.Path(log).read_bytes()
        i = data.find(mark)
        if i < 0:
            die('%r is not in %s' % (mark, log))
        seg = data[data.find(b'\n', i) + 1:]
        e = seg.find(b'$ ')
        seg = seg[:e] if e >= 0 else seg
        text = seg.decode('utf-8', 'replace')
        high = sorted({ord(ch) for ch in text if ord(ch) > 0xFF and ch != '�'})
        c256 = seg.count(b'38;5;') + seg.count(b'48;5;')
        plain = not high and c256 == 0
        ok = plain if a[0] == 'plain' else (not plain)
        print('%s %s: %d bytes after %r: %d code points above U+00FF, %d 256-colour SGRs: the %s tier' % (
            'PASS' if ok else 'FAIL', a[0], len(seg), a[2], len(high), c256, 'plain' if plain else 'rich'))
    else:
        die(__doc__)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
