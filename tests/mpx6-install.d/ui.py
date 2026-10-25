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
token='ERASE /dev/vdb 254:16-seq2 536870912 test'
for prefix in ['', '2\n', '2\nalice\n', '2\nalice\ny\n', '2\nalice\ny\next2-preview\n']:
    p=subprocess.run([program],input=prefix,text=True,capture_output=True)
    assert p.returncode==1 and 'UI result cancelled' in p.stdout,(prefix,p.stdout,p.stderr)
print('PASS I-ui-eof: EOF at every prewrite prompt cancels')
for game,expected in [('y','true'),('n','false')]:
    p=subprocess.run([program],input=f'n\np\n2\nalice\n\n{game}\next2-preview\n{token}\n',text=True,capture_output=True)
    assert p.returncode==0 and f'UI confirmed vdb alice {expected}' in p.stdout,(p.stdout,p.stderr)
    assert 'An explicit y or n is required.' in p.stdout
    assert 'NO journal' in p.stdout and 'capacity_bytes 536870912' in p.stdout
print('PASS I-ui-answers: navigation, full plan, both games answers and no blank default')
p=subprocess.run([program],input='2\nalice\ny\next2-preview\nyes\n',text=True,capture_output=True)
assert p.returncode==1 and 'UI result cancelled' in p.stdout
print('PASS I-ui-confirmation: yes is not the exact target token')
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
