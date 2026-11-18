#!/usr/bin/env python3
"""Pipe and PTY UI witnesses. No signals are sent; EOF/q ends each child."""
import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time

program=sys.argv[1]
token='ERASE /dev/vdb 254:16-seq2 536870912 test ext3'
# px78b (R-P6-confirm): after the plan, one summary naming the disk by
# model, serial, size and node, the root's notice folded in, and one word.
# px162: ext3 is the default; --ext2-preview names ext2 (the witness's argument).
summary=('Erase Samsung SSD 860, serial PX71-VDB (0.5 GB, /dev/vdb), and install PAX?\n'
         'The root file system is ext3, journalled (data=ordered); pax-install --ext2-preview installs ext2 without a journal.\n'
         'Type yes to install; anything else cancels: pax-install> ')
summary2=('Erase Samsung SSD 860, serial PX71-VDB (0.5 GB, /dev/vdb), and install PAX?\n'
          'The root file system is ext2 without a journal.\n'
          'Type yes to install; anything else cancels: pax-install> ')
def ui(keys,*args):
    return subprocess.run([program,*args],input=keys,text=True,capture_output=True)
for prefix in ['', '2\n', '2\nalice\n', '2\nalice\ny\n']:
    p=ui(prefix)
    assert p.returncode==1 and 'UI result cancelled' in p.stdout,(prefix,p.stdout,p.stderr)
print('PASS I-ui-eof: EOF at every prewrite prompt cancels')
for game,expected in [('y','true'),('n','false')]:
    p=ui(f'n\np\n2\nalice\n\n{game}\nyes\n')
    assert p.returncode==0 and f'UI confirmed vdb alice {expected}' in p.stdout,(p.stdout,p.stderr)
    assert 'An explicit y or n is required.' in p.stdout
    assert 'PAX install plan v2\nformat ext3 (journal 4096 blocks' in p.stdout and 'capacity_bytes 536870912' in p.stdout,p.stdout
    assert summary in p.stdout,p.stdout
    for gone in ['confirmation ', 'Type ext2-preview', token]:
        assert gone not in p.stdout,(gone,p.stdout)
print('PASS I-ui-answers: navigation, full plan, both games answers, no blank default; the summary names the disk and yes installs')
p=ui('2\nalice\nn\nyes\n','--ext2-preview')
assert p.returncode==0 and 'UI confirmed vdb alice false ext2' in p.stdout,(p.stdout,p.stderr)
assert 'PAX install plan v1\nformat ext2-developer-preview (NO journal; not ext3)' in p.stdout and summary2 in p.stdout,p.stdout
p=ui('2\nalice\nn\nyes\n')
assert p.returncode==0 and 'UI confirmed vdb alice false ext3' in p.stdout,(p.stdout,p.stderr)
print('PASS I-ui-profile: the guided plan is ext3 by default; --ext2-preview plans ext2, its plan and notice as before')
for word in ['y', 'YES', 'Yes', 'q', '', token, 'ext2-preview', 'ext3', 'confirmation '+token]:
    p=ui(f'2\nalice\ny\n{word}\n')
    assert p.returncode==1 and 'UI result cancelled' in p.stdout and summary in p.stdout,(word,p.stdout,p.stderr)
    assert 'UI confirmed' not in p.stdout,(word,p.stdout)
print('PASS I-ui-confirmation: only yes installs; y, YES, Yes, q, empty, the old token, ext2-preview and the old confirmation line each cancel')
master,slave=pty.openpty()
fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0))
p=subprocess.Popen([program],stdin=slave,stdout=slave,stderr=slave,close_fds=True)
os.close(slave)
received=bytearray()
def wait_for(needle):
    deadline=time.monotonic()+5
    while needle not in received:
        assert time.monotonic()<deadline,bytes(received)
        if select.select([master],[],[],0.1)[0]: received.extend(os.read(master,65536))
try:
    wait_for(b'80x24')
    fcntl.ioctl(master,termios.TIOCSWINSZ,struct.pack('HHHH',40,100,0,0))
    os.write(master,b'n\n')
    wait_for(b'100x40')
    os.write(master,b'q\n')
    assert p.wait(timeout=5)==1
finally:
    os.close(master)
    p.wait(timeout=5)
print('PASS I-ui-resize: terminal dimensions refreshed between pages; q exits')
