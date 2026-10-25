#!/usr/bin/env python3
"""Independent host oracles: GPT, FAT, ext2 tree, game placement and owners."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import uuid

repo,work=map(Path,sys.argv[1:3]);games,name=sys.argv[3:5]
def run(*args):
    p=subprocess.run([str(x) for x in args],capture_output=True)
    assert p.returncode==0,(args,p.returncode,p.stdout,p.stderr)
    return p.stdout,p.stderr

disk=work/'target.img';root=work/'root.img';source=work/'source'
out,err=run('sgdisk','-v',disk)
(work/'gpt.verify').write_bytes(out+err)
assert b'No problems found' in out+err and b'Warning' not in out+err and b'error' not in (out+err).lower(),out+err
out,err=run('sfdisk','--json',disk)
table=json.loads(out)['partitiontable'];parts={int(p['start']):p for p in table['partitions']}
assert set(parts)=={2048,4096,135168},parts
assert parts[2048]['size']==2048 and parts[4096]['size']==131072 and parts[135168]['size']==913368,parts
seed='px71-'+games+'-'+name
guid=str(uuid.UUID(bytes=hashlib.sha256(f'pax-gpt-part:{seed}:1700000000:2'.encode()).digest()[:16]))
assert parts[135168]['uuid'].lower()==guid
with disk.open('rb') as f,(work/'fat.img').open('wb') as o:
    f.seek(2097152);o.write(f.read(67108864))
out,err=run('fsck.fat','-n',work/'fat.img')
(work/'fat.verify').write_bytes(out+err)
lines=(out+err).decode().splitlines()
assert len(lines)==2 and lines[0].startswith('fsck.fat ') and re.fullmatch(r'.*: \d+ files, \d+/\d+ clusters',lines[1]),lines
print('PASS I-oracles: sgdisk clean without regeneration warnings, exact sfdisk geometry/PARTUUID, strict fsck.fat output')
# Use the maintained tree oracle with direct e2fsprogs from this isolated
# oracle container. No patched filesystem-tool implementation or source.
wrapper=work/'e2fs-local'
wrapper.write_text('#!/bin/sh\nshift\nexec "$@"\n');wrapper.chmod(0o755)
mod=SourceFileLoader('px71_e2tree',str(repo/'tools/e2tree')).load_module();mod.E2FS=str(wrapper)
output=io.StringIO()
with contextlib.redirect_stdout(output): assert mod.main(['e2tree',str(root)])==0
listing=output.getvalue();(work/'target.tree').write_text(listing)
actual={x.split('\t')[0]:x.split('\t') for x in listing.splitlines()}
config=f'timeout: 0\nquiet: yes\n\n/PAX ext2 developer preview\n    protocol: limine\n    path: boot():/boot/pax\n    cmdline: quiet root=PARTUUID={guid} rootfstype=ext2 rw\n'
changes={'/boot/limine/limine.conf':config.encode(),'/etc/fstab':f'PARTUUID={guid} / ext2 rw 0 1\ntmpfs /tmp tmpfs nosuid,nodev 0 0\n'.encode()}
changed_meta=set(changes)|{'/etc/passwd','/etc/group','/home/pax'}
expected=set()
for p in sorted(source.rglob('*')):
    path='/'+p.relative_to(source).as_posix();expected.add(path)
    row=actual[path];mode=0o755 if p.is_dir() or path.startswith('/bin/') else 0o644
    uid=gid=1000 if path=='/home/pax' else 0
    if path=='/root':mode=0o700
    if path=='/tmp':mode=0o1777
    if path in ['/proc','/sys']:mode=0o555
    if p.is_symlink():mode=0o777
    assert int(row[2],8)==mode and int(row[3])==uid and int(row[4])==gid,(path,row)
    if p.is_symlink():assert row[-1]=='-> '+os.readlink(p),(path,row)
    elif p.is_file():
        content=changes.get(path,p.read_bytes())
        assert row[-1]==hashlib.sha256(content).hexdigest(),(path,row)
    for i in [8,9,10]:assert row[i]==('1700000000.000000000' if path in changed_meta else '0.000000000'),(path,row)
allowed=expected|{'/lost+found'}
if games=='yes':
    for path in ['/home/pax/Games','/home/pax/Games/pack','/home/pax/Games/pack/pack']:
        allowed.add(path);row=actual[path]
        assert int(row[2],8)==0o755 and row[3:5]==['1000','1000'],(path,row)
    digest=(work/'payload/games.sha256').read_text().split()[0]
    assert actual['/home/pax/Games/pack/pack'][-1]==digest
else:assert not any('/Games' in x for x in actual)
assert set(actual)==allowed,(set(actual)-allowed,allowed-set(actual))
for path in ['/boot/pax','/boot/limine/limine-bios.sys','/boot/limine/limine.conf','/EFI/BOOT/BOOTX64.EFI']:
    out,err=run('mtype','-i',work/'fat.img','::'+path)
    src='/boot'+path if path.startswith('/EFI') else path
    content=changes.get(src,(source/src.lstrip('/')).read_bytes())
    assert out==content,path
print(f'PASS I-tree-{games}: every source path, byte, mode, owner, link target and whole-second time; games {games} bytes/modes/owners; no hidden game payload')
print('PASS I-boot-files: independent FAT byte readback, new configuration and PARTUUID')
