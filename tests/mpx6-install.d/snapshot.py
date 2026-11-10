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
    # The oracle compares one pre-walk metadata set. Under relatime, an old
    # atime would advance when the earlier hard-link alias is hashed, before
    # the later alias is lstat'ed. Keep atime newer than mtime AND ctime so
    # our reads do not mutate the fixture (works on relatime and noatime).
    atime_ns=(time.time_ns()//1_000_000_000+86400)*1_000_000_000+123456789
    for p in [src, *src.rglob('*')]: os.utime(p, ns=(atime_ns,1700000001987654321),follow_symlinks=False)
    expected={}
    for p in [src, *sorted(src.rglob('*'))]:
        rel='/' if p==src else '/'+p.relative_to(src).as_posix()
        if any(rel.startswith('/'+x+'/') for x in ['dev','proc','sys','tmp']): continue
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
    # px114 (pax#329): what a live system writes while it runs is never an install's. The census
    # (notes/px114/census.txt): kernel/dhcp's lease in /var/lib/dhcp and /etc/resolv.conf; root's
    # files at the top of the tree (its home is /: pelt's history, lope's store); sudo's log.
    # Beside them, the neighbours each rule must leave alone. Each row prints PASS or FAIL by name.
    rt=w/'runtime'; failed=[]
    def put(rel,text='x\n'):
        p=rt/rel.lstrip('/'); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text)
    for rel,text in [('/var/lib/dhcp/pax.lease','state bound\naddress 10.0.2.15\n'),('/etc/resolv.conf','nameserver 10.0.2.3\n'),
                     ('/.sh_history','pax-install\n'),('/.local/share/lope/store','lope-store 1\n'),('/.cache/wolf/entry','cache\n'),
                     ('/var/log/sudo.log','root : COMMAND=/bin/true\n'),
                     ('/Trash/files/old-notes','trashed at the stick\n'),('/Trash/info/old-notes.trashinfo','[Trash Info]\nPath=/old-notes\n'),
                     ('/var/lib/pkg/db','package state\n'),('/var/libx/keep','kept\n'),('/etc/resolv.conf.d/keep','kept\n'),
                     ('/home/pax/.sh_history','a home below the top\n'),('/var/log/kept','another log\n'),('/bin/tool','tool\n')]:
        put(rel,text)
    def take(name,mode=None):
        out=subprocess.run([program,rt,w/('rt-'+name),w/('rt-'+name+'.attrs')]+([mode] if mode else []),capture_output=True,text=True)
        attrs=set()
        if (w/('rt-'+name+'.attrs')).exists():
            attrs={shlex.split(l)[0] for l in (w/('rt-'+name+'.attrs')).read_text().splitlines()}
        return out,attrs,w/('rt-'+name)
    def row(name,ok,what):
        print(('PASS ' if ok else 'FAIL ')+name+': '+what,flush=True)
        if not ok: failed.append(name)
    out,attrs,copy=take('walk')
    assert out.returncode==0,(out.stdout,out.stderr)
    def gone(paths):
        return [p for p in paths if p in attrs or os.path.lexists(str(copy)+p)]
    left=gone(['/var/lib/dhcp','/var/lib/dhcp/pax.lease'])
    row('I-runtime-lease',not left,'kernel/dhcp\'s /var/lib/dhcp and its lease neither copied nor listed'+(' (copied or listed: '+', '.join(left)+')' if left else ''))
    left=gone(['/etc/resolv.conf'])
    row('I-runtime-resolv',not left,'kernel/dhcp\'s /etc/resolv.conf neither copied nor listed'+(' (copied or listed)' if left else ''))
    top=sorted({p for p in attrs if p.startswith('/.')}|{'/'+x.name for x in copy.iterdir() if x.name.startswith('.')})
    row('I-runtime-root-home',not top,'no top-level dot name (root\'s home is /: pelt\'s history, lope\'s store, a cache) copied or listed'+(' ('+', '.join(top)+')' if top else ''))
    left=gone(['/var/log/sudo.log'])
    row('I-runtime-sudo-log',not left and '/var/log' in attrs,'sudo\'s log neither copied nor listed; /var/log itself both'+(' (the log copied or listed)' if left else ''))
    # pax#331: trash keeps a user's trash in ~/Trash, and root's home is /, so root's is /Trash.
    left=gone(['/Trash','/Trash/files','/Trash/files/old-notes','/Trash/info','/Trash/info/old-notes.trashinfo'])
    row('I-runtime-root-trash',not left,'trash\'s /Trash (root\'s ~/Trash, its home /) neither copied nor listed'+(' (copied or listed: '+', '.join(left)+')' if left else ''))
    keep=['/var/lib','/var/lib/pkg','/var/lib/pkg/db','/var/libx/keep','/etc/resolv.conf.d/keep','/home/pax/.sh_history','/var/log/kept','/bin/tool']
    lost=[p for p in keep if p not in attrs or not os.path.lexists(str(copy)+p)]
    lost+=[p for p in keep if (rt/p.lstrip('/')).is_file() and p not in lost and (copy/p.lstrip('/')).read_bytes()!=(rt/p.lstrip('/')).read_bytes()]
    row('I-runtime-neighbours',not lost,'package state under /var/lib, /var/libx, /etc/resolv.conf.d, a dot name in a home and another log copied and listed'+(' (lost: '+', '.join(lost)+')' if lost else ''))
    out,attrs,copy=take('renewal','renewal')
    ok=out.returncode==0 and not gone(['/var/lib/dhcp/pax.lease','/etc/resolv.conf'])
    row('I-runtime-renewal',ok,'the lease and resolv.conf rewritten between the two walks (a renewal at T1): the copy completes'+('' if ok else ' (exit '+str(out.returncode)+': '+out.stderr.strip()[-200:]+')'))
    if failed: sys.exit(1)
