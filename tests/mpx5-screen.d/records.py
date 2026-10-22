#!/usr/bin/env python3
"""tests/mpx5-screen's VT image (px59): vtcases.py's two probes as the
records user/elf/vtcases.c plays, and the keys tools/ps2-session types
while it plays them: the start key, then after each screen's name (its
OSC string on the serial log) the dump and the key that goes on. A
screen's name is its probe's number, a colon, the VT's name.
    records.py RECORDS KEYS"""
import pathlib
import runpy
import struct
import sys

here = pathlib.Path(__file__).resolve().parent
cases = runpy.run_path(str(here / 'vtcases.py'))
KIND = {'screen': b's', 'emit': b'e', 'palette': b'p', 'answer': b'a', 'echo': b'c'}
rec, keys = bytearray(), ['#!ps2-session', 'prompt 1 vtcases: ready', 'key ret']
for n, probe in ((1, cases['PROBE1']), (2, cases['PROBE2'])):
    if n == 2:
        rec += b'r' + b'2\0' + struct.pack('<I', 0)
    for kind, name, data in probe:
        label = '' if name is None else '%d:%s' % (n, name)
        rec += KIND[kind] + label.encode() + b'\0' + struct.pack('<I', len(data)) + data
        if kind in ('screen', 'palette', 'echo'):
            keys += ['prompt 1 \\x1b]px59;%s\\x07' % label, 'dump vt-%s 0.5' % label.replace(':', '-'), 'key ret']
keys += ['prompt 1 vtcases: done']
pathlib.Path(sys.argv[1]).write_bytes(bytes(rec))
pathlib.Path(sys.argv[2]).write_text('\n'.join(keys) + '\n')
