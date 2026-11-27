#!/usr/bin/env python3
"""Offline exact-signature controls; no helper, compiler or guest executes."""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

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
# Exercise the complete receipt/pixel parser and CLI for all four outcomes.
root=Path(__file__).resolve().parents[2]
module=runpy.run_path(str(Path(__file__).with_name('ownership.py')))
ref=runpy.run_path(str(root/'tools/screen-ref'));glyphs=ref['font_glyphs']()
for kind,want,raw in [('KNOWN-FAIL',0,'1'),('XPASS',1,'0'),('changed',1,'1'),('missing',1,'75')]:
 with tempfile.TemporaryDirectory(prefix='ownership-fixture-') as d:
  out=Path(d)
  data=(b'PAX: the console\r\nKLOG-CMDLINE \r\nKLOG-PRINTK 8 4 1 7\r\n'
        b'KLOG-META parent=11 child=12 rows=50 cols=160\r\n'+module['PAINT'])
  before=len(data);line=b'user: klog-own pid 12 exit_group 0 after 2 runs\r\n';data+=line;after=len(data)
  data+=(b'\x1b[?1049l\r\nKLOG-DONE child=12 status=0\r\n'
         b'user: klog-own pid 11 exit_group 0 after 5 runs\r\n'
         b'PAX: init /bin/as ended with status 0; nothing left to run\r\n')
  (out/'serial.log').write_bytes(data);(out/'dumps.txt').write_text(f'before {before}\nafter {after}\n')
  t=ref['Term'](160,50)
  for b in module['PAINT']:t.feed(b)
  ideal=bytes(ref['render'](t,glyphs,1280,800))
  for b in line:t.feed(b)
  overlay=bytes(ref['render'](t,glyphs,1280,800))
  (out/'before.ppm').write_bytes(b'P6\n1280 800\n255\n'+ideal)
  pixels=ideal if kind=='XPASS' else overlay
  if kind=='changed':pixels=pixels[:-1]+bytes([pixels[-1]^255])
  if kind!='missing':(out/'after.ppm').write_bytes(b'P6\n1280 800\n255\n'+pixels)
  p=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('ownership.py')),str(out/'serial.log'),str(out)],capture_output=True,text=True)
  label=kind if kind in ('KNOWN-FAIL','XPASS') else 'FAIL'
  ok=p.returncode==want and p.stdout.startswith(label+' KLOG-FULLSCREEN-565 ') and (out/'ownership.actual.exit').read_text().strip()==raw
  print(('PASS ' if ok else 'FAIL ')+'ownership-pipeline-'+kind.lower());fail+=not ok
raise SystemExit(int(bool(fail)))
