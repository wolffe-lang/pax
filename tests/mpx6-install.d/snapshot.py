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
import time

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
    # px112: a running system's state under /var/run (sudo's timestamps, burrowd's pid) and
    # burrowd's host key and log stay out of the walk; /var/run itself and the configuration stay in.
    RUNTIME={'/etc/burrowd/ssh_host_ed25519_key','/etc/burrowd/ssh_host_ed25519_key.pub','/var/log/burrowd.log'}
    for d in ['var/run/sudo/ts','var/log','etc/burrowd']: (src/d).mkdir(parents=True)
    (src/'var/run/sudo/ts/0').write_text('a timestamp record')
    (src/'var/run/burrowd.pid').write_text('123\n')
    (src/'var/log/burrowd.log').write_text('a log line\n')
    (src/'etc/burrowd/burrowd_config').write_text('ListenAddress 127.0.0.1\n')
    (src/'etc/burrowd/ssh_host_ed25519_key').write_text('not a key');(src/'etc/burrowd/ssh_host_ed25519_key').chmod(0o600)
    (src/'etc/burrowd/ssh_host_ed25519_key.pub').write_text('not a key either')
    # The oracle compares one pre-walk metadata set. Under relatime, an old
    # atime would advance when the earlier hard-link alias is hashed, before
    # the later alias is lstat'ed. Keep atime newer than mtime AND ctime so
    # our reads do not mutate the fixture (works on relatime and noatime).
    atime_ns=(time.time_ns()//1_000_000_000+86400)*1_000_000_000+123456789
    for p in [src, *src.rglob('*')]: os.utime(p, ns=(atime_ns,1700000001987654321),follow_symlinks=False)
    expected={}
    for p in [src, *sorted(src.rglob('*'))]:
        rel='/' if p==src else '/'+p.relative_to(src).as_posix()
        if any(rel.startswith('/'+x+'/') for x in ['dev','proc','sys','tmp','var/run']) or rel in RUNTIME: continue
        st=p.lstat()
        expected[rel]=(st.st_mode&0o7777,st.st_uid,st.st_gid,st.st_mtime_ns//1_000_000_000,st.st_atime_ns//1_000_000_000,st.st_ctime_ns//1_000_000_000)
    out=subprocess.run([program,src,w/'copy',w/'attrs'],capture_output=True,text=True)
    assert out.returncode==0,(out.stdout,out.stderr)
    actual={}
    for line in (w/'attrs').read_text().splitlines():
        row=shlex.split(line)
        actual[row[0]]=(int(row[1],8), *map(int,row[2:]))
    assert (src/'bin/tool').stat().st_atime_ns==atime_ns,'fixture reads changed the shared inode atime'
    assert actual==expected,(actual,expected)
    assert (w/'copy/bin/tool').read_bytes()==(src/'bin/tool').read_bytes()
    assert (w/'copy/bin/tool').stat().st_ino==(w/"copy/a ' directory/hard link").stat().st_ino
    assert os.readlink(w/"copy/a ' directory/symlink")=='../bin/tool'
    for d in ['dev','proc','sys','tmp']: assert list((w/'copy'/d).iterdir())==[]
    print('PASS I-metadata: bytes, numeric ids, modes, hard links, symlinks, quoted names, whole-second times')
    print('PASS I-exclusions: mountpoints preserved, runtime contents omitted')
    assert (w/'copy/var/run').is_dir() and list((w/'copy/var/run').iterdir())==[],list((w/'copy/var/run').iterdir())
    assert (w/'copy/etc/burrowd/burrowd_config').exists() and (w/'copy/var/log').is_dir()
    assert not any((w/'copy'/r.lstrip('/')).exists() for r in RUNTIME)
    print('PASS I-runtime-state: /var/run kept and empty (/var/run/sudo/ts and burrowd.pid left out); burrowd\'s host key, its .pub and its log left out, its configuration copied')
    for mode in ['bytes','tree','runtime-dir']:
        out=subprocess.run([program,src,w/('changed-'+mode),w/('attrs-'+mode),mode],capture_output=True,text=True)
        assert out.returncode==1 and 'source_changed' in out.stderr,(out.stdout,out.stderr)
    print('PASS I-source-mutation: changed bytes, tree entries and excluded runtime-directory metadata refused')
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
