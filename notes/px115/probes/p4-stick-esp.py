"""px115 probe P4: the stick image's ESP: where its archive and kernel are, and whether they are tools/mkdistribution's
dev.cpio and kernel byte for byte (mtools as a black box; the image read-only)."""
import hashlib, struct, subprocess, sys, json
from pathlib import Path
img, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
with open(img, 'rb') as f:
    f.seek(512)
    h = f.read(92)
    assert h[:8] == b'EFI PART'
    ent_lba, n, sz = struct.unpack('<QII', h[72:88])
    f.seek(ent_lba * 512)
    parts = []
    for i in range(n):
        e = f.read(sz)
        if e[:16] == b'\0' * 16:
            continue
        first, last = struct.unpack('<QQ', e[32:48])
        name = e[56:128].decode('utf-16le').rstrip('\0')
        parts.append(dict(n=i + 1, type=e[:16][::-1].hex(), first=first, last=last, bytes=(last - first + 1) * 512, name=name))
res = dict(image_bytes=img.stat().st_size, partitions=parts)
esp = [p for p in parts if p['name'] == 'esp' or p['n'] == 1][0]
at = esp['first'] * 512
res['mdir'] = subprocess.run(['mdir', '-/', '-i', f'{img}@@{at}', '::/'], capture_output=True).stdout.decode(errors='replace')
for path in ('/boot/pax', '/boot/initramfs.cpio', '/boot/limine/limine.conf', '/pax/install-targets'):
    r = subprocess.run(['mcopy', '-n', '-i', f'{img}@@{at}', '::' + path, str(out/'x')], capture_output=True)
    if r.returncode:
        res[path] = 'absent'
        continue
    d = (out/'x').read_bytes()
    res[path] = dict(bytes=len(d), sha256=hashlib.sha256(d).hexdigest()) if path != '/pax/install-targets' else dict(bytes=len(d), lines=d.count(b'\n'))
    if path == '/boot/limine/limine.conf':
        res['stick_limine_conf'] = d.decode(errors='replace')
    (out/'x').unlink()
print(json.dumps(res, indent=1))
