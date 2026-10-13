import sys,re,datetime as d,collections as c
log=sys.argv[1]
jobs=c.defaultdict(list)
for l in open(log,errors="replace"):
    p=l.rstrip("\n").split("\t",2)
    if len(p)<3: continue
    m=re.match(r"\ufeff?(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+)Z (.*)",p[2])
    if not m: continue
    t=d.datetime.fromisoformat(m.group(1)[:26])
    jobs[p[0]].append((t,m.group(2)))
elf=c.defaultdict(list)   # (tier, elfsha) -> [(job,name,secs)]
byname=c.defaultdict(set) # (tier,name-ish kmain?) 
tot=c.Counter(); per={}
for j,ls in jobs.items():
    start=None; prev=None; nat=rel=0.0; nb=0; inter=0; seenboot=False
    for t,x in ls:
        if x.startswith("##[group]Run tests/"+j): start=t; prev=t
        m=re.match(r"\S+: built (native|release)(?: (\S+?))?(?: in \d+ s)?: elf ([0-9a-f]{64})",x)
        mt=re.match(r"tour: built (native|release) with wolf",x)
        if mt and prev:
            s=(t-prev).total_seconds(); prev=t; nb+=2
            if mt.group(1)=="native": nat+=s
            else: rel+=s
            elf[(mt.group(1),"tour-two-kernels-digest-not-printed-"+mt.group(1))].append((j,"kmain_tour+kmain_tour_text",s))
            continue
        if m and prev:
            s=(t-prev).total_seconds(); prev=t; nb+=1
            if seenboot: inter+=1
            seenboot=False
            if m.group(1)=="native": nat+=s
            else: rel+=s
            elf[(m.group(1),m.group(3))].append((j,m.group(2) or "kmain_console",s))
        elif prev and re.search(r" (bios|uefi)\b",x) and "PASS" in x: seenboot=True
    if nb: per[j]=(nb,nat/60,rel/60,inter)
print("%-16s %6s %8s %8s %s"%("suite","builds","native","release","boots-between-builds"))
N=R=0
for j,(nb,n,r,i) in per.items():
    print("%-16s %6d %8.1f %8.1f %s"%(j,nb,n,r,i or "")); N+=n;R+=r
print("%-16s %6d %8.1f %8.1f"%("total",sum(v[0] for v in per.values()),N,R))
print()
for tier in ("native","release"):
    ks=[k for k in elf if k[0]==tier]
    builds=sum(len(elf[k]) for k in ks)
    dupsecs=sum(sum(sorted(s for _,_,s in elf[k])[:-1]) if False else sum(s for _,_,s in elf[k])-max(s for _,_,s in elf[k]) for k in ks)
    allsecs=sum(s for k in ks for _,_,s in elf[k])
    print("%s: %d builds, %d distinct ELF digests, %.1f min in all, %.1f min in builds whose ELF another build also produced"%(tier,builds,len(ks),allsecs/60,dupsecs/60))
print()
print("ELF digests built more than once:")
for k,v in sorted(elf.items(),key=lambda kv:-len(kv[1])):
    if len(v)>1: print(" ",k[0],k[1][:12],len(v),"x:"," ".join("%s/%s(%ds)"%(j,n,s) for j,n,s in v))
# same source name, different digest across jobs?
names=c.defaultdict(set)
src=c.defaultdict(set)
for (tier,sha),v in elf.items():
    for j,n,s in v: names[(tier,n)].add(sha)
print()
print("names with more than one digest:",[ (k,len(v)) for k,v in names.items() if len(v)>1])
