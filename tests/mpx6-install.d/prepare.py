#!/usr/bin/env python3
"""Account and payload policy, with independent expected bytes and metadata."""
from pathlib import Path
import hashlib
import shlex
import subprocess
import sys
import tempfile
import uuid
program,work=map(Path,sys.argv[1:]);work.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=work,prefix='prepare-') as tmp:
    w=Path(tmp);s=w/'source';p=w/'payload'
    for d in ['etc','home','boot/limine','boot/EFI/BOOT','usr/share/pax-install']:(s/d).mkdir(parents=True,exist_ok=True)
    (p/'games').mkdir(parents=True)
    (s/'usr/share/pax-install/hidden-game').write_text('must not leak on no')
    root='root:x:0:0:root:/:/bin/custom-root-shell\n'
    (s/'etc/passwd').write_text(root+'pax:x:1000:1000:pax:/home/pax:/bin/pelt\nservice:x:990:990:service:/srv:/bin/false\n')
    (s/'etc/group').write_text('root:x:0:\npax:x:1000:\n')
    (s/'etc/fstab').write_text('old-root\n')
    (s/'boot/limine/limine.conf').write_text('old-config\n')
    assets=['boot/pax','boot/limine/limine-bios.sys','boot/EFI/BOOT/BOOTX64.EFI']
    for path in assets:(s/path).write_text('test asset '+path)
    h=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    (p/'boot.sha256').write_text(''.join(h(s/x)+'  /'+x+'\n' for x in assets))
    (p/'games/pack').write_bytes(b'game bytes')
    (p/'games/pack.source.tar.gz').write_bytes(b'fixture corresponding source with original licences')
    (p/'games/pack.engine.source.tar.gz').write_bytes(b'fixture engine source with its licence')
    (p/'games.txt').write_text('pack '+'a'*40+' '+h(p/'games/pack.source.tar.gz')+' pack 0755 '+'b'*40+' '+h(p/'games/pack.engine.source.tar.gz')+'\n')
    (p/'games.sha256').write_text(h(p/'games/pack')+'  pack\n')
    before={str(x):x.read_bytes() for x in s.rglob('*') if x.is_file()}
    for game in ['yes','no']:
        out=w/game
        r=subprocess.run([program,s,p,out,'alice',game],capture_output=True,text=True)
        assert r.returncode==0,(r.stdout,r.stderr)
        text=(out/'etc/passwd').read_text()
        assert text.startswith(root) and 'alice:x:1000:1000:alice:/home/alice:/bin/pelt\n' in text and '\npax:' not in text,text
        assert 'service:x:990:990:service:/srv:/bin/false\n' in text
        attrs={r[0]:r[1:] for r in map(shlex.split,Path(str(out)+'.attrs').read_text().splitlines())}
        assert attrs['/home/alice'][:3]==['0755','1000','1000']
        assert list((out/'usr/share/pax-install').iterdir())==[]
        if game=='yes':
            assert (out/'home/alice/Games/pack/pack').read_bytes()==b'game bytes'
            assert attrs['/home/alice/Games/pack/pack'][:3]==['0755','1000','1000']
            assert (out/'home/alice/Games/pack/source.tar.gz').read_bytes()==(p/'games/pack.source.tar.gz').read_bytes()
            assert (out/'home/alice/Games/pack/engine.source.tar.gz').read_bytes()==(p/'games/pack.engine.source.tar.gz').read_bytes()
            assert attrs['/home/alice/Games/pack/engine.source.tar.gz'][:3]==['0644','1000','1000']
        else:assert not (out/'home/alice/Games').exists()
        guid=str(uuid.UUID(bytes=hashlib.sha256(b'pax-gpt-part:test:1700000000:2').digest()[:16]))
        assert 'root=PARTUUID='+guid in (out/'boot/limine/limine.conf').read_text()
        assert (out/'etc/fstab').read_text().startswith('PARTUUID='+guid+' / ext2 rw')
        print('PASS I-account-games-'+game+': named user, uid/gid 1000, root shell unchanged, payload omitted, complete game and engine source on yes')
    assert {str(x):x.read_bytes() for x in s.rglob('*') if x.is_file()}==before
    # gm01: the engine's source is held to its digest like the game's
    good=(p/'games/pack.engine.source.tar.gz').read_bytes()
    (p/'games/pack.engine.source.tar.gz').write_bytes(good+b'x')
    r=subprocess.run([program,s,p,w/'engine','alice','yes'],capture_output=True,text=True)
    assert r.returncode==1 and 'corrupt_asset' in r.stderr,(r.returncode,r.stderr)
    (p/'games/pack.engine.source.tar.gz').write_bytes(good)
    (p/'games.txt').write_text('pack '+'a'*40+' '+h(p/'games/pack.source.tar.gz')+' pack 0755\n')
    r=subprocess.run([program,s,p,w/'five','alice','yes'],capture_output=True,text=True)
    assert r.returncode==1 and 'invalid' in r.stderr,(r.returncode,r.stderr)
    (p/'games.txt').write_text('pack '+'a'*40+' '+h(p/'games/pack.source.tar.gz')+' pack 0755 '+'b'*40+' '+h(p/'games/pack.engine.source.tar.gz')+'\n')
    print('PASS I-engine-source: a changed engine archive refused (corrupt_asset), a row without the engine refused (invalid)')
    (s/'boot/pax').write_bytes(b'corrupt')
    r=subprocess.run([program,s,p,w/'corrupt','alice','no'],capture_output=True,text=True)
    assert r.returncode==1 and 'corrupt_asset' in r.stderr
    print('PASS I-asset-digest: corrupt boot asset refused; no target needed')
