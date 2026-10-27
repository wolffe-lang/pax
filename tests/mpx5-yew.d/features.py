#!/usr/bin/env python3
"""Y8: independent visible-content witnesses, each attached to a real screendump."""
from pathlib import Path
import re
import runpy
import sys

root = Path(__file__).resolve().parents[2]
log, out = map(Path, sys.argv[1:])
ref = runpy.run_path(str(root/'tools/screen-ref'))
glyphs = ref['font_glyphs']()
data = log.read_bytes()
start = data.index(b'PAX: the console')
frames = {}
for line in (out/'dumps.txt').read_text().splitlines():
    name, offset = line.split()
    width, height, actual = ref['read_ppm'](str(out/(name+'.ppm')))
    term = ref['Term'](width//8, height//16)
    for byte in data[start:int(offset)]:
        term.feed(byte)
    expected = bytes(ref['render'](term, glyphs, width, height))
    assert expected == actual, 'Y8 pixels differ: '+name
    text = '\n'.join(''.join(chr(c[0]) for c in row).rstrip() for row in term.cells)
    (out/(name+'.grid.txt')).write_text(text+'\n')
    frames[name] = text
    print('PASS Y8 screenshot', name, f'{width//8* (height//16)} cells pixel-identical')
assert set(frames) == {'editor','search','edited','undo','fletch'}, 'Y8 missing screenshot'
for word in ('alpha','beta','gamma'):
    assert word in frames['editor'] and word in frames['undo'], 'Y8 text lost: '+word
assert '/beta' in frames['search'] or ('search' in frames['search'].lower() and 'beta' in frames['search']), 'Y8 search query absent'
assert 'delta' in frames['edited'], 'Y8 insertion absent'
assert 'delt' not in frames['undo'], 'Y8 undo did not remove insertion'
assert re.search(r'(?m)^\s*42\s*$', frames['fletch']), 'Y8 Fletch result absent'
assert b'PAX: init /bin/as ended with status 0; nothing left to run' in data
print('PASS Y8 search query, inserted text, undo restoration, Fletch expression and clean halt')
