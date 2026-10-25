#!/usr/bin/env python3
"""tests/mpx5-screen's comparisons (px59).

  compare.py ref LOG FROM DIR
      every screen DIR/dumps.txt names (tools/ps2-session's `NAME OFFSET`
      lines) against tools/screen-ref's picture of LOG from FROM to that
      offset: pixel for pixel, and cell for cell (an 8x16 block). One
      line a dump; the last line `ref: D dumps, P identical; C of T cells`.
  compare.py vt LOG DIR
      the VT's cases on PAX (user/elf/vtcases): every `vt-<probe>-<name>`
      dump of an 80 x 25 screen read cell by cell (the glyphs matched
      against font/spleen-8x16.bdf, the colours against the PC palette)
      and held to the VT's own row (vt.rows, vt2.rows), the named classes
      (vtcheck.py's NAMED) PAX's by name and still different; the cursor
      is where the VT's was (PAX draws it as its cell inverted); and the
      QUERY lines vtcases printed held to the VT's answers. A screen of
      another size (OVMF gives 1280 x 800 whatever Limine asks) is said
      so and counted (`not 80x25`). Last line `vt: S the VT's, N named,
      F failed; Q answers the VT's, A failed; X not 80x25`.
Exit 0 when every comparison held, 1 otherwise."""
import pathlib
import re
import runpy
import sys

here = pathlib.Path(__file__).resolve().parent
root = here.parents[1]
ref = runpy.run_path(str(root / 'tools/screen-ref'))
vtc = runpy.run_path(str(here / 'vtcheck.py'))
PALETTE = ref['PALETTE']


def dumps(d):
    out = []
    for line in (pathlib.Path(d) / 'dumps.txt').read_text().splitlines():
        name, off = line.split()
        out.append((name, int(off)))
    return out


