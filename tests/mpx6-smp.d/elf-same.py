#!/usr/bin/env python3
# tests/mpx6-smp.d/elf-same.py — two kernel ELFs compared where the machine sees them (px166, stage 3): every allocated
# section (the ones loaded: .text, .rodata, .data, .bss) of one against the other's, by name, address, size and bytes.
# .text must be byte for byte the same; the other loaded sections the same but for `pax_kernel_commit`'s bytes, which
# tools/build-kernel writes per commit. Sections the machine never loads (debug, symbols) are not compared: they name
# the build's paths. TESTWORDS-LEDGER-ELF reads it with SMP_SHIPPED_AGAINST: the shipped kernel against trunk's, the
# proof that the ledger left the shipped kernel's entry and release paths (and everything else) as trunk has them.
#   elf-same.py A B          prints `same: …` or `differs: …`; exit 0 when the same, 1 when not, 2 on an unreadable ELF
#   elf-same.py --selftest   each verdict on small synthetic ELFs
import struct, sys

SHF_ALLOC, SHT_NOBITS, SHT_SYMTAB = 2, 8, 2
STAMP = 48  # boot/start.S's pax_kernel_commit: 48 bytes, NUL-padded ASCII (its symbol carries no size)


def load(path):
    b = open(path, 'rb').read()
    if b[:4] != b'\x7fELF' or b[4] != 2 or b[5] != 1:
        raise ValueError(f'{path}: not a 64-bit little-endian ELF')
    shoff, = struct.unpack_from('<Q', b, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', b, 0x3a)
    secs = []
    for i in range(shnum):
        name, typ, flags, addr, off, size, link, info, align, entsize = struct.unpack_from('<IIQQQQIIQQ', b, shoff + i * shentsize)
        secs.append(dict(name=name, type=typ, flags=flags, addr=addr, off=off, size=size, link=link))
    sh = secs[shstrndx]
    def cstr(tab, o):
        e = b.index(b'\0', tab['off'] + o)
        return b[tab['off'] + o:e].decode(errors='replace')
    for s in secs:
        s['name'] = cstr(sh, s['name'])
    syms = []
    for s in secs:
        if s['type'] == SHT_SYMTAB:
            st = secs[s['link']]
            for o in range(s['off'], s['off'] + s['size'], 24):
                nm, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', b, o)
                syms.append((cstr(st, nm), info & 15, value, size))
    return b, secs, syms


def where(syms, addr):
    best = None
    for name, kind, value, size in syms:
        if kind == 2 and value <= addr < value + max(size, 1) and name:
            best = f'{name}+{addr - value:#x}'
    return best or f'{addr:#x}'


def compare(pa, pb):
    a, sa, ya = load(pa)
    b, sb, yb = load(pb)
    la = [s for s in sa if s['flags'] & SHF_ALLOC]
    lb = [s for s in sb if s['flags'] & SHF_ALLOC]
    why = []
    shape = lambda s: (s['name'], s['type'], s['flags'], s['addr'], s['size'])
    if [shape(s) for s in la] != [shape(s) for s in lb]:
        for x, y in zip(la, lb):
            if shape(x) != shape(y):
                why.append(f'{x["name"]} at {x["addr"]:#x} size {x["size"]:#x}, against {y["name"]} at {y["addr"]:#x} size {y["size"]:#x}')
        if len(la) != len(lb):
            why.append(f'{len(la)} loaded sections against {len(lb)}')
    commit = {n: (v, s or STAMP) for n, k, v, s in ya if n == 'pax_kernel_commit'}.get('pax_kernel_commit')
    masked = 0
    for x, y in zip(la, lb):
        if x['type'] == SHT_NOBITS or x['name'] != y['name']:
            continue
        bx = bytearray(a[x['off']:x['off'] + x['size']])
        by = bytearray(b[y['off']:y['off'] + y['size']])
        if commit and x['name'] != '.text' and x['addr'] <= commit[0] < x['addr'] + x['size']:
            o = commit[0] - x['addr']
            for i in range(o, min(o + commit[1], len(bx), len(by))):
                if bx[i] != by[i]:
                    masked += 1
                bx[i] = by[i] = 0
        if bx != by:
            n = sum(1 for i in range(min(len(bx), len(by))) if bx[i] != by[i]) + abs(len(bx) - len(by))
            first = next((i for i in range(min(len(bx), len(by))) if bx[i] != by[i]), min(len(bx), len(by)))
            why.append(f'{x["name"]} differs at {n} bytes, the first at {where(ya, x["addr"] + first)}')
    if why:
        return False, 'differs: ' + '; '.join(why[:4])
    return True, (f'same: {len(la)} loaded sections, .text byte for byte, the rest but pax_kernel_commit '
                  f'({masked} of its bytes differ)')


# --- the self-test: small ELFs with .text, .data (holding pax_kernel_commit), .bss, a debug section and symbols ----
def build(text, data, bss=0x100, debug=b'path-a', commit=b'a' * 40, funcs=(('f0', 0, 8), ('f1', 8, 8))):
    shstr = b'\0.text\0.data\0.bss\0.debug_str\0.symtab\0.strtab\0.shstrtab\0'
    nm = lambda s: shstr.index(s.encode() + b'\0')
    data = data[:8] + commit + data[8 + len(commit):]
    strtab = b'\0' + b''.join(n.encode() + b'\0' for n, _o, _s in funcs) + b'pax_kernel_commit\0'
    syms = [b'\0' * 24]
    o = 1
    for n, off, size in funcs:
        syms.append(struct.pack('<IBBHQQ', o, 0x12, 0, 1, 0x1000 + off, size)); o += len(n) + 1
    syms.append(struct.pack('<IBBHQQ', o, 0x11, 0, 2, 0x2000 + 8, len(commit)))
    symtab = b''.join(syms)
    body = [(text, 1, 6, 0x1000), (data, 1, 3, 0x2000), (b'', SHT_NOBITS, 3, 0x3000), (debug, 1, 0, 0),
            (symtab, SHT_SYMTAB, 0, 0), (strtab, 3, 0, 0), (shstr, 3, 0, 0)]
    names = ['.text', '.data', '.bss', '.debug_str', '.symtab', '.strtab', '.shstrtab']
    out = bytearray(64)
    offs = []
    for blob, *_ in body:
        offs.append(len(out)); out += blob
    shoff = len(out)
    out += b'\0' * 64
    for (blob, typ, flags, addr), name, off in zip(body, names, offs):
        size = bss if typ == SHT_NOBITS else len(blob)
        link = 6 if name == '.symtab' else 0
        out += struct.pack('<IIQQQQIIQQ', nm(name), typ, flags, addr, off, size, link, 0, 8, 24 if name == '.symtab' else 0)
    out[0:16] = b'\x7fELF\x02\x01\x01' + b'\0' * 9
    struct.pack_into('<HHIQQQIHHHHHH', out, 16, 2, 62, 1, 0x1000, 0, shoff, 0, 64, 0, 0, 64, 8, 7)
    return bytes(out)


def selftest():
    import tempfile, os
    text, data = bytes(range(16)), bytes(64)
    cases = [
        ('the same build: same', build(text, data), build(text, data), True),
        ('another commit stamp and debug paths: same', build(text, data), build(text, data, commit=b'b' * 40, debug=b'path-b'), True),
        ('one .text byte (a call left in f1): differs, at f1', build(text, data), build(text[:9] + b'\xe8' + text[10:], data), False),
        ('.data outside the stamp: differs', build(text, data), build(text, data[:60] + b'\1' + data[61:]), False),
        ('.text longer: differs', build(text, data), build(text + b'\x90' * 4, data), False),
        ('.bss larger: differs', build(text, data), build(text, data, bss=0x140), False),
    ]
    bad = 0
    with tempfile.TemporaryDirectory() as td:
        for name, x, y, want in cases:
            pa, pb = os.path.join(td, 'a.elf'), os.path.join(td, 'b.elf')
            open(pa, 'wb').write(x); open(pb, 'wb').write(y)
            got, said = compare(pa, pb)
            ok = got == want and (name.split(', at ')[-1] in said if ', at ' in name else True)
            bad += not ok
            print(f'{"PASS" if ok else "FAIL"} ELF-SAME-SELFTEST {name}: {said}')
    print(f'elf-same-selftest: {len(cases) - bad} of {len(cases)} as wanted')
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        sys.exit(selftest())
    if len(sys.argv) != 3:
        sys.exit('usage: elf-same.py A B | --selftest')
    try:
        same, said = compare(sys.argv[1], sys.argv[2])
    except (OSError, ValueError, struct.error) as e:
        print(f'unreadable: {e}')
        sys.exit(2)
    print(said)
    sys.exit(0 if same else 1)
