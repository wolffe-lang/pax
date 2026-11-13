#!/usr/bin/env python3
"""T7's reason decoder: real detailed costs, old images, and near misses."""
import importlib.util
from pathlib import Path
import sys

# The suite may run from a pinned, clean snapshot shared by several steps.
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location('scroll_reason', Path(__file__).with_name('scroll-reason.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# Exact reason from a native BIOS QEMU boot at the reporting change's head.
real = ('read 310, write 274 cycles; copy when read <= 4 x write; minimum of 5 samples; '
        'reads [350,318,314,310,310]; writes [304,276,274,278,274]; window 4002 cycles, 1 us')
slow = ('read 1000, write 100 cycles; copy when read <= 4 x write; minimum of 5 samples; '
        'reads [1000,1000,1000,1000,1000]; writes [100,100,100,100,100]; window 4932 cycles, 1 us; injected slow')
cases = [
    ('detailed-real', 'copy', real, True),
    ('detailed-slow', 'redraw', slow, True),
    ('legacy-copy', 'copy', 'read 100, write 100 cycles; copy when read <= 4 x write', True),
    ('legacy-redraw', 'redraw', 'read 500, write 100 cycles; copy when read <= 4 x write', True),
    ('fbread', 'copy', 'fbread', True), ('fbwrite', 'redraw', 'fbwrite', True),
    ('no-screen', 'none', 'no screen', True),
    ('wrong-way', 'redraw', real, False),
    ('wrong-minimum', 'copy', real.replace('read 310,', 'read 311,'), False),
    ('wrong-write-minimum', 'copy', real.replace('write 274 cycles', 'write 275 cycles'), False),
    ('missing-sample', 'copy', real.replace('[350,318,314,310,310]', '[350,318,314,310]'), False),
    ('extra-sample', 'copy', real.replace('[350,318,314,310,310]', '[350,318,314,310,310,310]'), False),
    ('wrong-statistic', 'copy', real.replace('minimum', 'median'), False),
    ('wrong-count', 'copy', real.replace('of 5 samples', 'of 4 samples'), False),
    ('bad-units', 'copy', real.replace('1 us', '1 ms'), False),
    ('negative-cost', 'copy', real.replace('[350,', '[-350,'), False),
    ('trailing-text', 'copy', real + '; arbitrary', False),
    ('forced-tail', 'copy', 'fbread; arbitrary', False),
    ('forced-wrong-way', 'redraw', 'fbread', False),
    ('no-screen-wrong-way', 'copy', 'no screen', False),
]
bad = False
for name, way, text, expected in cases:
    ok = module.validate(way, text) is None
    if ok != expected:
        print(f'FAIL T7-reason {name}: accepted={ok}, expected={expected}')
        bad = True
    else:
        print(f'PASS T7-reason {name}')
raise SystemExit(1 if bad else 0)
