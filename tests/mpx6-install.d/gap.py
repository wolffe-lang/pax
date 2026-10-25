#!/usr/bin/env python3
"""Black-box Limine byte ownership; log LAST, original disk never modified."""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

work=Path(sys.argv[1]);limine=Path(sys.argv[2]);candidate=work/'log-last.img'
subprocess.run(['cp','--sparse=always',work/'target.img',candidate],check=True)
with candidate.open('r+b') as f:
    f.write(bytes(440));f.seek(1048576);f.write(bytes(1048576))
    f.seek(0);before=f.read(2097152)
(work/'limine-before.bin').write_bytes(before)
p=subprocess.run([limine,'bios-install',candidate,'3'],capture_output=True)
(work/'limine-linux.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,(p.stdout,p.stderr)
with candidate.open('rb') as f:after=f.read(2097152)
(work/'limine-after.bin').write_bytes(after)
ranges=[];start=None
for i,(a,b) in enumerate(zip(before,after)):
    if a!=b and start is None:start=i
    if a==b and start is not None:ranges.append([start,i]);start=None
if start is not None:ranges.append([start,len(after)])
assert ranges and all(end<=65536 or start>=131072 for start,end in ranges),ranges
prefix=[i for i in range(1048576) if before[i]!=after[i]]
bios=[i for i in range(1048576,2097152) if before[i]!=after[i]]
envelopes=[min(prefix),max(prefix)+1,min(bios),max(bios)+1]
s=(work/'install.serial').read_text(errors='replace')
m=re.search(r'Limine changed-byte envelopes: prefix \[(\d+),(\d+)\), BIOS partition \[(\d+),(\d+)\)',s)
assert m and list(map(int,m.groups()))==envelopes,(envelopes,m.groups() if m else None)
with candidate.open('rb') as a,(work/'target.img').open('rb') as b:
    assert hashlib.file_digest(a,'sha256').digest()==hashlib.file_digest(b,'sha256').digest(),'PAX bios-install differs from Linux oracle'
marker=b'{"v":1,"phase":"oracle-log-last","state":"durable","detail":"written after bios-install; no resume authority"}\n'
with candidate.open('r+b') as f:
    f.seek(65536);old=f.read(65536).split(b'\0',1)[0];assert len(old)+len(marker)<65536
    f.seek(65536);f.write((old+marker).ljust(65536,b'\0'));f.flush();__import__('os').fsync(f.fileno())
    f.seek(0);last=f.read(2097152)
(work/'limine-after-log.bin').write_bytes(last)
assert last[:65536]==after[:65536] and last[131072:]==after[131072:]
(work/'limine-ranges.json').write_text(json.dumps({'argv':['bios-install','DEVICE','3'],'log':[65536,131072],'envelopes':envelopes,'changed_byte_ranges':ranges},indent=2)+'\n')
print(f'PASS I-log-disjoint: Limine envelopes {envelopes}; exact ranges dumped; PAX equals Linux, log last changes only [65536,131072)')
