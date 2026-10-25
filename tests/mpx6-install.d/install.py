#!/usr/bin/env python3
"""Install from read-only rescue contents onto a separate QEMU virtio disk.
Built program inputs are Ubuntu-baseline static binaries, never host tools.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

repo,lane,work=map(Path,sys.argv[1:4]);games,name=sys.argv[4:6]
assert games in ['yes','no'] and name in ['vdb','vdc']
work.mkdir(parents=True,exist_ok=True)
source=work/'source'; source.mkdir()
dt=lane/'build/disktools';full=lane/'build/full'
kernel=Path((dt/'native.elf.path').read_text().strip())
cache=lane/'cache'

def run(args,ok=True):
    p=subprocess.run([str(x) for x in args],capture_output=True)
    if ok: assert p.returncode==0,(args,p.returncode,p.stdout[-8000:],p.stderr[-8000:])
    return p

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

for d in ['bin','boot/EFI/BOOT','boot/limine','etc','root','home/pax','dev','proc','sys','tmp','usr/share/tunes']:
    (source/d).mkdir(parents=True,exist_ok=True)
programs={n:dt/'bore'/n for n in ['cat','cp','env','ls']}
programs.update(sh=full/'pelt/pelt',pelt=full/'pelt/pelt',lope=full/'lope/lope',reboot=full/'probe/reboot')
programs.update({n:dt/'bin'/n for n in ['paxgpt','paxfat','paxext2']})
programs.update(limine=dt/'limine/limine',**{'pax-install':lane/'build/install-gate/bin/pax-install'})
for n,p in programs.items():
    run(['strip','-o',source/'bin'/n,p]);(source/'bin'/n).chmod(0o755)
shutil.copyfile(kernel,source/'boot/pax')
for src,dst in [('BOOTX64.EFI','boot/EFI/BOOT/BOOTX64.EFI'),('limine-bios.sys','boot/limine/limine-bios.sys')]:
    shutil.copyfile(cache/'limine-12.9.1'/src,source/dst)
(source/'boot/limine/limine.conf').write_text('old source configuration must be replaced\n')
(source/'etc/passwd').write_text('root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\n')
(source/'etc/group').write_text('root:x:0:\npax:x:1000:\n')
(source/'etc/motd').write_text('PAX installer test source\n')
(source/'etc/shrc').write_text((repo/'user/shrc').read_text()+'\ncd\n')
(source/'etc/pax-run').write_text('/bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m\n')
shutil.copyfile(repo/'user/fstab-root',source/'etc/fstab')
os.symlink('../proc/self/mounts',source/'etc/mtab')
(source/'usr/share/tunes/readme').write_text('persistent lope test directory\n')
payload=work/'payload';(payload/'games').mkdir(parents=True)
shutil.copyfile(repo/'user/install/games.txt',payload/'games.txt')
shutil.copyfile(full/'pack/pack',payload/'games/pack')
shutil.copyfile(full/'pack/games.sha256',payload/'games.sha256')
(payload/'boot.sha256').write_text(''.join(sha(source/p)+'  /'+p+'\n' for p in ['boot/pax','boot/limine/limine-bios.sys','boot/EFI/BOOT/BOOTX64.EFI']))
seed='px71-'+games+'-'+name
minor,seq=(16,2) if name=='vdb' else (32,3)
token=f'ERASE /dev/{name} 254:{minor}-seq{seq} 536870912 {seed}'
script=work/'install.sh'
script.write_text(f'/bin/pax-install --install --ext2-preview --target {name} --seed {seed} --user pax --games {games} --source /source --payload /payload --confirm "{token}"\n'
                  'echo INSTALL-EXIT-$?\n')
(work/'run').write_text('/bin/sh /install.sh\n')
args=['/tmp/:1777','/bin/sh='+str(source/'bin/sh')+':755','/bin/pax-install='+str(source/'bin/pax-install')+':755',
      '/etc/pax-run='+str(work/'run')+':644','/install.sh='+str(script)+':644']
# Formatters execute from the rescue environment, not the target.
for n in ['paxgpt','paxfat','paxext2','limine']:args.append('/bin/'+n+'='+str(source/'bin'/n)+':755')
for base,prefix in [(source,'/source'),(payload,'/payload')]:
    for p in [base,*sorted(base.rglob('*'))]:
        rel=prefix+('/'+p.relative_to(base).as_posix() if p!=base else '')
        if p.is_symlink():args.append(rel+'->'+os.readlink(p));continue
        mode=0o755 if p.is_dir() or '/bin/' in rel else 0o644
        uid=gid=1000 if rel=='/source/home/pax' else 0
        if rel=='/source/root':mode=0o700
        if rel=='/source/tmp':mode=0o1777
        if rel in ['/source/proc','/source/sys']:mode=0o555
        args.append(rel+'/:'+f'{mode:o}:{uid}:{gid}' if p.is_dir() else rel+'='+str(p)+f':{mode:o}:{uid}:{gid}')
run([repo/'tools/mkinitramfs',work/'init.cpio',*args])
run([repo/'tools/mkimage','--conf',repo/'boot/limine-initramfs.conf','--add',work/'init.cpio','initramfs.cpio',kernel,work/'boot.iso'])
with (work/'source-guard.img').open('wb') as f:f.truncate(8*1024*1024)
with (work/'target.img').open('wb') as f:f.truncate(512*1024*1024)
guard=sha(work/'source-guard.img')
cmd=[repo/'tools/qemu-halt','--accel','tcg','--firmware','bios','--timeout','1200','--elf',kernel,
     '--serial',work/'install.serial','--marker','halt','--qemu','-m','--qemu','1536M','--drive',str(work/'source-guard.img')+',ro']
if name=='vdc':cmd+=['--drive',str(work/'source-guard.img')+',ro']
cmd+=['--drive',work/'target.img',work/'boot.iso']
t=time.monotonic();p=run(cmd,False);(work/'install.boot').write_bytes(p.stdout+p.stderr)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
s=(work/'install.serial').read_text(errors='replace')
assert 'INSTALL-EXIT-0' in s,s[-18000:]
assert sha(work/'source-guard.img')==guard
with (work/'target.img').open('rb') as f:
    f.seek(65536);log=f.read(65536).split(b'\0',1)[0]
records=[json.loads(x) for x in log.splitlines()]
assert records[-1]['phase']=='result' and records[-1]['state']=='complete',records
assert {x['phase'] for x in records if x['state']=='durable'}=={'gpt','fat',*[f'mkdir-{i}' for i in range(4)],*[f'copy-boot-{i}' for i in range(4)],'root','limine','verify-gpt',*[f'verify-boot-{i}' for i in range(4)]},records
(work/'phases.jsonl').write_bytes(log)
with (work/'target.img').open('rb') as f,(work/'root.img').open('wb') as out:
    f.seek(69206016);left=467644416
    while left:
        b=f.read(min(left,1048576));assert b;out.write(b);left-=len(b)
p=run(['e2fsck','-fn',work/'root.img']);(work/'root.fsck').write_bytes(p.stdout+p.stderr)
assert b'WARNING' not in p.stdout+p.stderr,p.stdout+p.stderr
print(f'PASS I-install-{games}-{name}: guest executor complete, durable phase log, source guard unchanged, e2fsck clean; {time.monotonic()-t:.2f}s',flush=True)
