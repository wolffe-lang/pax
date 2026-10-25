#!/usr/bin/env python3
"""Independent lstat/hash oracle for the Wolf snapshot and staging manifest."""
from pathlib import Path
import hashlib
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

program, work = map(Path, sys.argv[1:])
work.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=work, prefix='snapshot-') as tmp:
    w=Path(tmp); src=w/'source'; src.mkdir()
    for d in ['dev','proc','sys','tmp','lost+found','bin',"a ' directory"]:
        (src/d).mkdir()
    for d in ['dev','proc','sys','tmp']: (src/d/'omitted').write_text('not copied')
    (src/'bin/tool').write_bytes(bytes(range(256))*20000)
    (src/'bin/tool').chmod(0o751)
    os.link(src/'bin/tool', src/"a ' directory/hard link")
    os.symlink('../bin/tool', src/"a ' directory/symlink")
    (src/'empty').touch()
    for p in [src, *src.rglob('*')]: os.utime(p, ns=(1700000000123456789,1700000001987654321),follow_symlinks=False)
    expected={}
    for p in [src, *sorted(src.rglob('*'))]:
        rel='/' if p==src else '/'+p.relative_to(src).as_posix()
        if any(rel.startswith('/'+x+'/') for x in ['dev','proc','sys','tmp']): continue
        st=p.lstat()
        expected[rel]=(st.st_mode&0o7777,st.st_uid,st.st_gid,int(st.st_mtime),int(st.st_atime),int(st.st_ctime))
    out=subprocess.run([program,src,w/'copy',w/'attrs'],capture_output=True,text=True)
    assert out.returncode==0,(out.stdout,out.stderr)
    actual={}
    for line in (w/'attrs').read_text().splitlines():
        row=shlex.split(line)
        actual[row[0]]=(int(row[1],8), *map(int,row[2:]))
    assert actual==expected,(actual,expected)
    assert (w/'copy/bin/tool').read_bytes()==(src/'bin/tool').read_bytes()
    assert (w/'copy/bin/tool').stat().st_ino==(w/"copy/a ' directory/hard link").stat().st_ino
    assert os.readlink(w/"copy/a ' directory/symlink")=='../bin/tool'
    for d in ['dev','proc','sys','tmp']: assert list((w/'copy'/d).iterdir())==[]
    print('PASS I-metadata: bytes, numeric ids, modes, hard links, symlinks, quoted names, whole-second times')
    print('PASS I-exclusions: mountpoints preserved, runtime contents omitted')
    for mode in ['bytes','tree']:
        out=subprocess.run([program,src,w/('changed-'+mode),w/('attrs-'+mode),mode],capture_output=True,text=True)
        assert out.returncode==1 and 'source_changed' in out.stderr,(out.stdout,out.stderr)
    print('PASS I-source-mutation: changed bytes and changed directory entries refused')
    (src/'z-last').write_text('last source file')
    out=subprocess.run([program,src,w/'interrupted',w/'attrs-interrupted','interrupt'],capture_output=True,text=True)
    assert out.returncode==1 and 'stage: io' in out.stderr,(out.stdout,out.stderr)
    assert (w/'interrupted/bin/tool').exists()
    print('PASS I-interrupted-copy: missing late input aborts after a partial scratch copy, before target access')
    (src/'lost+found/recovered').write_text('must not be lost')
    out=subprocess.run([program,src,w/'bad-copy',w/'bad-attrs'],capture_output=True,text=True)
    assert out.returncode==1 and 'recovered_files' in out.stderr,(out.stdout,out.stderr)
    assert not (w/'bad-copy').exists()
    print('PASS I-lost-found: recovered files refused before staging')
