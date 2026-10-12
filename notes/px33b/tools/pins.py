#!/usr/bin/env python3
# pins.py FILE: the two refusals a split part meets that check.py does not see (px32's play judges; this is a lane-side
# aid): a hairpin end ('!') with no hairpin open, a hairpin left open at the end, and a tie ('~') whose next event in
# the part sounds none of its notes. Prints each with its line; 'errors N'.
import sys, re
DYN = {"ppp", "pp", "p", "mp", "mf", "f", "ff", "fff"}
ACC = {"sfz", "sf", "fz", "fp"}
openp, tie, errs, last = {}, {}, 0, {}
for ln, line in enumerate(open(sys.argv[1]), 1):
    line = re.sub(r"(^|\s)#.*", "", line).strip()
    if not line: continue
    w = line.split()
    if w[0] in ("part", "title", "tempo", "meter", "bar"): continue
    p = w[0]
    for t in w[1:]:
        if t in DYN: openp.pop(p, None); continue
        if t == "fp": openp.pop(p, None); continue
        if t in ACC: continue
        if t in ("<", ">", "cresc", "dim"): openp[p] = ln; continue
        if t == "!":
            if p not in openp: print("line %d: '!' in %s with no hairpin open" % (ln, p)); errs += 1
            openp.pop(p, None); continue
        notes, rest = t.split("/", 1)
        ns = set() if notes == "r" else set(notes.split(","))
        if p in tie:
            if not (tie[p][0] & ns): print("line %d: %s's tie from line %d meets none of its notes" % (ln, p, tie[p][1])); errs += 1
            del tie[p]
        m = re.match(r"^[0-9.tx+]+(.*)$", rest)
        if "~" in m.group(1): tie[p] = (ns, ln)
for p, ln in openp.items(): print("line %d: %s's hairpin never ends" % (ln, p)); errs += 1
for p, (ns, ln) in tie.items(): print("line %d: %s's tie never ends" % (ln, p)); errs += 1
print("errors %d" % errs)
