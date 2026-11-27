#!/usr/bin/env python3
"""Exact known-red ownership witness. Raw isolation failure is never renamed PASS."""
from pathlib import Path
import hashlib
import json
import re
import runpy
import sys

MARKER=b'KLOG_OWNER_MARKER'
PAINT=b'\x1b[?1049h\x1b[?25l\x1b[0;37;40m\x1b[2J\x1b[2;7H'+MARKER+b'\x1b[2;7H'


def classify(e):
    required=('before','after','ideal','overlay','between','kernel_line')
    if any(e.get(k) is None for k in required):
        return dict(kind='FAIL',suite_exit=1,raw_exit=None,reason='missing evidence')
    raw=0 if e['after']==e['ideal'] else 1
    if not e.get('setup_ok') or e['before']!=e['ideal']:
        return dict(kind='FAIL',suite_exit=1,raw_exit=raw,reason='setup or before frame differs')
    if e['between']!=e['kernel_line']:
        return dict(kind='FAIL',suite_exit=1,raw_exit=raw,reason='changed or additional output')
    if raw==0:
        return dict(kind='XPASS',suite_exit=1,raw_exit=0,reason='isolation now holds; review pax#565 exception')
    if e['after']!=e['overlay']:
        return dict(kind='FAIL',suite_exit=1,raw_exit=1,reason='not the exact known overlay')
    return dict(kind='KNOWN-FAIL',suite_exit=0,raw_exit=1,reason='exact pax#565 overlay')


def extract(log,out):
    repo=Path(__file__).resolve().parents[2]
    ref=runpy.run_path(str(repo/'tools/screen-ref'));glyphs=ref['font_glyphs']()
    data=log.read_bytes()
    meta=re.search(rb'(?m)^KLOG-META parent=([0-9]+) child=([0-9]+) rows=([0-9]+) cols=([0-9]+)\r?$',data)
    assert meta,'missing probe metadata'
    parent,child,rows,cols=map(int,meta.groups())
    assert parent>0 and child>0 and parent!=child and (rows,cols)==(50,160)
    cmdline=re.search(rb'(?m)^KLOG-CMDLINE ([^\r\n]*)\r?$',data)
    printk=re.search(rb'(?m)^KLOG-PRINTK ([^\r\n]+)\r?$',data)
    assert cmdline and printk,'missing boot-policy evidence'
    assert b'quiet' not in cmdline[1].split(),'ownership row requires verbose kernel'
    assert int(printk[1].split()[0])>6,'INFO must reach the console'
    assert re.search(rb'(?m)^KLOG-DONE child='+str(child).encode()+rb' status=0\r?$',data),'child did not exit successfully'
    assert re.search(rb'user: klog-own pid '+str(parent).encode()+rb' exit_group 0 after [1-9][0-9]* runs\r?\n',data),'probe parent did not exit zero'
    assert b'PAX: init /bin/as ended with status 0; nothing left to run' in data
    dump=[line.split() for line in (out/'dumps.txt').read_text().splitlines()]
    assert [x[0] for x in dump]==['before','after'],'missing or extra capture'
    before_at,after_at=(int(x[1]) for x in dump)
    assert meta.end()<before_at<after_at<=len(data)
    delta=data[before_at:after_at]
    line=re.fullmatch(rb'user: klog-own pid '+str(child).encode()+rb' exit_group 0 after [1-9][0-9]* runs\r?\n',delta)
    assert line,'wrong child lifecycle signature or extra output'
    actual={}
    for name in ('before','after'):
        w,h,pixels=ref['read_ppm'](str(out/(name+'.ppm')))
        assert (w,h)==(1280,800),'wrong geometry'
        actual[name]=bytes(pixels)
    t=ref['Term'](160,50)
    for b in PAINT:t.feed(b)
    ideal=bytes(ref['render'](t,glyphs,1280,800))
    for b in delta:t.feed(b)
    overlay=bytes(ref['render'](t,glyphs,1280,800))
    # Independent before-offset replay proves the dump was of the real ready frame.
    t=ref['Term'](160,50)
    start=data.index(b'PAX: the console')
    for b in data[start:before_at]:t.feed(b)
    assert t.primary is not None and bytes(ref['render'](t,glyphs,1280,800))==actual['before']
    info=dict(parent_pid=parent,child_pid=child,geometry=[1280,800],cmdline=cmdline[1].decode(),printk=printk[1].decode(),kernel_line=delta.decode(),before_offset=before_at,after_offset=after_at,serial_sha256=hashlib.sha256(data).hexdigest())
    return dict(setup_ok=True,before=actual['before'],after=actual['after'],ideal=ideal,overlay=overlay,between=delta,kernel_line=line[0]),info


def main():
    log,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
    try:
        evidence,info=extract(log,out)
        result=classify(evidence)
    except (OSError,ValueError,AssertionError,IndexError) as error:
        info={'error':str(error)};result=classify({})
    # Keep the ideal-isolation verdict separate from the known-defect classifier.
    (out/'ownership.actual.exit').write_text(str(result['raw_exit'] if result['raw_exit'] is not None else 75)+'\n')
    (out/'ownership.result.json').write_text(json.dumps(dict(result, evidence=info),indent=2,sort_keys=True)+'\n')
    print(result['kind']+' KLOG-FULLSCREEN-565 raw_exit='+str(result['raw_exit'])+' '+result['reason'],flush=True)
    return result['suite_exit']


if __name__=='__main__':raise SystemExit(main())