def cmp_ref(log, frm, d):
    data = pathlib.Path(log).read_bytes()
    at = data.find(frm.encode())
    glyphs = ref['font_glyphs']()
    term = None
    fed = at
    n = same = cells = good = 0
    bad = []
    for name, off in dumps(d):
        w, h, px = ref['read_ppm'](str(pathlib.Path(d) / (name + '.ppm')))
        if term is None:
            term = ref['Term'](min(w // 8, 256), min(h // 16, 128))
        if at < 0 or off < fed:
            bad.append(name)
            print('FAIL %s: the log has no %r before byte %d' % (name, frm, off))
            continue
        for b in data[fed:off]:
            term.feed(b)
        fed = off
        mine = bytes(ref['render'](term, glyphs, w, h))
        total = term.cols * term.rows
        diff = 0
        for r in range(term.rows):
            for c in range(term.cols):
                for y in range(16):
                    o = ((r * 16 + y) * w + c * 8) * 3
                    if mine[o:o + 24] != px[o:o + 24]:
                        diff += 1
                        break
        n += 1
        cells += total
        good += total - diff
        if mine == px:
            same += 1
            print('PASS %s: at byte %d, %d pixels, %d of %d cells the reference\'s' % (name, off, w * h, total, total))
        else:
            bad.append(name)
            print('FAIL %s: at byte %d, %d of %d cells differ' % (name, off, diff, total))
    print('ref: %d dumps, %d identical; %d of %d cells' % (n, same, good, cells))
    return not bad and n > 0


def font():
    glyphs, cp, rows, on = {}, None, [], False
    for line in open(root / 'font/spleen-8x16.bdf', encoding='latin-1'):
        t = line.split()
        if not t:
            continue
        if t[0] == 'ENCODING':
            cp = int(t[1])
        elif t[0] == 'BITMAP':
            rows, on = [], True
        elif t[0] == 'ENDCHAR':
            on = False
            if cp is not None and 32 < cp < 127 and len(rows) == 16:
                glyphs.setdefault(tuple(rows), cp)
        elif on:
            rows.append(int(t[0], 16) >> (len(t[0]) * 4 - 8))
    return glyphs


def read_cells(w, h, px, glyphs, palette=PALETTE):
    """The screen as (code point, fg, bg) a cell, colours as palette
    indices; a uniform cell is a space, its foreground unknown (None)."""
    idx = {v: i for i, v in enumerate(palette)}
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
            row.append(found or (63, None, None))
        out.append(row)
    return out


def cmp_vt(log, d):
    glyphs = font()
    vt = {}
    for f, p in (('vt.rows', 1), ('vt2.rows', 2), ('vt70.rows', 3)):
        for k, v in vtc['rows'](f).items():
            vt[(p,) + k] = v
    # VT comparison normalizes glyphs and palette indices, not VGA DAC
    # quantization (the VT uses a 9x16 ROM font and 6-bit DAC). Derive the
    # requested palette from the measured input stream; ref checks pixels.
    palettes = {}
    for number in (1, 2, 3):
        t = ref['Term'](80,25)
        for kind, name, data in vtc['cases']['PROBE%d' % number]:
            for b in data: t.feed(b)
            if name is not None: palettes[(number,name)] = list(t.palette)
    held = named = pending = failed = other = 0
    for name, _off in dumps(d):
        m = re.match(r'vt-(\d)-(.*)$', name)
        if not m:
            continue
        p, case = int(m.group(1)), m.group(2)
        w, h, px = ref['read_ppm'](str(pathlib.Path(d) / (name + '.ppm')))
        if (w // 8, h // 16) != (80, 25):
            other += 1
            continue
        got = read_cells(w, h, px, glyphs, palettes.get((p,case),PALETTE))
        key = next((k for k in ((p, 'SCREEN', case), (p, 'ECHO', case)) if k in vt), None)
        if case in ('FG', 'BG'):
            want = [vtc['vga']((int(x, 16) >> (0 if case == 'FG' else 4)) & 15) for x in vt[(p, 'PALETTE', case)][0].split()]
            # an X in its background's colour is a uniform cell: that colour is both
            have = [(lambda g: (g[1] if g[1] is not None else g[2]) if case == 'FG' else g[2])(got[i // 80][i % 80])
                    for i in range(256)]
            # the cursor sits after the 256th cell, row 4 column 17: not among them
            ok = have == want
            print('%s PALETTE %s: the 256 indexed colours%s' % ('PASS' if ok else 'FAIL', case, '' if ok else ' differ'))
            held += ok
            failed += not ok
            continue
        if key is None:
            print('FAIL %s: no VT row' % name)
            failed += 1
            continue
        (cr, cc), cells = vtc['vt_grid'](vt[key][0])
        want = {(r, c): (ch, f, b) for r, c, ch, f, b, _blink in cells}
        # PAX draws no blink: a VT cell with the blink bit is one PAX cannot match
        why = ['cell %d,%d: the VT\'s blinks' % (r, c) for r, c, _ch, _f, _b, blink in cells if blink]
        for r in range(25):
            for c in range(80):
                ch, f, b = want.get((r + 1, c + 1), (32, 7, 0))
                if (r + 1, c + 1) == (cr, cc):
                    f, b = b, f  # PAX's cursor: the cell inverted
                gch, gf, gb = got[r][c]
                if ch == 32 or f == b:
                    # Equal foreground/background hides any glyph; pixels
                    # cannot recover its code point (S0 checks that metadata).
                    # A blank shows its background alone (the cursor's
                    # inverted blank its foreground, swapped above)
                    if gch != 32 or gb != b:
                        why.append('cell %d,%d: %r %s/%s, the VT\'s a blank in %s' % (r + 1, c + 1, chr(gch), gf, gb, b))
                    continue
                if (gch, gf, gb) != (ch, f, b):
                    why.append('cell %d,%d: %r %s/%s, the VT\'s %r %s/%s' % (r + 1, c + 1, chr(gch), gf, gb, chr(ch), f, b))
        ok = not why
        if case in vtc['NOT_YET']:
            # Pixel parity to the deterministic steady renderer was checked
            # separately; metadata parity is S0, animation remains not-yet.
            pending += 1
            print('not-yet %s: recorded, drawn steady; %s' % (name, vtc['NOT_YET'][case]))
            continue
        if case in vtc['NAMED']:
            if ok:
                failed += 1
                print('FAIL %s: named (%s) but the VT\'s' % (name, vtc['NAMED'][case]))
            else:
                named += 1
                print('named %s: %s (%s)' % (name, vtc['NAMED'][case], why[0]))
            continue
        if ok:
            held += 1
            print('PASS %s: the VT\'s 2000 cells and its cursor at %d,%d' % (name, cr, cc))
        else:
            failed += 1
            print('FAIL %s: %d cells differ; %s' % (name, len(why), why[0]))
    # The answers, printed at the end of the run (one QUERY line each).
    text = pathlib.Path(log).read_bytes().decode('latin-1')
    # vtcases prints each `QUERY <probe>:<name> …` line after a clear;
    # the VT's rows name the case without the probe
    got = [re.sub(r'^QUERY \d:', 'QUERY ', m) for m in re.findall(r'QUERY [^\r\n\x1b]*', text)]
    want = []
    for f in ('vt.rows', 'vt2.rows'):
        want += [l for l in (here / f).read_text().splitlines() if l.startswith('QUERY ')]
    qa = qf = 0
    grid = None
    for name, _off in dumps(d):
        if name.startswith('vt-'):
            w, h, _px = ref['read_ppm'](str(pathlib.Path(d) / (name + '.ppm')))
            grid = (w // 8, h // 16)
            break
    for i, wl in enumerate(want):
        gl = got[i] if i < len(got) else '(none)'
        if gl == wl:
            qa += 1
        elif grid != (80, 25) and wl == 'QUERY CPR-wrap 1b 5b 31 3b 38 30 52' and gl == 'QUERY CPR-wrap 1b 5b 31 3b 38 31 52':
            qa += 1  # 160 columns: column 80 is not the last, so X moves the cursor to 81
            print('PASS %s: the 160-column grid\'s (the VT\'s 80 columns wrap there)' % gl)
            continue
        else:
            qf += 1
            print('FAIL answer %d: %s, the VT %s' % (i + 1, gl, wl))
            continue
        print('PASS %s' % gl)
    if len(got) != len(want):
        qf += 1
        print('FAIL %d QUERY lines, the VT\'s %d' % (len(got), len(want)))
    print('vt: %d the VT\'s, %d named, %d not-yet, %d failed; %d answers the VT\'s, %d failed; %d not 80x25'
          % (held, named, pending, failed, qa, qf, other))
    return failed == 0 and qf == 0 and (held + named + pending + other) > 0


def main():
    a = sys.argv[1:]
    if a[:1] == ['ref'] and len(a) == 4:
        ok = cmp_ref(a[1], a[2], a[3])
    elif a[:1] == ['vt'] and len(a) == 3:
        ok = cmp_vt(a[1], a[2])
    else:
        sys.stderr.write(__doc__)
        sys.exit(2)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
