#!/usr/bin/env python3
"""Offline offset/key controls for the existing console sender's records."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
plain = b'\x1b[?1049h\x1b[2J\x1b[4;5H\x1b[37mif true { plain_word }'
colour = b'\x1b[?1049h\x1b[2J\x1b[4;5H\x1b[1;38;2;198;120;221mif\x1b[0;37m true { plain_word }'
failures = 0
for case in ('valid', 'missing-offset', 'stale-offset', 'ctrl-only'):
    with tempfile.TemporaryDirectory(prefix='yew-console-fixture-', dir=os.environ['TMPDIR']) as temp:
        directory = Path(temp)
        keys = b'\x1b[1;7A\x1b[1;7B.'
        if case == 'ctrl-only':
            keys = b'\x1b[1;5A\x1b[1;7B.'
        before = b'P: typed: ' + keys.hex(' ').encode() + b'\r\n' + plain
        full = before + b'\x1b[?1049l$ ' + colour
        (directory / 'serial.log').write_bytes(full)
        marks = f'default {len(before)}\n'
        if case != 'missing-offset':
            marks += f'colour {len(before) if case == "stale-offset" else len(full)}\n'
        (directory / 'dumps.txt').write_text(marks)
        result = subprocess.run([sys.executable, '-I', '-B', HERE / 'colour-results.py', directory, 'ps2'],
                                capture_output=True, text=True)
        good = (result.returncode == 0) == (case == 'valid')
        if case == 'missing-offset':
            good &= 'FAIL yew-colour-capture-ps2-colour' in result.stdout
        elif case == 'stale-offset':
            good &= 'FAIL yew-lu-keyword-colour-console-ps2' in result.stdout
        elif case == 'ctrl-only':
            good &= 'FAIL key-ctrl-alt-up-ps2' in result.stdout
        print(('PASS ' if good else 'FAIL ') + 'yew-console-record-' + case)
        failures += not good
raise SystemExit(int(bool(failures)))
