#!/usr/bin/env python3
"""Three matched rescue boots with/without checking; both archives carry both binaries."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys

repo, work = Path(sys.argv[1]), Path(sys.argv[2])
p=work/'measure-boot';p.mkdir(exist_ok=True)
noop=work/'no-check'
assert noop.exists()
rows=[]
for mode in ['without', 'with']:
    runfile=p/(mode+'.run')
    runfile.write_text('/bin/fsck.ext2 -fn /dev/vda2\n' if mode=='with' else '/bin/no-check\n')
    archive=p/(mode+'.cpio')
    subprocess.run([str(repo/'tools/mkinitramfs'),str(archive),
                    '/bin/fsck.ext2='+str(work/'bin/fsck.ext2')+':755',
                    '/bin/no-check='+str(noop)+':755', '/etc/pax-run='+str(runfile)+':644'],check=True,stdout=subprocess.DEVNULL)
    image=p/(mode+'.img')
    shutil.copyfile(work/'native/rescue/base.img',image)
    for source,destination in [(archive,'::/boot/initramfs.cpio'),
                               (work/'native/rescue/rescue.conf','::/boot/limine/limine.conf')]:
        subprocess.run([str(repo/'tools/disktools'),str(work),'mcopy','-o','-i',str(image)+'@@2097152',str(source),destination],check=True)
    times=[]
    for i in range(3):
        serial=p/f'{mode}-{i}.serial'
        subprocess.run(['python3','-I',str(repo/'tests/mpx6-fsck.d/boot.py'),str(repo),str(image),str(serial),'bios','halt'],check=True)
        text=serial.read_text()
        assert ('fsck.ext2 pid 1 exit_group 0' if mode=='with' else 'no-check pid 1 exit_group 0') in text,text
        meta=Path(str(serial)+'.meta').read_text()
        times.append(float(re.search(r'elapsed: ([0-9.]+)s',meta)[1]))
    rows.append({'mode':mode,'bios_native_boot_seconds':times})
    print(json.dumps(rows[-1]),flush=True)
(p/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
