#!/usr/bin/env python3
"""Account and payload policy, with independent expected bytes and metadata."""
from pathlib import Path
import hashlib
import os
import shlex
import shutil
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
    # px106 (R-px106-6 B3): the installer's user in group sudo (gid 27), the rest of /etc/group byte for byte.
    def groups(text, name='wolf'):
        f=w/'group.case'; f.write_text(text)
        r=subprocess.run([program,'groups',f,name],capture_output=True,text=True)
        return r.returncode,r.stdout
    def row(name, ok, what):
        if not ok: print('FAIL '+name+': '+what); sys.exit(1)
        print('PASS '+name+': '+what)
    base='root:x:0:\nwolf:x:1000:\nlobo:x:990:\n'
    rc,out=groups(base)
    row('I-sudo-group-append',(rc,out)==(0,base+'sudo:x:27:wolf\n'),'no sudo line: sudo:x:27:wolf appended, every other line as it was ('+repr(out)+')')
    rc,out=groups('root:x:0:')
    row('I-sudo-group-no-newline',(rc,out)==(0,'root:x:0:\nsudo:x:27:wolf\n'),'a file with no final newline gets one before the appended line ('+repr(out)+')')
    rc,out=groups('root:x:0:\nsudo:x:27:alice\nwolf:x:1000:\n')
    row('I-sudo-group-add',(rc,out)==(0,'root:x:0:\nsudo:x:27:alice,wolf\nwolf:x:1000:\n'),'a sudo line without them: added at the end of its members, in place ('+repr(out)+')')
    rc,out=groups('root:x:0:\nsudo:x:27:\n')
    row('I-sudo-group-add-empty',(rc,out)==(0,'root:x:0:\nsudo:x:27:wolf\n'),'an empty member list: wolf the member ('+repr(out)+')')
    t='root:x:0:\nsudo:x:27:alice,wolf,bob\nwolf:x:1000:\n'
    rc,out=groups(t)
    row('I-sudo-group-member',(rc,out)==(0,t),'already a member: the text byte for byte ('+repr(out)+')')
    rc,once=groups(base); rc2,twice=groups(once)
    row('I-sudo-group-idempotent',rc==0 and rc2==0 and twice==once,'a second pass changes nothing ('+repr(twice)+')')
    rc,out=groups('root:x:0:\nwheel:x:27:\nwolf:x:1000:\n')
    row('I-sudo-group-gid-taken',(rc,out)==(3,'refused: gid_taken\n'),'gid 27 held by a group not named sudo: refused by name, nothing merged ('+repr(out)+')')
    rc,out=groups('root:x:0:\nsudo:x:28:\nwolf:x:1000:\n')
    row('I-sudo-group-other-gid',(rc,out)==(3,'refused: sudo_gid\n'),'a sudo line at another gid: refused by name ('+repr(out)+')')
    # px112 (R-px112-9, C): the stick's burrowd listens on loopback; an install writes the LAN's line.
    shipped=(Path(__file__).resolve().parents[2]/'user/burrowd/burrowd_config').read_text()
    (s/'etc/burrowd').mkdir(parents=True,exist_ok=True)
    (s/'etc/burrowd/burrowd_config').write_text(shipped)
    want_burrowd=''.join(('ListenAddress 0.0.0.0' if l.split()[:1]==['ListenAddress'] else l)+'\n' for l in shipped.splitlines())
    row('I-burrowd-stick',[l for l in shipped.splitlines() if l.split()[:1]==['ListenAddress']]==['ListenAddress 127.0.0.1'],'the shipped configuration has one ListenAddress line, loopback')
    before={str(x):x.read_bytes() for x in s.rglob('*') if x.is_file()}
    for game in ['yes','no']:
        out=w/game
        r=subprocess.run([program,s,p,out,'alice',game],capture_output=True,text=True)
        assert r.returncode==0,(r.stdout,r.stderr)
        text=(out/'etc/passwd').read_text()
        assert text.startswith(root) and 'alice:x:1000:1000:alice:/home/alice:/bin/pelt\n' in text and '\npax:' not in text,text
        assert 'service:x:990:990:service:/srv:/bin/false\n' in text
        grp=(out/'etc/group').read_text()
        if grp!='root:x:0:\nalice:x:1000:\nsudo:x:27:alice\n':
            print('FAIL I-sudo-group-fresh: the installed /etc/group is '+repr(grp)); sys.exit(1)
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
        got=(out/'etc/burrowd/burrowd_config').read_text() if (out/'etc/burrowd/burrowd_config').exists() else ''
        row('I-burrowd-lan-'+game,got==want_burrowd and attrs.get('/etc/burrowd/burrowd_config',[])[:3]==['0644','0','0'],
            'the installed burrowd_config is the shipped one with `ListenAddress 0.0.0.0`, root\'s, 0644')
        print('PASS I-account-games-'+game+': named user, uid/gid 1000, in group sudo (27), root shell unchanged, payload omitted, complete game and engine source on yes')
    assert {str(x):x.read_bytes() for x in s.rglob('*') if x.is_file()}==before
    # px114 (pax#329): a source holding what a live system writes while it runs (the census,
    # notes/px114/census.txt): the prepared tree, its attrs and the manifest it is installed with
    # hold none of it; package state under /var/lib is carried.
    runtime=['/var/lib/dhcp/pax.lease','/etc/resolv.conf','/.sh_history','/.local/share/lope/store','/var/log/sudo.log','/Trash/files/x']
    for rel in runtime+['/var/lib/pkg/db']:
        (s/rel[1:]).parent.mkdir(parents=True,exist_ok=True); (s/rel[1:]).write_text('run time '+rel+'\n')
    out=w/'runtime'
    r=subprocess.run([program,s,p,out,'alice','no'],capture_output=True,text=True)
    row('I-runtime-install-run',r.returncode==0,'the prepare run on a source holding the census paths (exit '+str(r.returncode)+' '+r.stderr.strip()[-200:]+')')
    attrs={shlex.split(l)[0] for l in Path(str(out)+'.attrs').read_text().splitlines()}
    m=(out/'etc/pax-install/manifest').read_text().splitlines()
    listed={l.split(' ',6)[6] for l in m[6:]}
    every=runtime+['/var/lib/dhcp','/.local','/.local/share','/.local/share/lope','/Trash','/Trash/files']
    left=[x for x in every if x in attrs or x in listed or os.path.lexists(str(out)+x)]
    row('I-runtime-install',not left and '/var/lib/pkg/db' in listed and (out/'var/lib/pkg/db').exists(),
        'the lease, resolv.conf, root\'s history, lope\'s store and trash, sudo\'s log: none in the tree, its attrs or its manifest; /var/lib/pkg carried'+(' (left: '+', '.join(left)+')' if left else ''))
    for rel in ['var','.local','.sh_history','etc/resolv.conf','Trash']:
        x=s/rel
        shutil.rmtree(x) if x.is_dir() else x.unlink()
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
    # A marked live image carries demo games already; install them only
    # through the selected, verified payload, never by copying the demo home.
    demo=s/'home/pax/Games/demo'; demo.mkdir(parents=True)
    (demo/'save').write_text('source bytes must not be changed')
    r=subprocess.run([program,s,p,w/'unmarked','pax','no'],capture_output=True,text=True)
    assert r.returncode==1 and 'invalid' in r.stderr, 'unmarked source must still refuse an existing Games directory'
    (s/'etc/pax-live').write_text('pax-live-games-v1\n')
    for game in ['yes','no']:
        out=w/('live-'+game)
        r=subprocess.run([program,s,p,out,'pax',game],capture_output=True,text=True)
        assert r.returncode==0,('live source',game,r.stdout,r.stderr)
        assert not (out/'home/pax/Games/demo').exists()
        assert (out/'home/pax/Games').exists()==(game=='yes')
        if game=='yes': assert (out/'home/pax/Games/pack/pack').read_bytes()==b'game bytes'
        assert (demo/'save').read_text()=='source bytes must not be changed'
    print('PASS I-live-games: marked demo tree omitted, payload decision respected, unmarked source still refused, source untouched')
    (s/'boot/pax').write_bytes(b'corrupt')
    r=subprocess.run([program,s,p,w/'corrupt','alice','no'],capture_output=True,text=True)
    assert r.returncode==1 and 'corrupt_asset' in r.stderr
    print('PASS I-asset-digest: corrupt boot asset refused; no target needed')
