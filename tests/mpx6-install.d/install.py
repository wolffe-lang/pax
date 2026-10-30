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
fault=os.environ.get('PAX_INSTALL_FAULT','')
guided=os.environ.get('PAX_INSTALL_GUIDED','')=='1' or fault=='cancel-words'
full_tree=len(sys.argv)>6 and sys.argv[6]=='full'
assert games in ['yes','no'] and name in ['vdb','vdc']
work.mkdir(parents=True,exist_ok=True)
source=work/'source'; source.mkdir()
dt=lane/'build/disktools';full=lane/'build/full'
kernel=Path((dt/(os.environ.get('PAX_INSTALL_TIER','native')+'.elf.path')).read_text().strip())
cache=Path(os.environ.get('PAX_CACHE',repo/'.pax-cache'))

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
if full_tree:
    programs.update({p.name:p for p in (full/'bore').iterdir() if p.is_file() and os.access(p,os.X_OK)})
    for n in ['aspen','yew','su','play','lupin']: programs[n]=full/n/n
    for n in ['scent','egrep','fgrep']: programs[n]=full/'scent'/n
    programs['as']=full/'bin/as'
for n,p in programs.items():
    if p.read_bytes()[:4]==b'\x7fELF':run(['strip','-o',source/'bin'/n,p])
    else:shutil.copyfile(p,source/'bin'/n)
    (source/'bin'/n).chmod(0o755)
if full_tree:
    shutil.copytree(full/'std/std',source/'usr/share/wolf/std')
    shutil.copytree(repo/'user/lupin',source/'usr/share/lupin')
    for p in (repo/'user/tunes').iterdir():shutil.copyfile(p,source/'usr/share/tunes'/p.name)
    shutil.copyfile(full/'localtime',source/'etc/localtime')
    os.symlink('scent',source/'bin/grep')
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
# gm01: every game tools/mkgames built, with its source and its engine's
for row in (repo/'user/install/games.txt').read_text().splitlines():
    if row.strip() and not row.startswith('#'):
        g=row.split()[0]
        for f in [g,g+'.source.tar.gz',g+'.engine.source.tar.gz']:shutil.copyfile(full/'games'/f,payload/'games'/f)
shutil.copyfile(full/'games/games.sha256',payload/'games.sha256')
(payload/'boot.sha256').write_text(''.join(sha(source/p)+'  /'+p+'\n' for p in ['boot/pax','boot/limine/limine-bios.sys','boot/EFI/BOOT/BOOTX64.EFI']))
if fault=='missing-boot':(source/'boot/pax').unlink()
if fault=='corrupt-boot':
    with (source/'boot/pax').open('ab') as f:f.write(b'corrupt')
if fault in ['gpt','fat','root','limine']:
    executable={'gpt':'paxgpt','fat':'paxfat','root':'paxext2','limine':'limine'}[fault]
    (source/'bin'/executable).write_text('#!/bin/sh\nexit 2\n')
if fault=='invalid-manifest':
    shutil.copyfile(source/'bin/paxext2',source/'bin/paxext2.real')
    (source/'bin/paxext2').write_text('#!/bin/sh\nprev=\nfor arg do\n if [ "$prev" = --attrs ]; then printf "not a manifest\\n" > "$arg"; fi\n prev=$arg\ndone\nexec /bin/paxext2.real "$@"\n')
