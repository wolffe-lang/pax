#!/usr/bin/env python3
"""Offline negative controls for the editor's colour and key observations."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load():
    spec = importlib.util.spec_from_file_location('yew_colour_rows', HERE / 'colour.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame(keyword=b'\x1b[1;38;2;198;120;221m', row=4):
    return (b'\x1b[?1049h\x1b[2J' + ('\x1b[%d;5H' % row).encode()
            + keyword + b'if' + b'\x1b[0;38;2;200;204;212m true { plain_word }')


def main():
    failures = 0
    cases = [
        ('yew-sgr-judge-rejects-plain', lambda m: not m.keyword_colour(frame(b'\x1b[0;38;2;200;204;212m'))),
        ('yew-sgr-judge-rejects-statusline-only', lambda m: not m.keyword_colour(frame(row=50))),
        ('yew-sgr-judge-rejects-overwritten-keyword', lambda m: not m.keyword_colour(
            frame() + b'\x1b[4;5H\x1b[0;38;2;200;204;212mif')),
        ('yew-sgr-judge-rejects-osc-payload', lambda m: not m.keyword_colour(b'\x1b]0;' + frame() + b'\x07')),
        ('yew-sgr-judge-accepts-keyword', lambda m: m.keyword_colour(frame())),
        ('yew-sgr-judge-accepts-grouped-sgr', lambda m: m.keyword_colour(frame(b'\x1b[38;2;198;120;221;1m'))),
        ('yew-sgr-judge-accepts-split-sgr', lambda m: m.keyword_colour(frame(b'\x1b[38;2;198;120;221m\x1b[1m'))),
        ('yew-sgr-judge-keeps-last-editor-screen', lambda m: m.keyword_colour(frame() + b'\x1b[?1049l$ ')),
        ('key-judge-rejects-ctrl-only', lambda m: not m.key_bytes(b'\x1b[1;5A', 'up')),
        ('key-judge-rejects-truncated-csi', lambda m: not m.key_bytes(b'\x1b[1;7', 'up')),
        ('key-judge-rejects-suffix', lambda m: not m.key_bytes(b'\x1b[1;7Ax', 'up')),
        ('key-judge-accepts-up', lambda m: m.key_bytes(b'\x1b[1;7A', 'up')),
        ('key-judge-accepts-down', lambda m: m.key_bytes(b'\x1b[1;7B', 'down')),
        ('yew-default-foreground-observed', lambda m: m.foregrounds(frame(b'\x1b[37m')) is not None),
    ]
    for name, check in cases:
        try:
            passed = bool(check(load()))
        except (ImportError, OSError, AttributeError, ValueError) as error:
            passed = False
            print(f'  {name}: {type(error).__name__}: {error}')
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)
        failures += not passed
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
