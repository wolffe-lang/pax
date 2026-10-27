#!/usr/bin/env python3
"""Count LLVM CFG natural-loop headers and branch instructions per function.
This measures emitted IR, not a claim about the compiler's internal timing.
"""
import csv, re, sys, fileinput
from collections import defaultdict

rows=[]
def finish(name, blocks, branches, conditional, instructions):
    if not blocks: return
    names=list(blocks); ids={n:i for i,n in enumerate(names)}
    succ=[[ids[n] for n in blocks[b] if n in ids] for b in names]
    seen=set(); post=[]
    stack=[(0,False)]
    while stack:
        u,done=stack.pop()
        if done: post.append(u); continue
        if u in seen: continue
        seen.add(u); stack.append((u,True))
        for v in succ[u]:
            if v not in seen: stack.append((v,False))
    order=post[::-1]; mask=sum(1<<u for u in seen)
    pred=defaultdict(list)
    for u in seen:
        for v in succ[u]: pred[v].append(u)
    dom={u:mask for u in seen}; dom[0]=1
    changed=True
    while changed:
        changed=False
        for u in order:
            if u==0: continue
            d=mask
            for p in pred[u]: d &= dom[p]
            d |= 1<<u
            if d!=dom[u]: dom[u]=d; changed=True
    headers={v for u in seen for v in succ[u] if dom[u] & (1<<v)}
    backedges=sum(bool(dom[u] & (1<<v)) for u in seen for v in succ[u])
    rows.append(dict(function=re.sub(r'\$[0-9a-f]+$','',name),blocks=len(blocks),
                     loops=len(headers),backedges=backedges,branches=branches,
                     conditional=conditional,instructions=instructions,
                     proxy=len(headers)*conditional*conditional))

name=None; block=None
for line in fileinput.input(sys.argv[1:]):
    if line.startswith('define '):
        name=re.search(r'@"([^"]+)"',line).group(1)
        blocks={}; branches=conditional=instructions=0; block=None
    elif name is not None:
        if line.rstrip()=='}':
            finish(name,blocks,branches,conditional,instructions); name=None
        else:
            m=re.match(r'^([A-Za-z0-9_.]+):',line)
            if m:
                block=m.group(1); blocks[block]=[]
            elif block is not None:
                s=line.strip()
                if s and not s.startswith(';'): instructions+=1
                blocks[block] += re.findall(r'label %([A-Za-z0-9_.]+)',line)
                if s.startswith('br ') or s.startswith('switch '): branches+=1
                if s.startswith('br i1 ') or s.startswith('switch '): conditional+=1
rows.sort(key=lambda x:x['proxy'],reverse=True)
w=csv.DictWriter(sys.stdout,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
