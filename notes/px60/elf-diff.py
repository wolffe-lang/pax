import hashlib
import struct
import sys
from pathlib import Path

def sections(path):
    data = Path(path).read_bytes()
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, h[6] + i * h[11]) for i in range(h[12])]
    names_header = headers[h[13]]
    names = data[names_header[4]:names_header[4]+names_header[5]]
    result = {}
    for s in headers:
        name = names[s[0]:].split(b'\0', 1)[0].decode()
        result[name] = b'' if s[1] == 8 else data[s[4]:s[4]+s[5]]
    return result

a, b = map(sections, sys.argv[1:])
for name in sorted(a.keys() | b.keys()):
    x, y = a.get(name,b''), b.get(name,b'')
    print(name, 'same' if x == y else 'DIFFERENT', len(x), len(y), hashlib.sha256(x).hexdigest(), hashlib.sha256(y).hexdigest())
    if name == '.strtab':
        for side, entries in [('LOCAL',set(x.split(b'\0')) - set(y.split(b'\0'))), ('CI',set(y.split(b'\0')) - set(x.split(b'\0')))]:
            for entry in sorted(entries):
                print(side, entry.decode(errors='replace'))
