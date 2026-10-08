#!/bin/bash
# inside px13-ubuntu: strace pelt on a pty, black-box
cd /w
cc -O0 -o termios termios.c && ./termios > termios.txt
strace -f -o termios.strace -X verbose ./termios > /dev/null
for s in session eof; do
  KEYS=$s.keys python3 ptysess.py pelt-$s.tty strace -f -o pelt-$s.strace /pelt/pelt > pelt-$s.status
  KEYS=$s.keys python3 ptysess.py pelt-$s-plain.tty /pelt/pelt > pelt-$s-plain.status
  KEYS=$s.keys python3 ptysess.py dash-$s.tty dash -i > dash-$s.status 2>&1 || true
done
echo done
