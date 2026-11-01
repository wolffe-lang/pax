#!/usr/bin/env python3
"""Every external status stays loud; persisted phases and argv are independent."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

program,work=map(Path,sys.argv[1:]);work.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=work,prefix='executor-') as tmp:
    w=Path(tmp)
    mock=w/'mock'
    mock.write_text('#!/usr/bin/python3\nimport json,sys\nprint(json.dumps(sys.argv[2:]))\n'
                    'print("error: planted zero-exit diagnostic" if sys.argv[1]=="diagnostic" else "ok")\n'
                    'sys.exit(0 if sys.argv[1]=="diagnostic" else int(sys.argv[1]))\n')
    mock.chmod(0o755)
    for status in ['0','1','2','127','diagnostic']:
        d=w/status;d.mkdir();disk=d/'log.img';disk.write_bytes(bytes(131072))
        p=subprocess.run([program,disk,mock,d,status],capture_output=True,text=True)
        expected=0 if status=='0' else 1
        assert p.returncode==expected,('FAIL I-external-'+status,p.stdout,p.stderr)
        records=[json.loads(x) for x in disk.read_bytes()[65536:].split(b'\0',1)[0].splitlines()]
        assert records[0]['state']=='started'
        assert records[-1]['state']==('durable' if status=='0' else 'failed'),records
        assert json.loads((d/'witness.out').read_text().splitlines()[0])==['literal; $(touch NEVER)','two words']
        assert not (d/'NEVER').exists()
        if status=='2': assert 'exit=2' in records[-1]['detail']
        print('PASS I-external-'+status+': status/diagnostic checked and phase persisted; argv literal')

# px86: the zero phases, each alone and then all four, on a sparse file the
# size of the 512 MiB rig's target and of kasumi's 860: every byte of a
# patterned image outside the phase's ranges and the log reservation keeps
# its pattern, every byte inside reads zero, nothing is written outside the
# patterned regions but the ranges, and the log holds the phase's records
# (started, durable) and nothing else. zero-bios is the 860's fix: exactly
# [1 MiB, 2 MiB), PAX's BIOS boot partition, before Limine.
MIB=1<<20
def expected(n):
    """The ranges planner.lu holds plan.lu's wipes to, recomputed here."""
    end=(n-33*512)//4096*4096
    root=min(end-69206016,17592186040320)
    root_end=69206016+root
    backup=n-33*512
    gap=[(17408,65536),(131072,MIB)]
    if end<backup:gap.append((end,backup))
    if root_end<end:gap.insert(2,(max(root_end,end-MIB),end))
    return {'zero-bios':[(MIB,2*MIB)],
            'zero-esp':[(2*MIB,3*MIB),(2097152+67108864-MIB,2097152+67108864)],
            'zero-root':[(69206016,69206016+MIB),(root_end-MIB,root_end)],
            'zero-gap':gap}
def pattern(at,length):
    return hashlib.shake_256(b'px86 %d' % at).digest(length)
with tempfile.TemporaryDirectory(dir=work,prefix='wipe-') as tmp:
    w=Path(tmp)
    for n in [536870912,1000204886016]:
        ranges=expected(n)
        patterned=[(0,65536),(131072,72*MIB),(max(72*MIB,n-4*MIB),n)]
        for only in ['zero-bios','zero-esp','zero-root','zero-gap','all']:
            disk=w/f'{n}-{only}.img'
            with disk.open('wb') as f:
                f.truncate(n)
                for a,b in patterned:
                    f.seek(a)
                    for at in range(a,b,MIB):f.write(pattern(at,min(MIB,b-at)))
            p=subprocess.run([program,'--wipe',disk,str(n),only],capture_output=True,text=True)
            assert p.returncode==0,(f'FAIL I-{only}',p.stdout,p.stderr)
            zero=[r for k,v in ranges.items() if only in (k,'all') for r in v]
            with disk.open('rb') as f:
                for a,b in patterned:
                    f.seek(a)
                    for at in range(a,b,MIB):
                        got=f.read(min(MIB,b-at));want=bytearray(pattern(at,len(got)))
                        for z0,z1 in zero:
                            lo,hi=max(z0,at),min(z1,at+len(got))
                            if lo<hi:want[lo-at:hi-at]=bytes(hi-lo)
                        assert got==bytes(want),(f'FAIL I-{only}: {n} bytes: a byte outside the phase changed or inside it is not zero, in [{at},{at+len(got)})')
                for z0,z1 in zero:
                    f.seek(z0);assert f.read(z1-z0)==bytes(z1-z0),(f'FAIL I-{only}: [{z0},{z1}) not zero')
                # nothing written anywhere else: every allocated extent lies in a patterned region or a range
                at=0
                while at<n:
                    try:data=os.lseek(f.fileno(),at,os.SEEK_DATA)
                    except OSError:break
                    hole=os.lseek(f.fileno(),data,os.SEEK_HOLE)
                    for x in range(data,hole,4096):
                        assert any(a<=x<b for a,b in patterned+zero+[(65536,131072)]),(f'FAIL I-{only}: {n} bytes: a write at {x}, outside every range')
                    at=hole
                f.seek(65536);log=f.read(65536)
            records=[json.loads(x) for x in log.split(b'\0',1)[0].splitlines()]
            names=[k for k in ranges if only in (k,'all')]
            assert [(r['phase'],r['state']) for r in records]==[(k,s) for k in names for s in ('started','durable')],(f'FAIL I-{only}: the log',records)
            assert log.split(b'\0',1)[1]==bytes(65536-len(log.split(b'\0',1)[0])-1),(f'FAIL I-{only}: bytes after the records')
            for r in records:
                if r['state']=='started':assert r['detail']=='zero '+' '.join(f'[{a},{b})' for a,b in ranges[r['phase']]),r
            disk.unlink()
            print(f'PASS I-{"zero-all" if only == "all" else only}: {n} bytes: '+'; '.join(f'{k} '+' '.join(f'[{a},{b})' for a,b in ranges[k]) for k in names)+' zeroed and nothing else; the log holds its records alone',flush=True)
