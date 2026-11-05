#!/usr/bin/env python3
"""tests/mpx5-lsp.d/test_rows.py — rows.py's own proof that it can fail.

    python3 -I tests/mpx5-lsp.d/test_rows.py

open-fix.good and hung.good are the Linux side's transcripts of the two
sessions (tests/mpx5-lsp's regions, the `time:` lines left out). Each must
pass rows.py whole; each mutation below, one change a transcript must not
survive, must fail at the row named beside it. Prints one line a case and
`test_rows: PASS` or `FAIL test_rows …`; exit 0 or 1.
"""
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True  # the module it loads leaves no __pycache__ in the tree

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("px99_rows", os.path.join(HERE, "rows.py"))
rows = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rows)


def good(name):
    return open(os.path.join(HERE, name + ".good"), encoding="utf-8", errors="surrogateescape").read()


def frame_edit(text, k, edit):
    """Text with the k-th `s2c` frame's JSON changed by edit(obj), its
    length kept true."""
    out, n = [], -1
    for l in text.split("\n"):
        if l.startswith("s2c "):
            n += 1
            if n == k:
                obj = json.loads(l.split(" ", 2)[2])
                edit(obj)
                b = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
                l = "s2c %d %s" % (len(b.encode("utf-8")), b)
        out.append(l)
    return "\n".join(out)


def line_edit(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


def two(o):
    o["params"]["diagnostics"].append(dict(o["params"]["diagnostics"][0]))


def code(o):
    o["params"]["diagnostics"][0]["code"] = "E0402"


def shift(o):
    o["params"]["diagnostics"][0]["range"]["start"]["character"] += 1


def related(o):
    o["params"]["diagnostics"][0]["relatedInformation"] = []


def notcleared(o):
    o["params"]["diagnostics"] = [{"code": "E0401", "message": "x", "range": {"start": {"line": 4, "character": 17}, "end": {"line": 4, "character": 24}}, "severity": 1, "source": "wolf"}]


def otheruri(o):
    o["params"]["uri"] = "file:///home/pax/lsp/other.lu"


def utf8(o):
    o["result"]["capabilities"]["positionEncoding"] = "utf-8"


def version(o):
    o["result"]["serverInfo"]["version"] = "0.2.35"


def result(o):
    o["result"] = {}


OPEN = [
    ("two diagnostics", "R2", lambda t: frame_edit(t, 1, two)),
    ("another code", "R2", lambda t: frame_edit(t, 1, code)),
    ("a range one character off", "R2", lambda t: frame_edit(t, 1, shift)),
    ("no related location", "R2", lambda t: frame_edit(t, 1, related)),
    ("another file published", "R2", lambda t: frame_edit(t, 1, otheruri)),
    ("not cleared by the fix", "R3", lambda t: frame_edit(t, 2, notcleared)),
    ("utf-8 negotiated for a client that named none", "R1", lambda t: frame_edit(t, 0, utf8)),
    ("another server version", "R1", lambda t: frame_edit(t, 0, version)),
    ("shutdown answers an object", "R4", lambda t: frame_edit(t, 3, result)),
    ("the server exits 1", "R5", lambda t: line_edit(t, "exit: status 0", "exit: status 1")),
    ("two SIGCHLDs", "R5", lambda t: line_edit(t, "sigchld: 1", "sigchld: 2")),
    ("no SIGCHLD", "R5", lambda t: line_edit(t, "sigchld: 1", "sigchld: 0")),
    ("a line on the server's standard error", "R5", lambda t: line_edit(t, "exit: status 0", "stderr: thread 'main' panicked\nexit: status 0")),
    ("a frame's length untrue", "R0", lambda t: line_edit(t, "c2s 52 ", "c2s 53 ")),
    ("a frame sent that is not the session's", "R0", lambda t: line_edit(t, '"version":2}', '"version":3}')),
    ("the execve failed", "R5", lambda t: line_edit(t, "exec: ok", "exec: failed errno 2")),
    ("a deadline in the session", "R5", lambda t: line_edit(t, "exit: status 0", "deadline: shutdown not seen within 600000 ms\nexit: status 0")),
]
HUNG = [
    ("the diagnostics came", "R2", lambda t: line_edit(t, "deadline: first-diagnostics not seen within 3000 ms",
                                                         's2c 2 {}\ncame: first-diagnostics')),
    ("the killed server exits 0", "R5", lambda t: line_edit(t, "exit: signal 9", "exit: status 0")),
    ("the write to the gone server succeeds", "R5", lambda t: line_edit(t, "lspc: write to the server failed -32\n", "")),
    ("SIGPIPE's death in place of EPIPE", "R5", lambda t: line_edit(t, "lspc: write to the server failed -32", "lspc: write to the server failed -4")),
    ("no SIGCHLD", "R5", lambda t: line_edit(t, "sigchld: 1", "sigchld: 0")),
    ("the kill refused", "R5", lambda t: line_edit(t, "SIGKILL: 0", "SIGKILL: -3")),
]


def main():
    bad = 0
    for name, cases in (("open-fix", OPEN), ("hung", HUNG)):
        g = good(name)
        got = rows.check(name, g)
        if got:
            print("FAIL test_rows %s.good: %s" % (name, got[0]))
            bad = 1
        else:
            print("  ok   %s.good passes" % name)
        for what, row, mutate in cases:
            got = rows.check(name, mutate(g))
            if any(l.startswith(row + " ") for l in got):
                print("  ok   %s, %s: %s" % (name, what, next(l for l in got if l.startswith(row + " "))[:110]))
            else:
                print("FAIL test_rows %s, %s: not at %s (%s)" % (name, what, row, got[:2]))
                bad = 1
    print("test_rows: FAIL" if bad else "test_rows: PASS")
    return bad


if __name__ == "__main__":
    sys.exit(main())
