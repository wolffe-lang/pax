"""Read ELF64 section bytes; compare the two builds, not their debug paths."""
from pathlib import Path
import hashlib
import struct
import sys

root = Path(sys.argv[1])
def text(path):
    data = path.read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01'
    off = struct.unpack_from('<Q', data, 40)[0]
    width, count, strings = struct.unpack_from('<HHH', data, 58)
    assert width == 64 and strings < count
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, off + i * width) for i in range(count)]
    names = data[sections[strings][4]:sections[strings][4] + sections[strings][5]]
    for section in sections:
        name = names[section[0]:].split(b'\0', 1)[0]
        if name == b'.text':
            return data[section[4]:section[4] + section[5]]
    raise ValueError('no .text in ' + str(path))

for kernel in ('kmain_console', 'kmain_session'):
    for tier in ('native', 'release'):
        a = text(root / f'base-{kernel}-{tier}' / (kernel + '.elf'))
        b = text(root / f'pax-{kernel}-{tier}' / (kernel + '.elf'))
        print(kernel, tier, len(a), '->', len(b), 'delta', len(b)-len(a), 'byte-identical', a == b,
              'sha256', hashlib.sha256(b).hexdigest())
        assert a == b
