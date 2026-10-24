#!/usr/bin/env python3
"""tests/mpx5-screen's VT rows (px59): tools/screen-ref, the reference PAX's
screen is held to pixel for pixel, held in turn to a Linux VT, class by
class. vtcases.py is what each of px59's two VT probes sent (notes/px59/
vtprobe.c, vtprobe2.c, one boot each); vt.rows and vt2.rows are what the
VT showed (/dev/vcsa1: every cell and the cursor) and answered, measured
twice each on kasumi's own kernel's VT under QEMU (notes/px59). Each
probe is replayed through screen-ref's terminal at the VT's 80 x 25 and
every snapshot compared with the VT's: all 2,000 cells (the VT's VGA
attribute translated to the PC palette's order), the cursor, each
query's answer. A case listed in NAMED is PAX's own answer by name (the
gap table, notes/px59-the-console-for-an-editor.md); it must still
differ from the VT's, so a class that comes to be served is seen.
Prints one line a case and a count; exit 0 when every case held."""
import pathlib
import runpy
import sys

here = pathlib.Path(__file__).resolve().parent
Term = runpy.run_path(str(here.parents[1] / 'tools/screen-ref'))['Term']
cases = runpy.run_path(str(here / 'vtcases.py'))

# Why a class is PAX's own (R-px59-N, rulings; `dropped`: read and not
# drawn as the VT draws it; `divergent`: drawn otherwise, by choice).
NAMED = {
    'bright-background': 'divergent (R-px59-1): 100-107 drawn bright; the VGA VT draws them without brightness',
}


NOT_YET = {name: 'needs the timer hook, px71' for name in (
    'SGR5', 'attr-5', 'combined-5-7', 'combined-1-5-7',
    'combined-2-5-7', 'combined-3-5-7', 'save-attributes',
)}


def vga(v):
    """A VGA attribute nibble's colour as the PC palette's index (red and
    blue swap places; bit 3 is the bright half)."""
    return (v & 10) | ((v & 1) << 2) | ((v & 4) >> 2)


def rows(path):
    out = {}
    for line in (here / path).read_text().splitlines():
        kind, name, rest = line.split(' ', 2)
        out.setdefault((kind, name), []).append(rest)
    return out


def grid(t):
    """screen-ref's terminal as the VT's row: the cursor and every cell
    that is not a blank in the default colours."""
    cells = []
    for r in range(t.rows):
        for c in range(t.cols):
            cp, f, b = t.cells[r][c]
            if (cp, f, b) != (32, 7, 0):
                cells.append((r + 1, c + 1, cp, f, b & 15, b >> 4))
    return (t.cy + 1, t.cx + 1), cells


def vt_grid(rest):
    """A VT row (`cursor=r,c cells= r,c[-c2]:CH/AT ...`) the same way."""
    head, _, body = rest.partition(' cells=')
    r, c = head.split('=')[1].split(',')
    cells = []
    for item in body.split():
        pos, val = item.split(':')
        ch, at = (int(x, 16) for x in val.split('/'))
        row, cols = pos.split(',')
        a, _, b = cols.partition('-')
        for col in range(int(a), int(b or a) + 1):
            cells.append((int(row), col, ch, vga(at & 15), vga((at >> 4) & 7), at >> 7))
    return (int(r), int(c)), sorted(cells)


def echo(ans):
    """What ECHO with ECHOCTL shows of answer bytes: a control byte as ^X."""
    return b''.join(b'^' + bytes([b + 64]) if b < 32 else bytes([b]) for b in ans)


def replay(probe, rowfile, report):
    vt = rows(rowfile)
    t = Term(80, 25)
    seen = {}
    for kind, name, data in probe:
        if kind == 'emit':
            for b in data:
                t.feed(b)
            continue
        if kind == 'palette':
            for b in cases['CLEAR']:
                t.feed(b)
            for i in range(256):
                for b in b'\x1b[0;%d;5;%dmX' % (38 if name == 'FG' else 48, i):
                    t.feed(b)
            got = [t.cells[i // 80][i % 80][1 if name == 'FG' else 2] for i in range(256)]
            want = [vga((int(x, 16) >> (0 if name == 'FG' else 4)) & 15) for x in vt[('PALETTE', name)][0].split()]
            report('PALETTE ' + name, got == want, 'the 256 indexed colours' if got == want else
                   'first differs at %d: %d, the VT %d' % next((i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w))
            continue
        if kind == 'answer':
            t.answers = bytearray()
            for b in data:
                t.feed(b)
            got = ' '.join('%02x' % b for b in t.answers) or 'none'
            n = seen[name] = seen.get(name, -1) + 1
            want = vt[('QUERY', name)][n]
            report('QUERY ' + name, got == want, got if got == want else 'answers %s, the VT %s' % (got, want))
            continue
        tag = 'SCREEN'
        if kind == 'screen':
            data = cases['CLEAR'] + data
        if kind == 'echo':
            tag = 'ECHO'
            t.answers = bytearray()
        for b in data:
            t.feed(b)
        if kind == 'echo':
            for b in echo(bytes(t.answers)):
                t.feed(b)
        got = grid(t)
        want = vt_grid(vt[(tag, name)][0])
        same = (got[0], sorted(got[1])) == want
        why = ''
        if not same:
            if got[0] != want[0]:
                why = 'cursor %d,%d, the VT %d,%d; ' % (got[0] + want[0])
            g, w = set(got[1]), set(want[1])
            d = sorted(g ^ w)
            if d:
                x = d[0]
                why += 'cell %d,%d: %s, the VT %s' % (x[0], x[1], next((c[2:] for c in got[1] if c[:2] == x[:2]), 'blank'),
                                                    next((c[2:] for c in want[1] if c[:2] == x[:2]), 'blank'))
        report(tag + ' ' + name, same, 'the VT\'s cells and cursor' if same else why)


def main():
    held = named = pending = 0
    bad = []

    def report(case, same, detail):
        nonlocal held, named, pending
        name = case.split(' ', 1)[1]
        if name in NOT_YET and case.startswith('SCREEN'):
            if not same:
                bad.append(case)
                print('FAIL %s: recorded attributes differ: %s' % (case, detail))
            else:
                pending += 1
                print('not-yet %s: recorded, drawn steady; %s' % (case, NOT_YET[name]))
            return
        if name in NAMED and case.startswith('SCREEN'):
            if same:
                bad.append(case)
                print('FAIL %s: named (%s) but now the VT\'s' % (case, NAMED[name]))
            else:
                named += 1
                print('named %s: %s (%s)' % (case, NAMED[name], detail))
            return
        if same:
            held += 1
            print('same %s: %s' % (case, detail))
        else:
            bad.append(case)
            print('FAIL %s: %s' % (case, detail))

    replay(cases['PROBE1'], 'vt.rows', report)
    replay(cases['PROBE2'], 'vt2.rows', report)
    replay(cases['PROBE3'], 'vt70.rows', report)
    print('vtcheck: %d cases the VT\'s, %d named, %d not-yet, %d failed' % (held, named, pending, len(bad)))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
