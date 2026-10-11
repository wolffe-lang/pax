#!/usr/bin/env python3
# expand.py FILE: expands "@double PART SRC SEMIS [*]" lines into a part line copying SRC's events in that bar
# (pitches shifted by SEMIS semitones, tremolo added with *). Used only for bars marked REDUCTION.
import sys, re
N={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
NAMES=['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B']
def mid(p):
    m=re.match(r'([A-G])(##|bb|#|b)?(\d)$',p); a={'#':1,'##':2,'b':-1,'bb':-2,None:0}[m.group(2)]
    return 12*(int(m.group(3))+1)+N[m.group(1)]+a
def name(n): return NAMES[n%12]+str(n//12-1)
def shift(tok,s,trem):
    m=re.match(r'^([^/]+)/([0-9.tx+]+)([\^\'>\-_*~]*)$',tok)
    if not m: return tok
    p,l,mk=m.groups()
    if p!='r': p=','.join(name(mid(q)+s) for q in p.split(','))
    else: return tok
    mk=mk.replace("'","")
    if trem and '*' not in mk: mk+='*'
    return p+'/'+l+mk
out=[]; bar=[]
def flush():
    lines={}
    for l in bar:
        w=l.split()
        if w and not w[0].startswith('@') and w[0] not in ('bar',): lines.setdefault(w[0],[]).append(l)
    for l in bar:
        w=l.split()
        if w and w[0]=='@double':
            part,src,s=w[1],w[2],int(w[3]); trem=len(w)>4 and w[4]=='*'
            for sl in lines.get(src,[]):
                toks=sl.split()[1:]
                out.append(part+' '+' '.join(shift(t,s,trem) for t in toks))
        else: out.append(l)
for l in open(sys.argv[1]):
    l=l.rstrip('\n')
    if l.startswith('bar '): flush(); bar=[l]
    else: bar.append(l)
flush(); print('\n'.join(out))
