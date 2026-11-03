#!/usr/bin/env python3
"""The Nth den session of a transcript (tests/mpx5-den, px90).

Usage: region.py TRANSCRIPT N

TRANSCRIPT is a serial log or a Linux-side terminal transcript already
normalised by tools/lib.sh's serial_norm. A session is the lines from the
one that is exactly `den-session-begin` (the echo's output, not the typed
command, which follows a prompt) to the one that is exactly
`den-session-end`, both kept. The kernel's own `user: ...` lines are left
out, and a `user: ...` tail cut from a line the program was writing
(tests/mpx5-scent's run_part rule), so a session typed on PAX and the same
keys typed on Linux are the same bytes when the programs agree. Prints the
session (1-based N) and exits 0, or names what is missing and exits 1.
"""
import sys

def lines(text):
    # The kernel's line inside a program's: the program's head is joined
    # to the line after the kernel's (run_part's `printf "%s"`).
    carry = ''
    for line in text.split('\n'):
        i = line.find('user: ')
        if i == 0:
            continue
        if i > 0:
            carry += line[:i]
            continue
        yield carry + line
        carry = ''

def sessions(text):
    out, cur = [], None
    for line in lines(text):
        if line == 'den-session-begin':
            cur = [line]
            continue
        if cur is not None:
            cur.append(line)
            if line == 'den-session-end':
                out.append(cur)
                cur = None
    return out

def main():
    path, n = sys.argv[1], int(sys.argv[2])
    found = sessions(open(path, encoding='latin-1').read())
    if len(found) < n:
        print(f'region.py: {path}: {len(found)} complete den session(s), not {n}', file=sys.stderr)
        return 1
    sys.stdout.write('\n'.join(found[n - 1]) + '\n')
    return 0

if __name__ == '__main__':
    sys.exit(main())
