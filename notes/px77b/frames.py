#!/usr/bin/env python3
"""px77b: the qualify's kept screen frames, PPM to PNG (lossless), after block A is released."""
from pathlib import Path
import hashlib, json, re, struct, sys, zlib
O = Path(sys.argv[1])
def png(ppm, dest):
    data = ppm.read_bytes(); match = re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s', data); assert match
    w, h = map(int, match.groups()); raw = data[match.end():]; assert len(raw) == w*h*3
    def chunk(k, b): return struct.pack('>I', len(b))+k+b+struct.pack('>I', zlib.crc32(k+b))
    filtered = b''.join(b'\0'+raw[y*w*3:(y+1)*w*3] for y in range(h))
    dest.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(filtered, 6))+chunk(b'IEND', b''))
    return w, h, hashlib.sha256(raw).hexdigest()
for name, t in json.loads((O/'frames.json').read_text()):
    w, h, d = png(O/name, O/(name[:-4]+'.png'))
    print(name, t, f'{w}x{h}', d, flush=True)
    (O/name).unlink()
for p in O.glob('frame-*.ppm'): p.unlink()
