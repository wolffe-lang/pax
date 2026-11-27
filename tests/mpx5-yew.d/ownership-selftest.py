#!/usr/bin/env python3
"""Offline exact-signature controls; no helper, compiler or guest executes."""
from pathlib import Path
import runpy

judge=runpy.run_path(str(Path(__file__).with_name('ownership.py')))['classify']
base=dict(setup_ok=True,before=b'ideal',after=b'overlay',ideal=b'ideal',overlay=b'overlay',between=b'child-line',kernel_line=b'child-line')
fail=0
for name,change,kind,rc,raw in [
 ('known',{},'KNOWN-FAIL',0,1),
 ('xpass',{'after':b'ideal'},'XPASS',1,0),
 ('changed-signature',{'after':b'other'},'FAIL',1,1),
 ('missing-evidence',{'after':None},'FAIL',1,None),
 ('bad-setup',{'setup_ok':False},'FAIL',1,1),
 ('wrong-before',{'before':b'other'},'FAIL',1,1),
 ('extra-output',{'between':b'child-line plus extra'},'FAIL',1,1)]:
 result=judge(dict(base,**change));ok=(result['kind'],result['suite_exit'],result['raw_exit'])==(kind,rc,raw)
 print(('PASS ' if ok else 'FAIL ')+'ownership-fixture-'+name)
 fail+=not ok
raise SystemExit(int(bool(fail)))
