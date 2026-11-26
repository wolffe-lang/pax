#!/usr/bin/env python3
"""Read the existing sender's offsets, not an arbitrary earlier coloured frame."""
from pathlib import Path
import re
import runpy
import sys

ROW = runpy.run_path(str(Path(__file__).with_name('colour.py')))


def report_keys(data, route):
    match = re.search(rb'P: typed: ([0-9a-f ]+)\r?\n', data)
    got = bytes.fromhex(match[1].decode()) if match else b''
    complete = len(got) == 13 and got[-1:] == b'.'
    passed = True
    for index, direction in enumerate(('up', 'down')):
        value = got[index * 6:(index + 1) * 6]
        good = complete and ROW['key_bytes'](value, direction)
        print(('PASS ' if good else 'FAIL ') + f'key-ctrl-alt-{direction}-{route} got={value.hex()}', flush=True)
        passed = good and passed
    return passed


def main():
    directory, adapter = Path(sys.argv[1]), sys.argv[2]
    data = (directory / 'serial.log').read_bytes()
    passed = report_keys(data, adapter)
    marks = {}
    if (directory / 'dumps.txt').exists():
        for line in (directory / 'dumps.txt').read_text().splitlines():
            name, offset = line.split()
            marks[name] = int(offset)
    for name in ('default', 'colour'):
        if name not in marks or not 0 < marks[name] <= len(data):
            print(f'FAIL yew-colour-capture-{adapter}-{name} missing/invalid snapshot offset', flush=True)
            passed = False
            continue
        sample = data[:marks[name]]
        (directory / (name + '.raw')).write_bytes(sample)
        if name == 'default':
            passed = ROW['report_default'](sample, 'console-' + adapter) and passed
        else:
            passed = ROW['report_colour'](sample, 'console-' + adapter) and passed
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
