#!/usr/bin/env python3
"""session.py — px106: the typed password sessions' run-time data and their delays.

    session.py make KEYSDIR OUTDIR     passwords made now, the keys with them put in
    session.py delays TEMPLATE TTY TIMES SPEC

make: OUTDIR/passwords.txt gets `root PW`, `pax PW`, `bob PW`, `new PW`,
`wrong PW` and `short PW` (twelve characters of [a-z0-9] from the
operating system's random source; short three), OUTDIR/shadow-in.txt the
lines tests/mpx5-sudo feeds tools/mkauth's mkshadow (`NAME PW`, lobo `!`),
and OUTDIR/NAME.keys each KEYSDIR/NAME.keys with `@ROOT@`, `@PAX@`, `@BOB@`,
`@NEW@`, `@WRONG@` and `@SHORT@` replaced. No password is in the tree:
the templates hold only the placeholders, and these files live in the
build directory of one run.

delays: TEMPLATE is the session's key template, TTY and TIMES what
tools/linux-tty --times wrote. For every step that types @WRONG@ (or an
empty answer), the time from the step to the first read that shows a
character other than white space (the program writes the newline at once
and its failure words after its delay). SPEC is `TEXT=SECONDS,...,spread=S`:
a step gated on TEXT is a failure the program delays by a nominal SECONDS,
documented to vary by up to S of it either way (Linux-PAM's pam_fail_delay(3):
"randomly distributed (by up to 50%) about" the requested delay, so S is 0.5
for Ubuntu's programs; PAX's are their nominal every time, S 0). Its floor is
SECONDS * (1 - S) less 0.1 s of measuring. Prints one line a step and
exits 1 when a floor is not met.
"""
import secrets
import string
import sys
from pathlib import Path

ALPHA = string.ascii_lowercase + string.digits


def pw(n=12):
    return "".join(secrets.choice(ALPHA) for _ in range(n))


def make(keysdir, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    vals = {"root": pw(), "pax": pw(), "bob": pw(), "new": pw(), "wrong": pw(), "short": pw(3)}
    while len(set(vals.values())) != len(vals):
        vals = {k: pw(3 if k == "short" else 12) for k in vals}
    (out / "passwords.txt").write_text("".join("%s %s\n" % kv for kv in vals.items()))
    (out / "shadow-in.txt").write_text("root %s\npax %s\nlobo !\nbob %s\n" % (vals["root"], vals["pax"], vals["bob"]))
    for t in sorted(Path(keysdir).glob("*.keys")) + sorted(Path(keysdir).glob("*.pax-keys")):
        text = t.read_text()
        for k, v in vals.items():
            text = text.replace("@%s@" % k.upper(), v)
        assert "@" not in text.replace("@@", ""), t
        (out / t.name).write_text(text)
    print("passwords made: %d; keys: %d" % (len(vals), len(list(out.glob("*.keys")))))


def delays(template, tty, times, floors):
    steps = [l.rstrip("\n") for l in open(template)]
    buf = open(tty, "rb").read()
    marks = []
    for line in open(times):
        f = line.split()
        if len(f) == 3:
            marks.append((float(f[0]), f[1], int(f[2])))
    nominal, spread = {}, None
    for item in floors.split(","):
        if item:
            k, v = item.rsplit("=", 1)
            if k == "spread":
                spread = float(v)
            else:
                nominal[k] = float(v)
    if spread is None:
        sys.exit("session.py delays: the SPEC names no spread= (the documented variation)")
    floor = {k: v * (1 - spread) - 0.1 for k, v in nominal.items()}
    bad = 0
    for k, line in enumerate(steps, 1):
        if not line.startswith("^{") or "}" not in line:
            continue
        gate, typed = line[2:line.index("}")], line[line.index("}") + 1:]
        if typed not in ("@WRONG@", "@SHORT@", ""):
            continue
        t = [m for m in marks if m[1] == "step" and m[2] == k]
        if not t:
            continue
        t0 = t[0][0]
        seen = None
        prev = None
        for m in marks:
            if m[1] != "out":
                continue
            if m[0] <= t0:
                prev = m[2]
                continue
            start = prev if prev is not None else 0
            if buf[start:m[2]].strip():
                seen = m[0]
                break
            prev = m[2]
        if seen is None:
            continue
        d = seen - t0
        want = floor.get(gate)
        ok = want is None or d >= want
        bad += 0 if ok else 1
        print("%s step %d %r: %.2f s%s" % ("PASS" if ok else "FAIL", k, gate, d, "" if want is None else
              " (floor %.2f: %.1f s nominal, spread %.0f%%)" % (want, nominal[gate], spread * 100)))
    return 1 if bad else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["make"]:
        make(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ["delays"]:
        sys.exit(delays(*sys.argv[2:6]))
    else:
        sys.exit(__doc__)
