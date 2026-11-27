#!/usr/bin/env python3
"""NoGit parser controls, without starting an editor or process probe."""
from pathlib import Path
import runpy
m=runpy.run_path(str(Path(__file__).with_name('nogit.py')))
base=(b'PAX: the console\r\n'
 b'user: exec pid 3 entry 0x1234 rsp 0x1 argc 2 envc 6\r\n'
 b'user: exec pid 5 entry 0x1234 rsp 0x1 argc 3 envc 6\r\n\x1b[?1049h'
 b'git: git unavailable; repo /home/pax\r\n'
 b'user: yew pid 7 exit_group 1 after 1 runs\r\n'
 b'git: git unavailable; repo /home/pax\r\n\x1b[?1049l'
 b'user: yew pid 5 exit_group 0 after 4 runs\r\n'
 b'user: yew pid 3 exit_group 0 after 40 runs\r\n'
 b'NOGIT-ABSENT=1\r\nNOGIT-EDITOR-STATUS=0\r\nNOGIT-CONTENT-BEGIN\r\n'
 b'alpha\r\nbeta\r\ngamma\r\ndelta\r\nNOGIT-CONTENT-END\r\n'
 b'PAX: init /bin/as ended with status 0; nothing left to run\r\n')
fail=0
for name,data,want in [
 ('valid',base,True),
 ('git-present',base.replace(b'NOGIT-ABSENT=1',b'NOGIT-ABSENT=0'),False),
 ('state-missing',base.replace(b'git: git unavailable;',b'loading'),False),
 ('editing-lost',base.replace(b'gamma\r\ndelta',b'gamma\r\nwrong'),False),
 ('editor-nonzero',base.replace(b'EDITOR-STATUS=0',b'EDITOR-STATUS=1'),False),
 ('guard-nonzero',base.replace(b'pid 5 exit_group 0',b'pid 5 exit_group 1'),False),
 ('retry-spin',base.replace(b'git: git unavailable; repo /home/pax',b'git: git unavailable; repo /home/pax\r\nuser: yew pid 9 exit_group 1 after 1 runs'),False)]:
 try:m['check_common'](data);m['check_pax'](data,0x1234);actual=True
 except AssertionError:actual=False
 good=actual==want;print(('PASS ' if good else 'FAIL ')+'nogit-fixture-'+name);fail+=not good
raise SystemExit(int(bool(fail)))
