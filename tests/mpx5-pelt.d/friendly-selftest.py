"""Prove the byte assertions reject missing styles, outcomes and dimensions."""
import contextlib
import importlib.util
import io
from pathlib import Path

spec = importlib.util.spec_from_file_location('friendly', Path(__file__).with_name('friendly.py'))
friendly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(friendly)
raw = (b'\x1b[0mecho\r\n50 160\r\n\x1b[90m_suffix\x1b[0m\x1b[K'
       b'\x1b[90;2m_suffix\x1b[0m\x1b[K\x1b[32mecho\x1b[0m'
       b'\x1b[91mpx81_missing\x1b[0m\x1b[91m\'\x1b[0m'
       b'\r\nPX81-ABBR\r\n' + b'\r\nPX81-EVENT\r\n' * 4 +
       b'\r\nPX81-DONE\r\nPAX: init /bin/env ended with status 0; nothing left to run\r\n')

def check(data, mode='framebuffer'):
    with contextlib.redirect_stdout(io.StringIO()):
        return friendly.check(data, mode)

assert check(raw)
for old, new in [(b'[90m', b'[37m'), (b'[90;2m', b'[90m'),
                 (b'[32m', b'[39m'), (b'px81_missing', b'missing'),
                 (b"[91m'", b"[33m'"), (b'\x1b[K', b''),
                 (b'PX81-ABBR', b'wrong'), (b'PX81-EVENT', b'wrong'),
                 (b'PX81-DONE', b'wrong'), (b'status 0', b'status 1'),
                 (b'50 160', b'0 0')]:
    assert not check(raw.replace(old, new)), old
assert not check(b'')
serial = raw.replace(b'50 160', b'0 0')
assert check(serial, 'serial-zero')
assert not check(serial, 'serial-sized')
assert check(serial + b'\n24 80\n', 'serial-sized')
print('friendly comparator selftest: PASS (styles, clear, results, size, exit and empty capture go red)')
