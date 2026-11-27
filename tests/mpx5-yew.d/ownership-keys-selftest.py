#!/usr/bin/env python3
"""Replay real child-exit captures through the actual literal PS/2 matcher."""
from pathlib import Path
from types import SimpleNamespace
import contextlib,io,json,runpy,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def prompt_result(blob,line):
    module=runpy.run_path(str(ROOT/'tools/ps2-session'))
    main=module['main'];g=main.__globals__
    class Clock:
        now=0
        def time(self):self.now+=0.1;return self.now
        def sleep(self,_):pass
    class Monitor:
        def connect(self,_):pass
        def settimeout(self,_):pass
        def recv(self,_):return b'(qemu)'
    g['time']=Clock();g['socket']=SimpleNamespace(socket=lambda *_:Monitor(),AF_UNIX=1,SOCK_STREAM=1,timeout=TimeoutError)
    with tempfile.TemporaryDirectory() as d:
        p=Path(d);(p/'serial').write_bytes(blob);(p/'keys').write_text('#!ps2-session\n'+line+'\n')
        argv=sys.argv
        try:
            sys.argv=['ps2-session','--serial',str(p/'serial'),'--monitor','unused','--keys',str(p/'keys'),'--out',str(p),'--timeout','1']
            with contextlib.redirect_stderr(io.StringIO()):
                try:main();return 0
                except SystemExit as e:return e.code
        finally:sys.argv=argv


def main():
    keys=(ROOT/'user/console/klog-own.keys').read_text().splitlines()
    line=keys[keys.index('key x')+1]
    captures=json.loads((HERE/'ownership-child.capture.json').read_text())
    old='prompt 1 user: klog-own pid [0-9]+ exit_group 0 after [1-9][0-9]* runs'
    for route,text in captures.items():
        blob=text.encode('latin-1')
        assert prompt_result(blob,old)==1,'old regex-looking literal unexpectedly matched'
        assert prompt_result(blob,line)==0,'actual child exit is invisible to current handshake: '+route
        parent=blob.split(b'\x1b[?1049h')[0]
        assert prompt_result(parent,line)==1,'parent startup logs satisfied child barrier'
        before=blob[:blob.index(b'user: klog-own pid 4 exit_group')]
        assert prompt_result(before,line)==1,'marker/cursor without child satisfied barrier'
        print('PASS ownership-child-handshake-'+route)
    print('PASS ownership-child-handshake-real-literal-matcher')

if __name__=='__main__':main()