seed='px71-'+games+'-'+name
minor,seq=(16,2) if name=='vdb' else (32,3)
capacity=77611520 if fault=='enospc' else int(os.environ.get('PAX_INSTALL_CAPACITY','536870912'))
assert capacity >= 77611520 and capacity % 512 == 0
assert not fault or capacity in (77611520,536870912), 'large-image faults need a bounded guard, never a full-hole hash'
root_bytes=min(17592186040320,(capacity-33*512)//4096*4096-69206016)
ratio=4096 if root_bytes < 536870912 else 16384 if root_bytes < 4398046511104 else 32768
sparse_zeroes=os.environ.get('PAX_INSTALL_SPARSE_ZEROES','')=='1'
needed=1<<30 if sparse_zeroes else root_bytes//ratio*256
assert shutil.disk_usage(work).free > needed + (2<<30), 'insufficient space for initialized inode tables'
token=f'ERASE /dev/{name} 254:{minor}-seq{seq} {capacity} {seed}'
if fault=='wrong-token':token+='-WRONG'
script=work/'install.sh'
# px78: the target is named on an install allow-list by its serial (the
# virtio disk's GET_ID string, QEMU's serial=; a virtio disk shows no model).
serial='PX71-'+name.upper()
(work/'allow-list').write_text(f'# px71 rig: the target alone\nmodel= serial={serial}\n')
allow='--allow-list /etc/pax-install-targets'
script.write_text(f'/bin/pax-install --install --ext2-preview --target {name} --seed {seed} --user pax --games {games} --source /source --payload /payload {allow} --confirm "{token}"\n'
                  'echo INSTALL-EXIT-$?\n')
if guided:
    script.write_text(f'/bin/pax-install --seed {seed} --source /source --payload /payload {allow}\necho INSTALL-EXIT-$?\n')
    (work/'keys').write_text(('2' if name=='vdb' else '3')+'\npax\n'+('y' if games=='yes' else 'n')+'\nyes\nno\n')
# px78b (R-P6-confirm): every answer but yes cancels at the one
# confirmation, the target byte-identical: one boot, one guided run each.
words=['y','YES','q','',token]
if fault=='cancel-words':
    script.write_text(''.join(f'/bin/pax-install --seed {seed} --source /source --payload /payload {allow}\necho CANCEL-EXIT-$?\n' for _ in words)+'echo INSTALL-EXIT-1\n')
    (work/'keys').write_text(''.join(('2' if name=='vdb' else '3')+'\npax\nn\n'+w+'\n' for w in words))
if fault=='cancel':script.write_text(f"printf 'q\\n' | /bin/pax-install --seed test {allow}\necho INSTALL-EXIT-$?\n")
if fault=='missing-tool':script.write_text(script.read_text().replace('--payload /payload','--payload /payload --tool-dir /missing'))
(work/'run').write_text('/bin/sh /install.sh\n')
args=['/tmp/:1777','/bin/sh='+str(source/'bin/sh')+':755','/bin/pax-install='+str(source/'bin/pax-install')+':755',
      '/etc/pax-run='+str(work/'run')+':644','/install.sh='+str(script)+':644','/etc/pax-install-targets='+str(work/'allow-list')+':644']
# Formatters execute from the rescue environment, not the target.
for n in ['paxgpt','paxfat','paxext2','limine']+(['paxext2.real'] if fault=='invalid-manifest' else []):args.append('/bin/'+n+'='+str(source/'bin'/n)+':755')
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
with (work/'target.img').open('wb') as f:f.truncate(capacity)
guard=sha(work/'source-guard.img')
blank=sha(work/'target.img') if fault else None
cmd=[repo/'tools/qemu-halt','--accel','tcg','--firmware',os.environ.get('PAX_INSTALL_FIRMWARE','bios'),'--timeout',os.environ.get('PAX_INSTALL_TIMEOUT','1200'),'--elf',kernel,
     '--serial',work/'install.serial','--marker','halt','--qemu','-m','--qemu','1536M','--drive',str(work/'source-guard.img')+',ro']
if name=='vdc':cmd+=['--drive',str(work/'source-guard.img')+',ro']
if guided:cmd+=['--type',work/'keys','--prompt','pax-install> ']
# px76: no COM1 (kasumi has none); the transcript is PAX's own, from memory.
if os.environ.get('PAX_INSTALL_NOSERIAL','')=='1':
    assert not guided,'the serial-less row is the unattended install'
    cmd.insert(1,'--no-serial')
if sparse_zeroes:
    assert not fault, 'sparse backing optimization is only a positive install fixture'
    cmd+=['--qemu','-drive','--qemu',f'file={work/"target.img"},if=none,id=bigroot,format=raw,detect-zeroes=unmap,discard=unmap',
          '--qemu','-device','--qemu',f'virtio-blk-pci,drive=bigroot,serial={serial}']
else:
    # px84 (R-px84-1 A): a 4Kn target, 4096-byte logical sectors, refused by name.
    cmd+=['--drive',str(work/'target.img')+(',ro' if fault=='readonly' else '')+';serial='+serial+(',logical_block_size=4096,physical_block_size=4096' if fault=='4kn' else '')]
cmd+=[work/'boot.iso']
t=time.monotonic();p=run(cmd,False);install_seconds=time.monotonic()-t
(work/'install.boot').write_bytes(p.stdout+p.stderr)
(work/'install-timing.json').write_text(json.dumps({'capacity_bytes':capacity,'root_bytes':root_bytes,'install_seconds':install_seconds,'qemu_zero_unmap':sparse_zeroes})+'\n')
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
s=(work/'install.serial').read_text(errors='replace')
if fault:
    assert 'INSTALL-EXIT-1' in s,s[-8000:]
    assert sha(work/'source-guard.img')==guard
    if fault in ['missing-boot','corrupt-boot','readonly','cancel','cancel-words','wrong-token','4kn']:
        assert sha(work/'target.img')==blank,'prewrite refusal changed target'
        # px78: a read-only disk is refused before the allow-list is read, by name.
        expected={'missing-boot':'stopped: io','corrupt-boot':'corrupt_asset','readonly':'refused: read-only: /dev/vdb','cancel':'cancelled','cancel-words':'cancelled','wrong-token':'unconfirmed','4kn':'pax-install: refused: sector_size'}[fault]
        assert expected in s,s[-8000:]
        if fault=='cancel-words':
            # A virtio disk shows no model (allow.lu); its serial is QEMU's serial=.
            flat=s.replace('\r','')
            for line in [f'Erase (no model), serial {serial} (0.5 GB, /dev/{name}), and install PAX?\n','The root file system is ext2 without a journal.\n','Type yes to install; anything else cancels: ']:
                assert flat.count(line)==len(words),'FAIL I-cancel-words: the summary: '+line+'\n'+flat[-8000:]
            assert flat.count('pax-install: cancelled/refused before writes: cancelled')==len(words),'FAIL I-cancel-words: a word did not cancel\n'+flat[-8000:]
            assert flat.count('CANCEL-EXIT-1')==len(words) and 'CANCEL-EXIT-0' not in flat,'FAIL I-cancel-words: an exit\n'+flat[-8000:]
            assert 'phase gpt' not in flat and 'Type ext2-preview' not in flat,'FAIL I-cancel-words: a write began or the old prompt\n'+flat[-8000:]
            print('PASS I-cancel-words: y, YES, q, empty and the old token each cancel at the summary naming the disk; target byte-identical',flush=True)
        if fault=='4kn':
            # The kernel names the device's 4096-byte blocks; the planner refuses the target.
            assert 'refused: a partition table on logical blocks of 4096 bytes' in s and 'vdb is the whole disk' in s,s[-8000:]
            print('PASS I-4kn-refused: 4096-byte logical sectors named sector_size before any write; target byte-identical',flush=True)
    else:
        with (work/'target.img').open('rb') as f:f.seek(65536);raw=f.read(65536).split(b'\0',1)[0]
        records=[json.loads(x) for x in raw.splitlines()]
        phase='root' if fault in ['enospc','invalid-manifest'] else ('gpt' if fault=='missing-tool' else fault)
        assert records[-1]['phase']==phase and records[-1]['state']=='failed',records
        assert not any(x['state']=='complete' for x in records)
        if fault in ['gpt','fat','root','limine']:assert 'exit=2' in records[-1]['detail']
    print('PASS I-fault-'+fault+': named refusal, no swallowed exit or bootability claim; source guard unchanged',flush=True)
    sys.exit(0)
assert 'INSTALL-EXIT-0' in s,('FAIL I-boot-files' if 'phase verify-boot-' in s else 'FAIL I-install')+'\n'+s[-18000:]
assert sha(work/'source-guard.img')==guard
with (work/'target.img').open('rb') as f:
    f.seek(65536);log=f.read(65536).split(b'\0',1)[0]
records=[json.loads(x) for x in log.splitlines()]
assert records[-1]['phase']=='result' and records[-1]['state']=='complete',records
assert {x['phase'] for x in records if x['state']=='durable'}=={'gpt','fat',*[f'mkdir-{i}' for i in range(4)],*[f'copy-boot-{i}' for i in range(4)],'root','limine','verify-gpt',*[f'verify-boot-{i}' for i in range(4)]},records
(work/'phases.jsonl').write_bytes(log)
# Extract only allocated extents, retaining holes. A multi-terabyte target
# must never be scanned or hashed from byte zero to its logical end.
with (work/'target.img').open('rb') as f,(work/'root.img').open('wb') as out:
    start,end=69206016,69206016+root_bytes
    out.truncate(root_bytes)
    at=start
    while at < end:
        try: data=os.lseek(f.fileno(),at,os.SEEK_DATA)
        except OSError as e:
            if e.errno == 6: break # ENXIO: no more allocated data
            raise
        if data >= end: break
        hole=min(os.lseek(f.fileno(),data,os.SEEK_HOLE),end)
        f.seek(data)
        while data < hole:
            b=f.read(min(hole-data,1048576));assert b
            if b.count(0) != len(b):out.seek(data-start);out.write(b)
            data+=len(b)
        at=hole
p=run(['e2fsck','-fn',work/'root.img']);(work/'root.fsck').write_bytes(p.stdout+p.stderr)
assert b'WARNING' not in p.stdout+p.stderr,p.stdout+p.stderr
p=run(['dumpe2fs','-h',work/'root.img']);(work/'root.geometry').write_bytes(p.stdout+p.stderr)
with (work/'root.img').open('rb') as f:
    import struct
    f.seek(1024);sb=f.read(1024)
    blocks,bpg,ipg=(struct.unpack_from('<I',sb,o)[0] for o in (4,32,40))
    groups=(blocks+bpg-1)//bpg
    expected_ipg=((root_bytes//ratio+groups-1)//groups+15)//16*16
    assert ipg==expected_ipg and struct.unpack_from('<I',sb,0)[0]==groups*expected_ipg,'I-density'
print(f'PASS I-density: root {root_bytes} bytes; {groups*ipg} inodes; ratio {ratio}',flush=True)
print(f'PASS I-install-{games}-{name}: guest executor complete, durable phase log, source guard unchanged, e2fsck clean; install {install_seconds:.2f}s; with verification {time.monotonic()-t:.2f}s',flush=True)
