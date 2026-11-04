#!/usr/bin/env python3
"""px92: the dev stick against the qualified release stick.

    dev-compare.py PAX_ROOT REL_STICK DEV_STICK REL_LIVE.cpio DEV_LIVE.cpio PAXFAT

1. Every ESP file the stick boots from or reads (the kernel, Limine's EFI and BIOS files, Limine's
   configuration, the install list) byte-identical between the two sticks.
2. The two live archives, row by row (mode, owner, bytes): the paths only in the dev archive, only in the
   release archive, and in both but different, each listed; the installer, the disk tools, Limine's installer,
   reboot/poweroff, the boot files and the install payload (bin/, boot/, usr/share/pax-install/) must not differ.
   Prints UNEXPECTED for any differing path outside the dev additions' classes. Exit 1 on a check that fails.
"""
from pathlib import Path
import fnmatch, hashlib, importlib.machinery, importlib.util, struct, subprocess, sys

root, rel, dev, relc, devc, paxfat = map(Path, sys.argv[1:7])
loader = importlib.machinery.SourceFileLoader('pax_distribution', str(root/'tools/distribution-root'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec); loader.exec_module(m)
bad = 0


def esp(img):
    with open(img, 'rb') as f:
        f.seek(512); h = f.read(92); a = struct.unpack_from('<Q', h, 72)[0]; f.seek(a * 512); e = f.read(128)
    return struct.unpack_from('<Q', e, 32)[0] * 512


for path in ['/boot/pax', '/EFI/BOOT/BOOTX64.EFI', '/boot/limine/limine-bios.sys', '/boot/limine/limine.conf',
             '/pax/install-targets']:
    a = subprocess.run([str(paxfat), '--offset', str(esp(rel)), 'cat', str(rel), path], capture_output=True, check=True).stdout
    b = subprocess.run([str(paxfat), '--offset', str(esp(dev)), 'cat', str(dev), path], capture_output=True, check=True).stdout
    same = a == b
    bad |= not same
    print(f"{'PASS' if same else 'FAIL'} ESP {path}: release {hashlib.sha256(a).hexdigest()[:16]}... "
          f"dev {hashlib.sha256(b).hexdigest()[:16]}... ({len(b)} bytes){'' if same else ' DIFFER'}")
# The ESP's /boot/initramfs.cpio is held to DEV_LIVE.cpio by tools/check-usb's U2 (its sha256 against the
# file's) in sdevstick and sdevline; `paxfat cat` of a 545 MB file ran over six minutes at 100% CPU with nothing
# written (stopped; not the installer's path), so it is not read again here.
print(f"ESP /boot/initramfs.cpio: held to {devc.name} (sha256 {hashlib.sha256(devc.read_bytes()).hexdigest()}) by check-usb's U2")

R = m.read_cpio(relc.read_bytes())
D = m.read_cpio(devc.read_bytes())
only_dev = sorted(set(D) - set(R))
only_rel = sorted(set(R) - set(D))
changed = sorted(k for k in set(R) & set(D) if R[k] != D[k])
DEV_CLASSES = ['usr/bin', 'usr/bin/*', 'usr/lib', 'usr/lib/wolf-musl', 'usr/lib/wolf-musl/*',
               'usr/share/wolf/compiler-std', 'usr/share/wolf/compiler-std/*', 'etc/shrc', 'etc/pax-files.sha256']
held = [k for k in only_dev + only_rel + changed
        if k == 'bin' or k.startswith(('bin/', 'boot/', 'usr/share/pax-install/')) or k in ('boot', 'usr/share/pax-install')]
print(f"{'PASS' if not held else 'FAIL'} archives: bin/, boot/ and usr/share/pax-install/ identical "
      f"({sum(1 for k in R if k.startswith(('bin/', 'boot/', 'usr/share/pax-install/')))} rows)" + ('' if not held else f': {held}'))
bad |= bool(held)
for k in ('bin/pax-install', 'bin/paxgpt', 'bin/paxfat', 'bin/paxext2', 'bin/limine', 'bin/reboot', 'bin/poweroff', 'boot/pax'):
    print(f"  {k}: {'equal' if R.get(k) == D.get(k) else 'DIFFER'} sha256 {hashlib.sha256(D[k][3]).hexdigest()[:16]}...")


def classes(keys):
    out = {}
    for k in keys:
        c = next((p for p in DEV_CLASSES if fnmatch.fnmatchcase(k, p)), None)
        top = c if c else 'UNEXPECTED ' + k
        out[top] = out.get(top, 0) + 1
    return out


print(f"only in dev ({len(only_dev)}): {classes(only_dev)}")
print(f"only in release ({len(only_rel)}): {classes(only_rel)}")
print(f"in both, different ({len(changed)}): {classes(changed)}")
for k in only_dev:
    if k.count('/') <= 2:
        print(f"  + {k} {oct(D[k][0])} {len(D[k][3])} bytes")
if 'etc/shrc' in changed:
    r = R['etc/shrc'][3].decode().splitlines(); d = D['etc/shrc'][3].decode().splitlines()
    print('etc/shrc: the dev lines: ' + repr([l for l in d if l not in r]) + '; release-only lines: ' + repr([l for l in r if l not in d]))
for k in changed:
    if k not in ('etc/shrc', 'etc/pax-files.sha256'):
        print(f"  ~ {k}: release {R[k][3][:120]!r} dev {D[k][3][:120]!r}")
unexpected = [k for k in only_dev + only_rel + changed if not any(fnmatch.fnmatchcase(k, p) for p in DEV_CLASSES)]
print(('UNEXPECTED: ' + repr(unexpected)) if unexpected else 'PASS archives: every differing path is a dev addition, etc/shrc or the file inventory')
sys.exit(1 if bad else 0)
