#!/usr/bin/env python3
"""Real absent-Git state, saved-file and normal-exit witnesses."""
from pathlib import Path
import json,re,runpy,struct,sys


def check_common(data):
    text=data.replace(b'\r',b'')
    absent=re.search(rb'(?m)^NOGIT-ABSENT=([0-9]+)$',text)
    assert absent and int(absent[1]) in (1,127),'Git was not proven absent'
    assert data.count(b'git: git unavailable;')>=2,'NoGit did not settle before and after editing'
    assert re.search(rb'(?m)^NOGIT-EDITOR-STATUS=0$',text),'editor did not exit zero'
    content=re.search(rb'(?ms)^NOGIT-CONTENT-BEGIN\n(.*?)^NOGIT-CONTENT-END$',text)
    assert content and b'alpha\nbeta\ngamma\ndelta\n' in content[1],'saved editing result differs'


def check_pax(data,entry):
    alt=data.index(b'\x1b[?1049h');prefix=data[:alt]
    execs=[]
    for m in re.finditer(rb'user: exec pid ([0-9]+) [^\r\n]*entry (0x[0-9a-f]+) [^\r\n]*argc ([0-9]+) ',prefix):
        if int(m[2],16)==entry:execs.append((int(m[1]),int(m[3])))
    assert len(execs)==2 and execs[0][1]==2 and execs[1][1]==3,'editor/guard exec identities absent'
    editor,guard=execs[0][0],execs[1][0]
    exits={}
    for m in re.finditer(rb'user: yew pid ([0-9]+) exit_group ([0-9]+) after [0-9]+ runs',data):
        exits.setdefault(int(m[1]),[]).append(int(m[2]))
    assert exits.get(editor)==[0] and exits.get(guard)==[0],'editor/guard exit status differs'
    failed=[(p,c) for p,codes in exits.items() if p not in (editor,guard) for c in codes if c!=0]
    assert len(failed)<=1 and all(c==1 for _,c in failed),'unexpected/repeated failed helper'
    assert b'PAX: init /bin/as ended with status 0; nothing left to run' in data
    return dict(editor_pid=editor,guard_pid=guard,editor_exit=0,guard_exit=0,failed_probe_exits=failed)


def main():
    route=sys.argv[1];log,images,out=map(Path,sys.argv[2:]);data=log.read_bytes()
    try:
        check_common(data);detail={'route':route,'NoGit':'before and after editing','saved_file':'alpha,beta,gamma,delta','editor_exit':0}
        assert not (images/'session/bin/git').exists() and not (images/'session/usr/bin/git').exists()
        if route=='pax':
            elf=(images/'yew/yew').read_bytes();assert elf[:6]==b'\x7fELF\x02\x01'
            detail.update(check_pax(data,struct.unpack_from('<Q',elf,24)[0]))
            ref=runpy.run_path(str(Path(__file__).resolve().parents[2]/'tools/screen-ref'))
            dumps=[x.split() for x in (out/'dumps.txt').read_text().splitlines()]
            assert [x[0] for x in dumps]==['state-before','state-after']
            for name,n in dumps:
                w,h,pixels=ref['read_ppm'](str(out/(name+'.ppm')));assert (w,h)==(1280,800)
                t=ref['Term'](160,50)
                for b in data[data.index(b'PAX: the console'):int(n)]:t.feed(b)
                assert bytes(ref['render'](t,ref['font_glyphs'](),w,h))==pixels
                footer='\n'.join(''.join(chr(c[0]) for c in row) for row in t.cells[-3:])
                assert 'git: git unavailable;' in footer,'NoGit state absent from actual footer'
        else:
            assert route=='linux'
            assert log.with_name(log.name+'.rc').read_text().strip()=='0','Linux shell did not complete'
        (out/'nogit.result.json').write_text(json.dumps(detail,indent=2,sort_keys=True)+'\n')
        print('PASS NOGIT-'+route+' '+json.dumps(detail,sort_keys=True),flush=True)
        return 0
    except (OSError,ValueError,AssertionError,IndexError) as error:
        print('FAIL NOGIT-'+route+' '+str(error),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
