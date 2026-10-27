"""The ordered J4 witness rejects missing, early and duplicate reads."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('sigign', Path(__file__).with_name('sigign.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
assert m.check(m.READY + '\n' + m.MASK) is None
for name, text in {
    'read-before-event': m.MASK + '\n' + m.READY,
    'no-event': m.MASK,
    'no-read': m.READY,
    'duplicate-event': m.READY + '\n' + m.READY + '\n' + m.MASK,
    'duplicate-read': m.READY + '\n' + m.MASK + '\n' + m.MASK,
    'ignored-after-event': m.READY + '\n' + m.MASK.replace('0000000000000000', '0000000000000400'),
    'empty': '',
}.items():
    assert m.check(text), name
    print('PASS J4 rejects ' + name)
print('PASS J4 ordered-probe selftest')
