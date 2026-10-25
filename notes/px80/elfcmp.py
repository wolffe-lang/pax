"""px80: compare two ELF64 files: the whole file, every PT_LOAD segment's
file bytes (the loaded image, with p_vaddr/p_memsz/p_flags), and every
section by name. Prints one line per item and a verdict line:
  identical | load-identical (the loaded image equal, other bytes not) | DIFFERENT
usage: python3 -I elfcmp.py A.elf B.elf"""
import hashlib
import struct
import sys
from pathlib import Path


def parse(path):
    d = Path(path).read_bytes()
    assert d[:4] == b'\x7fELF' and d[4] == 2, f'{path}: not ELF64'
    (_, _, _, _, _, phoff, shoff, _, _, phentsize, phnum, shentsize, shnum, shstrndx) = \
        struct.unpack_from('<16sHHIQQQIHHHHHH', d)
    segs = []
    for i in range(phnum):
        p_type, p_flags, p_off, p_vaddr, _, p_filesz, p_memsz, _ = struct.unpack_from('<IIQQQQQQ', d, phoff + i * phentsize)
        if p_type == 1:
            segs.append((p_vaddr, p_memsz, p_flags, d[p_off:p_off + p_filesz]))
    shs = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    names = d[shs[shstrndx][4]:shs[shstrndx][4] + shs[shstrndx][5]] if shnum else b''
    secs = {}
    for s in shs:
        name = names[s[0]:].split(b'\0', 1)[0].decode()
        secs[name] = (s[3], b'' if s[1] == 8 else d[s[4]:s[4] + s[5]], s[5])
    return d, segs, secs


def h(b):
    return hashlib.sha256(b).hexdigest()[:16]


a, b = sys.argv[1], sys.argv[2]
da, sa, xa = parse(a)
db, sb, xb = parse(b)
print(f'file {"same" if da == db else "DIFFERENT"} {len(da)} {len(db)} {h(da)} {h(db)}')
load_same = len(sa) == len(sb)
for i in range(max(len(sa), len(sb))):
    p = sa[i] if i < len(sa) else None
    q = sb[i] if i < len(sb) else None
    same = p is not None and q is not None and p[:3] == q[:3] and p[3] == q[3]
    load_same &= same
    f = lambda s: '-' if s is None else f'{s[0]:#x}+{s[1]:#x} flags {s[2]} {len(s[3])}B {h(s[3])}'
    print(f'PT_LOAD[{i}] {"same" if same else "DIFFERENT"} {f(p)} | {f(q)}')
for name in sorted(xa.keys() | xb.keys()):
    p, q = xa.get(name), xb.get(name)
    same = p is not None and q is not None and p == q
    f = lambda s: '-' if s is None else f'{s[0]:#x} {s[2]}B {h(s[1])}'
    print(f'section {name or "(null)"} {"same" if same else "DIFFERENT"} {f(p)} | {f(q)}')
print('verdict', 'identical' if da == db else 'load-identical' if load_same else 'DIFFERENT')
