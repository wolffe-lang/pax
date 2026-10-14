#!/usr/bin/env python3
# px41: how often tools/lobo-session's free_port (trunk's: bind port 0, read, close) answers one port
# twice in K calls in a row. usage: portdup.py K ROUNDS
import socket, sys, collections
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
k, rounds = int(sys.argv[1]), int(sys.argv[2])
dup = 0; lo, hi = 65536, 0; adj = collections.Counter()
for _ in range(rounds):
    ps = [free_port() for _ in range(k)]
    lo, hi = min(lo, *ps), max(hi, *ps)
    if len(set(ps)) < k:
        dup += 1
        for i in range(k):
            for j in range(i + 1, k):
                if ps[i] == ps[j]: adj[j - i] += 1
print("k=%d rounds=%d repeats=%d (%.4f%%) ports %d-%d; distance between the equal calls: %s; uniform would be %.4f%%"
      % (k, rounds, dup, 100.0 * dup / rounds, lo, hi, dict(adj), 100.0 * (k * (k - 1) / 2) / (hi - lo + 1)))
