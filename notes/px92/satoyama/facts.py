#!/usr/bin/env python3
"""px92: the bytes behind d2cmp's differences. The dev archives of 9c88ec8a and 8b4e98ae differ in bin/ and
usr/share/pax-install/boot.sha256 although no source of those programs changed between the two heads; for each
differing file: its differing byte ranges, the bytes there in both, and which stamping input appears at them
(the head as 40 or 8 hex digits, SOURCE_DATE_EPOCH as decimal text or a little-endian 32/64-bit word).

    facts.py PAX_ROOT OLD_DEV.cpio NEW_DEV.cpio GAUNTLET_DEV.cpio OUTDIR
"""
import hashlib, importlib.machinery, importlib.util, struct, subprocess, sys
from pathlib import Path
root, old, new, gnew, out = map(Path, sys.argv[1:6])
out.mkdir(parents=True, exist_ok=True)
loader = importlib.machinery.SourceFileLoader('d', str(root/'tools/distribution-root'))
spec = importlib.util.spec_from_loader(loader.name, loader); m = importlib.util.module_from_spec(spec); loader.exec_module(m)
O = m.read_cpio(old.read_bytes()); N = m.read_cpio(new.read_bytes()); G = m.read_cpio(gnew.read_bytes())
heads = {'9c88ec8a': ('9c88ec8ac016d7a6df911b3922ff3cfb596188e8', 1793767182)}
nh = subprocess.run(['git', '-C', str(root), 'log', '-1', '--format=%H %ct', '8b4e98ae'], capture_output=True, text=True).stdout.split()
heads['8b4e98ae'] = (nh[0], int(nh[1]))
gh = subprocess.run(['git', '-C', str(root), 'log', '-1', '--format=%H %ct', 'HEAD'], capture_output=True, text=True).stdout.split()
print('heads and SOURCE_DATE_EPOCHs:', heads, 'gauntlet', gh)
stamps = {}
for name, (h, t) in heads.items():
    stamps[f'{name} head'] = h.encode(); stamps[f'{name} short'] = h[:8].encode()
    stamps[f'{name} epoch text'] = str(t).encode()
    stamps[f'{name} epoch u32'] = struct.pack('<I', t); stamps[f'{name} epoch u64'] = struct.pack('<Q', t)
diff = sorted(k for k in set(O) & set(N) if O[k] != N[k])
print('differing paths (9c88ec8a dev vs 8b4e98ae dev):', len(diff))
for k in diff:
    a, b = O[k][3], N[k][3]
    if k.startswith('usr/share/wolf/compiler-std') or k in ('usr/bin/wolf', 'usr/bin/wolf-cimport-worker', 'usr/bin/libwolf_rt.a', 'etc/pax-files.sha256'):
        continue
    found = {s: (s_bytes in a, s_bytes in b) for s, s_bytes in stamps.items() if s_bytes in a or s_bytes in b}
    if len(a) != len(b):
        print(f'{k}: sizes {len(a)} vs {len(b)}; stamps present (old, new): {found}')
    else:
        offs = [i for i in range(len(a)) if a[i] != b[i]]
        ranges = []
        for i in offs:
            if ranges and i <= ranges[-1][1] + 8: ranges[-1][1] = i
            else: ranges.append([i, i])
        print(f'{k}: {len(a)} bytes, {len(offs)} differ in {len(ranges)} range(s); stamps present (old, new): {found}')
        for lo, hi in ranges[:6]:
            s, e = max(0, lo - 8), min(len(a), hi + 9)
            print(f'   [{lo:#x},{hi + 1:#x}) old {a[s:e]!r}\n   {"":>{len(hex(lo)) + 10}}new {b[s:e]!r}')
    if k in G:
        print(f'   gauntlet head\'s {k}: {"= 8b4e98ae" if G[k] == N[k] else "differs from 8b4e98ae"}')
