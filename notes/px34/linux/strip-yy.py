#!/usr/bin/env python3
"""px34: drop strace -yy's annotations (`fd<what>`, which may nest:
`0</dev/null<char 1:3>>`, and hold
`->`: `11<UNIX-STREAM:[1->2,"logs/control.sock"]>`) so shapes.py reads the lines as plain strace."""
import sys

def strip(line):
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == '<' and i > 0 and line[i - 1].isdigit():
            depth, q, j = 0, False, i
            while j < n:
                d = line[j]
                if q:
                    if d == '\\':
                        j += 1
                    elif d == '"':
                        q = False
                elif d == '"':
                    q = True
                elif d == '<':
                    depth += 1
                elif d == '>' and line[j - 1] != '-':  # `->` joins two ends
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            i = j + 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)

for path in sys.argv[1:]:
    with open(path, errors='replace') as f:
        for line in f:
            sys.stdout.write(strip(line))
