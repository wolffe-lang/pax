#!/usr/bin/env python3
"""px87: rewrite the pre-rebase commit names in a text to the rebased ones, by map.sh's table.

    rewrite.py MAP FILE...   (in place)

An 8-hex or 40-hex word that the table names as a pre-rebase commit becomes the rebased commit's word of the
same length. Left as they are: quoted log text that printed the old name (`kernel: <sha>`, `Merge <sha>… into
<sha>…`, `HEAD is now at`), file and directory names built from a sha (`pax-stick-0eadf6b4.img`, `s-0eadf6b4`,
`w/0eadf6b4`), and fenced blocks (the INSTALL.txt copy). Prints each file's count of rewritten words.
"""
import re
import sys

table = {}
for line in open(sys.argv[1]):
    if line.startswith('#') or not line.strip():
        continue
    o8, n8, o, n = line.split()[:4]
    table[o8], table[o] = n8, n
word = re.compile(r'(?<![0-9A-Za-z_./-])([0-9a-f]{40}|[0-9a-f]{8})(?![0-9A-Za-z_-])')
keep_before = re.compile(r'(kernel: |Merge |into |HEAD is now at )$')
for path in sys.argv[2:]:
    text = open(path).read()
    out, n, fenced = [], 0, False
    for line in text.split('\n'):
        if line.startswith('```'):
            fenced = not fenced
            out.append(line)
            continue
        if fenced:
            out.append(line)
            continue
        def sub(m):
            global n
            w = m.group(1)
            if w not in table or keep_before.search(line[:m.start()]):
                return w
            n += 1
            return table[w]
        out.append(word.sub(sub, line))
    open(path, 'w').write('\n'.join(out))
    print('%s: %d words rewritten' % (path, n))
