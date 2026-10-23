# px62 debug only: RIP samples between the user session's `$ gi` and its menu, by symbol.
import sys, subprocess, bisect, collections
serial, samples, elf = sys.argv[1:4]
b = open(serial, "rb").read()
def nth(pat, n):
    i = -1
    for _ in range(n):
        i = b.find(pat, i + 1)
    return i
lo, hi = nth(b"$ gi", 2), nth(b"1) /bin", 2)
print("window bytes", lo, hi)
syms = []
for line in subprocess.run(["nm", "-n", elf], capture_output=True, text=True).stdout.splitlines():
    p = line.split()
    if len(p) >= 3 and p[1] in "tTwW":
        syms.append((int(p[0], 16), p[2]))
addrs = [a for a, _ in syms]
def sym(r):
    i = bisect.bisect_right(addrs, r) - 1
    return syms[i][1] if i >= 0 else "?"
c = collections.Counter(); cr3s = collections.Counter(); n = 0; t = []
for line in open(samples):
    ts, rip, cr3, rfl, sz = line.split()
    sz = int(sz)
    if lo <= sz < hi and rip != "-":
        r = int(rip, 16); n += 1; t.append(float(ts))
        c["user" if r < 0x800000000000 else sym(r)] += 1
        cr3s[cr3] += 1
print("samples", n, "seconds", (t[-1] - t[0]) if t else 0)
for k, v in c.most_common(25):
    print(v, k)
print(cr3s.most_common(5))
prev = None
for line in open(samples):
    ts, rip, cr3, rfl, sz = line.split()
    sz = int(sz)
    if lo <= sz < hi and rip != "-":
        r = int(rip, 16)
        k = ("user" if r < 0x800000000000 else sym(r)) + " " + cr3 + " if=" + str((int(rfl, 16) >> 9) & 1) + " sz=" + str(sz)
        print("%.3f %s" % (float(ts), k[:110]))
