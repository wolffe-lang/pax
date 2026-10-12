#!/usr/bin/env python3
# rearrange.py SOURCE EDITS > OUT: px33's joined transcription re-arranged by an edit list (px33b).
# EDITS: lines, '#' comments allowed after the op.
#   head                 the lines up to 'end' replace every 'part' line of SOURCE (title/tempo/meter kept)
#   @ N  or  @ N-M       the bar(s) the ops below apply to
#   - P                  drop P's line(s) in the bar
#   + P WORDS...         add a line for P (after the bar's existing lines)
#   move P Q             P's line(s) become Q's
#   copy P Q             Q gets a copy of P's line(s)
#   barline WORDS        the bar's own line becomes `bar N WORDS` (meter, tempo, rit, fermata: px33b's tempo pass)
#   split P K LOW HIGH   P's events: the K lowest notes of each chord to LOW, the rest to HIGH; rests and
#                        dynamic words to both; a chord with K or fewer notes is an error
# Every op must find what it names; anything else is an error (status 2).
import sys, re
NOTE = re.compile(r"^([A-G])(##|bb|#|b)?([0-8])$")
SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACC = {None: 0, "#": 1, "##": 2, "b": -1, "bb": -2}
def midi(n):
    m = NOTE.match(n)
    if not m: die("bad note %s" % n)
    return 12 * (int(m.group(3)) + 1) + SEMI[m.group(1)] + ACC[m.group(2)]
def die(msg):
    sys.stderr.write("rearrange: %s\n" % msg); sys.exit(2)

src, edits = sys.argv[1], sys.argv[2]
head_lines, ops, cur = None, {}, None
lines = open(edits).read().split("\n")
i = 0
while i < len(lines):
    raw = lines[i]; i += 1
    s = re.sub(r"(^|\s)#.*", "", raw).strip()
    if not s: continue
    if s == "head":
        head_lines = []
        while lines[i].strip() != "end":
            head_lines.append(lines[i]); i += 1
        i += 1; continue
    if s.startswith("@"):
        r = s[1:].strip()
        a, b = (r.split("-") + [r])[:2] if "-" in r else (r, r)
        cur = list(range(int(a), int(b) + 1)); continue
    if cur is None: die("op before any @: %s" % s)
    for n in cur: ops.setdefault(n, []).append((s, raw.strip()))

def split_line(words, k):
    lo, hi = [], []
    for w in words:
        if "/" in w and (w.startswith("r/") or NOTE.match(w.split("/")[0].split(",")[0])):
            p, rest = w.split("/", 1)
            if p == "r": lo.append(w); hi.append(w); continue
            ps = p.split(",")
            if len(ps) <= k: die("split: %s has %d notes, K %d" % (w, len(ps), k))
            ps = sorted(ps, key=midi)
            lo.append(",".join(ps[:k]) + "/" + rest); hi.append(",".join(ps[k:]) + "/" + rest)
        else:
            lo.append(w); hi.append(w)
    return lo, hi

out, bar, body = [], None, []
def flush():
    global body
    if bar is None:
        out.extend(body); body = []; return
    for s, raw in ops.pop(bar, []):
        w = s.split()
        if w[0] == "-":
            n = len(body); body = [l for l in body if not (l.split() and l.split()[0] == w[1])]
            if len(body) == n: die("bar %d: - %s found nothing" % (bar, w[1]))
        elif w[0] == "+":
            c = re.search(r"(^|\s)#(.*)$", raw)
            body.append(" ".join(w[1:]) + ("   # px33b: " + c.group(2).strip() if c else ""))
        elif w[0] in ("move", "copy"):
            hit = [j for j, l in enumerate(body) if l.split() and l.split()[0] == w[1]]
            if not hit: die("bar %d: %s %s found nothing" % (bar, w[0], w[1]))
            for j in hit:
                t = body[j].split(None, 1)
                nl = w[2] + " " + (t[1] if len(t) > 1 else "")
                if w[0] == "move": body[j] = nl
                else: body.append(nl)
        elif w[0] == "split":
            p, k, low, high = w[1], int(w[2]), w[3], w[4]
            hit = [j for j, l in enumerate(body) if l.split() and l.split()[0] == p]
            if not hit: die("bar %d: split %s found nothing" % (bar, p))
            new = []
            for j, l in enumerate(body):
                if j in hit:
                    code = re.sub(r"(^|\s)#.*", "", l).split()
                    lo, hi = split_line(code[1:], k)
                    new.append(high + " " + " ".join(hi)); new.append(low + " " + " ".join(lo))
                else: new.append(l)
            body = new
        else: die("bar %d: unknown op %s" % (bar, s))
    out.extend(body); body = []

parts_done = False
for line in open(src):
    line = line.rstrip("\n")
    w = line.split()
    if w and w[0] == "part":
        if head_lines is None: body.append(line)
        elif not parts_done: body.extend(head_lines); parts_done = True
        continue
    if w and w[0] == "bar":
        flush(); bar = int(w[1])
        bl = [x for x in ops.get(bar, []) if x[0].split()[0] == "barline"]
        if bl:
            ops[bar] = [x for x in ops[bar] if x not in bl]
            c = re.search(r"(^|\s)#(.*)$", bl[-1][1])
            line = ("bar %d %s" % (bar, " ".join(bl[-1][0].split()[1:]))).rstrip() + ("   # px33b: " + c.group(2).strip() if c else "")
        out.append(line); continue
    body.append(line)
flush()
if ops: die("ops left for bars not in SOURCE: %s" % sorted(ops))
print("\n".join(out))
