#!/usr/bin/env python3
"""Judge document-cell SGR, retaining RGB instead of quantizing it to a VT.

Cursor motion, erasure, alternate screens, OSC and UTF-8 use the existing
screen-ref model. Only its pen/blank representation differs: the effective
wire foreground and bold flag stay attached to each cell. A statusline,
an OSC payload or a subsequently overwritten keyword cannot satisfy a row.
"""
import argparse
import json
from pathlib import Path
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
BaseTerm = runpy.run_path(str(ROOT / 'tools/screen-ref'))['Term']
SAMPLE = b'// colour witness\nif true { plain_word }\n'
DOCUMENT = 'if true { plain_word }'
KEYWORD = ('rgb', 198, 120, 221)


class WireTerm(BaseTerm):
    def __init__(self, cols=160, rows=50):
        super().__init__(cols, rows)
        self.fg, self.bg = ('ansi', 7), ('ansi', 0)
        self.cells = [[self.blank()] * cols for _ in range(rows)]
        self.editor = None

    def blank(self):
        return (32, (self.fg, self.bold == 1), self.bg)

    def sgr(self, ps):
        k = 0
        while k < len(ps):
            p = ps[k]
            k += 1
            if p == 0:
                self.fg, self.bg, self.bold = ('ansi', 7), ('ansi', 0), 0
                self.italic = self.underline = self.blink = self.inv = False
            elif p in (1, 2):
                self.bold = p
            elif p == 22:
                self.bold = 0
            elif p in (3, 23):
                self.italic = p == 3
            elif p in (4, 21, 24):
                self.underline = p != 24
            elif p in (7, 27):
                self.inv = p == 7
            elif p in (5, 25):
                self.blink = p == 5
            elif p in (38, 48):
                if k < len(ps) and ps[k] == 2 and k + 3 < len(ps):
                    colour = ('rgb', *ps[k + 1:k + 4])
                    k += 4
                elif k < len(ps) and ps[k] == 5 and k + 1 < len(ps):
                    colour = ('indexed', ps[k + 1])
                    k += 2
                else:
                    break
                if p == 38:
                    self.fg = colour
                else:
                    self.bg = colour
            elif 30 <= p <= 37 or 90 <= p <= 97:
                self.fg = ('ansi', p - 30 if p < 90 else p - 90 + 8)
            elif p == 39:
                self.fg = ('ansi', 7)
            elif 40 <= p <= 47 or 100 <= p <= 107:
                self.bg = ('ansi', p - 40 if p < 100 else p - 100 + 8)
            elif p == 49:
                self.bg = ('ansi', 0)

    def private_mode(self, b):
        if b == ord('l') and 1049 in self.params[:self.pi + 1] and self.primary is not None:
            self.editor = [row[:] for row in self.cells]
        super().private_mode(b)


def document_cells(data):
    term = WireTerm()
    # Console kernel diagnostics are not editor output; this is the same
    # whole-line removal used by the existing session's raw-byte extractor.
    clean = re.sub(rb'user: [^\r\n]*\r?\n', b'', data)
    # For the wire observer an OSC payload is never document text, even
    # when it contains an ESC other than its ST terminator.
    clean = re.sub(rb'\x1b\].*?(?:\x07|\x1b\\|\Z)', b'', clean, flags=re.S)
    for byte in clean:
        term.feed(byte)
    cells = term.cells if term.primary is not None or term.editor is None else term.editor
    for y, row in enumerate(cells):
        if y == 0 or y >= term.rows - 3:
            continue
        text = ''.join(chr(cell[0]) for cell in row)
        x = text.find(DOCUMENT)
        if x >= 0:
            plain = x + DOCUMENT.index('plain_word')
            return y, x, row[x:x + 2], row[plain:plain + len('plain_word')]
    return None


def keyword_colour(data):
    found = document_cells(data)
    if found is None:
        return False
    _, _, keyword, plain = found
    return (all(cell[1] == (KEYWORD, True) for cell in keyword)
            and all(cell[1][0] != KEYWORD for cell in plain))


def foregrounds(data):
    found = document_cells(data)
    if found is None:
        return None
    y, x, keyword, plain = found
    return dict(row=y + 1, column=x + 1,
                keyword=[cell[1] for cell in keyword],
                plain=[cell[1] for cell in plain])


def key_bytes(data, direction):
    return direction in ('up', 'down') and data == (b'\x1b[1;7A' if direction == 'up' else b'\x1b[1;7B')


def report_colour(data, route):
    passed = keyword_colour(data)
    print(('PASS ' if passed else 'FAIL ') + f'yew-lu-keyword-colour-{route} '
          + json.dumps(foregrounds(data), sort_keys=True), flush=True)
    return passed


def report_default(data, route):
    value = foregrounds(data)
    # This observation does not judge whether the two foregrounds differ.
    print(f'OBSERVE yew-lu-default-foreground-{route} TERM=linux '
          + json.dumps(value, sort_keys=True), flush=True)
    print(('PASS ' if value is not None else 'FAIL ') + f'yew-default-document-{route}', flush=True)
    return value is not None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('route', choices=('console', 'ssh', 'linux'))
    parser.add_argument('colour', type=Path)
    parser.add_argument('--default', type=Path)
    args = parser.parse_args()
    passed = report_colour(args.colour.read_bytes(), args.route)
    if args.default is not None:
        passed = report_default(args.default.read_bytes(), args.route) and passed
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
