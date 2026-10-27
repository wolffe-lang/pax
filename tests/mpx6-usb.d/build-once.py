#!/usr/bin/env python3
"""The USB matrix builds each kernel/tier once, but still boots every leg."""
import collections
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='pax-usb-build-once-',dir=os.environ.get('TMPDIR')) as tmp:
    tree=Path(tmp)
    for d in ('tests','tools','notes/px74'):
        (tree/d).mkdir(parents=True)
    for name in ('mpx6-usb','mpx6-usbcheck'):
        shutil.copy2(root/'tests'/name,tree/'tests'/name)
    (tree/'notes/px74/linux.rows').write_text('reference\n')
    (tree/'tools/lib.sh').write_text('PAX_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)\n'
        'die() { echo "$*" >&2; exit 2; }\n')
    helper='''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
name=Path(sys.argv[0]).name; args=sys.argv[1:]
with open(os.environ['CALLS'],'a') as f: f.write(json.dumps([name,args])+'\\n')
if name=='build-kernel':
    entry=Path(args[args.index('--src')+1]).stem
    if os.environ.get('BREAK')=='1' and '--release' in args: sys.exit(23)
    out=Path(args[-1]); out.mkdir(parents=True,exist_ok=True)
    (out/(entry+'.elf')).write_text('ELF fixture')
elif name=='mkimage':
    out=Path(args[-1]); out.parent.mkdir(parents=True,exist_ok=True); out.write_text('ISO fixture')
elif name=='mkinitramfs':
    Path(args[0]).write_text('CPIO fixture')
elif name=='qemu-run':
    out=Path(args[args.index('--serial')+1]); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join('PASS USB row%d\\n'%i for i in range(16))+'PASS USB invariants\\n')
    sys.exit(33)
'''
    for name in ('build-kernel','mkimage','mkinitramfs','fetch-limine','qemu-run','usb-session'):
        p=tree/'tools'/name; p.write_text(helper); p.chmod(0o755)
    # The C compiler is a fixture too: no executable under test is produced.
    (tree/'tools/cc').write_text('#!/bin/sh\nexit 0\n'); (tree/'tools/cc').chmod(0o755)
    calls=tree/'calls.jsonl'
    env=dict(os.environ,PAX_BUILD=str(tree/'build'),CALLS=str(calls),
             PATH=str(tree/'tools')+':'+os.environ['PATH'])
    result=subprocess.run([str(tree/'tests/mpx6-usb')],env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,(result.stdout,result.stderr)
    records=[__import__('json').loads(x) for x in calls.read_text().splitlines()]
    builds=collections.Counter((Path(a[a.index('--src')+1]).stem,'release' if '--release' in a else 'native')
                               for n,a in records if n=='build-kernel')
    expected=collections.Counter({(k,t):1 for k in ('kmain_usbcheck','kmain_console') for t in ('native','release')})
    assert builds==expected, f'kernel builds {dict(builds)}, expected {dict(expected)}'
    assert sum(n=='qemu-run' for n,a in records)==4, 'invariant boots were dropped'
    assert sum(n=='usb-session' for n,a in records)==12, 'topology/firmware/tier sessions were dropped'
    sessions=collections.Counter((Path(a[a.index('--image')+1]).parent.name,
        a[a.index('--firmware')+1],a[a.index('--topology')+1]) for n,a in records if n=='usb-session')
    assert sessions==collections.Counter({(t,f,p):1 for t in ('native','release')
        for f in ('bios','uefi') for p in ('root','hub','nested')}), 'matrix legs were duplicated or dropped'
    print('PASS USB build-once: four builds, four invariant boots, twelve distinct sessions')
    bundle=tree/'build/mpx6-usb/native'
    (bundle/'invariants/tier.txt').write_text('release\n')
    result=subprocess.run([str(tree/'tests/mpx6-usb'),'--tier','native','--firmware','uefi','--images',str(bundle)],
                          env=env,capture_output=True,text=True,timeout=30)
    assert result.returncode!=0 and 'tier mismatch' in result.stderr, result.stderr
    print('PASS USB build-once: a cached kernel from the wrong tier is refused')
    result=subprocess.run([str(tree/'tests/mpx6-usb')],env=dict(env,BREAK='1'),capture_output=True,text=True,timeout=30)
    assert result.returncode!=0, 'a failed release build passed'
    print('PASS USB build-once: build failures propagate')
