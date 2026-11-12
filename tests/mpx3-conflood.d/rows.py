#!/usr/bin/env python3
"""tests/mpx3-conflood.d/rows.py (px129, R-px129-13): peer.py's JSON held to the rows.

    rows.py RUN.json

  F1 the run reached `end` through idle, flood and after; in the idle phase every ping and every echo
     answered, the 95th percentile round trip of each at most 20 ms
  F2 while the console is flooded, of the pings and of the echoes, at least 95 % answered and the 95th
     percentile round trip at most 50 ms
Prints `PASS F…`/`FAIL F…` a row and one `stats` line a probe and phase; exit 0 when no row fails.
"""
import json
import sys

IDLE_P95 = 20.0
FLOOD_P95 = 50.0
FLOOD_ANSWERED = 0.95


def main():
    r = json.load(open(sys.argv[1]))
    p = r["probes"]
    fail = 0
    for k in sorted(p):
        print("stats " + k + ": " + ", ".join(f"{a} {b}" for a, b in p[k].items()))
    names = [x[0] for x in r["phases"]]
    want = ["idle", "flood", "after", "end"]
    ok = r["ended"] and names == want
    why = []
    for probe in ("ping", "echo"):
        st = p[f"{probe} idle"]
        if st["sent"] == 0 or st["answered"] != st["sent"]:
            ok = False
            why.append(f"{probe} idle answered {st['answered']} of {st['sent']}")
        elif st["p95"] > IDLE_P95:
            ok = False
            why.append(f"{probe} idle p95 {st['p95']} ms")
    print(f"{'PASS' if ok else 'FAIL'} F1 the run: phases {' '.join(names) or 'none'}"
          + (f"; {'; '.join(why)}" if why else f"; idle ping p95 {p['ping idle'].get('p95')} ms, echo p95 {p['echo idle'].get('p95')} ms (bound {IDLE_P95})"))
    fail |= not ok
    for probe in ("ping", "echo"):
        st = p[f"{probe} flood"]
        n, a = st["sent"], st["answered"]
        frac = a / n if n else 0.0
        p95 = st.get("p95")
        good = n > 0 and frac >= FLOOD_ANSWERED and p95 is not None and p95 <= FLOOD_P95
        print(f"{'PASS' if good else 'FAIL'} F2 {probe} during the flood: {a} of {n} answered ({frac:.0%}, at least {FLOOD_ANSWERED:.0%}), "
              f"p95 {p95} ms, median {st.get('median')} ms, max {st.get('max')} ms (bound {FLOOD_P95} ms)")
        fail |= not good
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
