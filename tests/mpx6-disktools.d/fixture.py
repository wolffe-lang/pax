#!/usr/bin/env python3
"""Compact CI installed tree; same playground session as the full local tree."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import shutil
import subprocess
import sys

repo, work, dest, kernel = map(Path, sys.argv[1:])
mk = SourceFileLoader('pax_mkdisk', str(repo / 'tools/mkdisk')).load_module()
tree = dest / 'tree'
if tree.exists(): shutil.rmtree(tree)
for d in ['bin', 'boot/EFI/BOOT', 'boot/limine', 'etc', 'root', 'home/pax', 'dev', 'proc', 'sys', 'tmp', 'usr/share/tunes']:
    (tree / d).mkdir(parents=True, exist_ok=True)
programs = {x: work / 'bin' / x for x in ['paxgpt', 'paxfat', 'paxext2']}
programs.update({x: work / 'bore' / x for x in ['cat', 'cp', 'env', 'ls']})
programs.update(sh=work/'pelt/pelt', pelt=work/'pelt/pelt', lope=work/'lope/lope', limine=work/'limine/limine', reboot=work/'probe/reboot')
for name, path in programs.items():
    shutil.copyfile(path, tree/'bin'/name)
    (tree/'bin'/name).chmod(0o755)
shutil.copyfile(kernel, tree/'boot/pax')
cache = Path(__import__('os').environ.get('PAX_CACHE', repo/'.pax-cache'))
shutil.copyfile(cache/'limine-12.9.1/BOOTX64.EFI', tree/'boot/EFI/BOOT/BOOTX64.EFI')
shutil.copyfile(cache/'limine-12.9.1/limine-bios.sys', tree/'boot/limine/limine-bios.sys')
guid = mk.uuid_of('pax-gpt-part:px69-fixture:1700000000:2')
(tree/'boot/limine/limine.conf').write_text(mk.root_conf(str(repo/'boot/limine-initramfs-quiet.conf'), guid, mk.uuid_of('pax-disk:pax-root:1700000000'), False))
(tree/'etc/passwd').write_text('root:x:0:0:root:/:/bin/pelt\npax:x:1000:1000:pax:/home/pax:/bin/pelt\n')
(tree/'etc/group').write_text('root:x:0:\npax:x:1000:\n')
(tree/'etc/motd').write_text('PAX disk tools fixture\n')
(tree/'etc/shrc').write_text((repo/'user/shrc').read_text()+'\ncd\n')
shutil.copyfile(repo/'user/fstab-root', tree/'etc/fstab')
(tree/'etc/pax-run.play').write_text('/bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m\n')
(tree/'etc/pax-run').write_text((tree/'etc/pax-run.play').read_text())
(tree/'usr/share/tunes/readme').write_text('directory used by the persistent lope session\n')
# Every input's metadata is explicit, including the attrs file itself.
attrs = ['/ 755 0 0 0', '/etc/disktools.attrs 644 0 0 0']
for p in sorted(tree.rglob('*')):
    name = '/'+str(p.relative_to(tree))
    mode = 0o755 if p.is_dir() or name.startswith('/bin/') else 0o644
    uid = gid = 0
    if name == '/home/pax': uid = gid = 1000
    if name == '/root': mode = 0o700
    if name == '/tmp': mode = 0o1777
    if name in ['/proc', '/sys']: mode = 0o555
    attrs.append('%s %o %d %d 0' % (name, mode, uid, gid))
(dest/'attrs').write_text('\n'.join(attrs)+'\n')
(tree/'etc/disktools.attrs').write_text((dest/'attrs').read_text())
subprocess.run([str(work/'bin/paxext2'),'--from',str(tree),'--attrs',str(dest/'attrs'),'--label','pax-root','--inodes','16384','467644416',str(dest/'expected.img')],check=True)
env='/bin/env SOURCE_DATE_EPOCH=1700000000 '
commands=['/bin/cp /etc/pax-run.play /etc/pax-run',env+'/bin/paxgpt --seed px69-fixture /dev/vdb 1:esp:4096:135167:esp 2:linux:135168:1048535:root 3:bios:2048:4095:bios',env+'/bin/paxfat --offset 2M --seed px69-fixture mkfs /dev/vdb 64M']
for d in ['/EFI','/EFI/BOOT','/boot','/boot/limine']:commands.append(env+f'/bin/paxfat --offset 2M mkdir /dev/vdb {d}')
for a,b in [('boot/EFI/BOOT/BOOTX64.EFI','EFI/BOOT/BOOTX64.EFI'),('boot/limine/limine.conf','boot/limine/limine.conf'),('boot/limine/limine-bios.sys','boot/limine/limine-bios.sys'),('boot/pax','boot/pax')]:commands.append(env+f'/bin/paxfat --offset 2M copy /dev/vdb /{a} /{b}')
commands += [env+'/bin/paxext2 --from / --attrs /etc/disktools.attrs --exclude /dev --exclude /proc --exclude /sys --exclude /tmp --exclude /lost+found --label pax-root --inodes 16384 --offset 66M 467644416 /dev/vdb','/bin/limine bios-install /dev/vdb 3']
(tree/'etc/pax-run').write_text('\n'.join(commands)+'\n')
args=[]
for line in attrs[1:]:
    n,mode,uid,gid,_=line.split();p=tree/n.lstrip('/')
    args.append(n+'/:'+':'.join([mode,uid,gid]) if p.is_dir() else n+'='+str(p)+':'+':'.join([mode,uid,gid]))
subprocess.run([str(repo/'tools/mkinitramfs'),str(dest/'bootstrap.cpio'),*args],check=True)
