"""px80: the compressed sections of ELF64 objects and archives, by their
headers: a section with SHF_COMPRESSED (0x800) and its Elf64_Chdr ch_type
(1 ELFCOMPRESS_ZLIB, 2 ELFCOMPRESS_ZSTD). One line per file:
  NAME members N sections M zlib Z zstd S
usage: python3 -I chdr.py FILE..."""
import struct
import sys
from pathlib import Path


def elf(d):
    if d[:4] != b'\x7fELF' or d[4] != 2:
        return 0, 0, 0
    shoff, = struct.unpack_from('<Q', d, 0x28)
    shentsize, shnum = struct.unpack_from('<HH', d, 0x3a)
    n = z = s = 0
    for i in range(shnum):
        _, _, flags, _, off, size, _, _, _, _ = struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize)
        if flags & 0x800:
            n += 1
            t, = struct.unpack_from('<I', d, off)
            z += t == 1
            s += t == 2
    return n, z, s


for f in sys.argv[1:]:
    d = Path(f).read_bytes()
    parts = []
    if d[:8] == b'!<arch>\n':
        p = 8
        while p + 60 <= len(d):
            size = int(d[p + 48:p + 58].decode().strip())
            parts.append(d[p + 60:p + 60 + size])
            p += 60 + size + (size & 1)
    else:
        parts.append(d)
    tot = [0, 0, 0]
    members = 0
    for m in parts:
        r = elf(m)
        if m[:4] == b'\x7fELF':
            members += 1
        tot = [a + b for a, b in zip(tot, r)]
    print(f'{Path(f).name} members {members} sections {tot[0]} zlib {tot[1]} zstd {tot[2]}')
