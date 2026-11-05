#!/usr/bin/env python3
"""tests/mpx5-lsp.d/rows.py — px99's witness of one lspc transcript.

    rows.py SESSION REGION

SESSION is `open-fix` or `hung` (tests/mpx5-lsp.d/session.py); REGION a
transcript's lines from `lspc: begin` to `lspc: end` with the `time:`
lines left out (tests/mpx5-lsp's `region`). Prints one line for each row
that fails, `Rn what: why`, and exits 1; prints nothing and exits 0 when
every row holds; exits 2 on a usage error.

The rows hold what the protocol, the session and the compiler's answer to
typed.lu must give, from this directory's own files, never from another
run, so a client or a server broken alike on PAX and on Linux (which
tests/mpx5-lsp's LSP1 cannot see) is still caught:
  R0 the client's lines: the session's name at both ends with status 0,
     the server started as `/usr/bin/wolf lsp` in /home/pax/lsp and its
     execve ok, every frame sent the session's body in order, each line
     of the kinds and in the order the session gives.
  R1 initialize: the first frame read answers id 1 with serverInfo
     wolf-lsp 0.2.36 and the capabilities wolf-lsp's own recordings hold
     at the same compiler pin for a client that declares none (CAPS:
     wolf-lsp's transcripts/diagnostics/overlay-unsaved.jsonl, its second
     frame, recorded against wolf-lang 5adf3d91, user/wolf.pin's).
  R2 open-fix: the next frame publishes typed.lu's diagnostics: exactly
     one, E0401, severity 1 (an error), source `wolf`, its range the string
     literal on typed.lu's `let n` line and its one related location the
     annotation `int` on that line, both found here in typed.lu. hung: no
     diagnostics; the deadline passed at 3000 ms and the kill answered 0.
  R3 open-fix: after the didChange, the next frame publishes typed.lu with
     no diagnostics.
  R4 open-fix: the next frame answers id 2 with a null result. hung: the
     frame written after the reap answered EPIPE (-32), not a SIGPIPE.
  R5 the end: no frame but these; no line of the server's standard error;
     the server's end (status 0 after shutdown and exit; signal 9 when
     killed); exactly one SIGCHLD; nothing read from the terminal.
"""
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True  # the module it loads leaves no __pycache__ in the tree

HERE = os.path.dirname(os.path.abspath(__file__))
URI = "file:///home/pax/lsp/typed.lu"
CAPS = {
    "codeActionProvider": True,
    "completionProvider": {"triggerCharacters": ["."]},
    "definitionProvider": True,
    "documentFormattingProvider": True,
    "documentSymbolProvider": True,
    "hoverProvider": True,
    "inlayHintProvider": {"resolveProvider": False},
    "positionEncoding": "utf-16",
    "referencesProvider": True,
    "renameProvider": {"prepareProvider": True},
    "semanticTokensProvider": {
        "full": True,
        "legend": {
            "tokenModifiers": ["declaration", "readonly"],
            "tokenTypes": ["namespace", "type", "parameter", "variable", "property", "enumMember", "function", "keyword"],
        },
        "range": True,
    },
    "signatureHelpProvider": {"retriggerCharacters": [","], "triggerCharacters": ["(", ","]},
    "textDocumentSync": {"change": 1, "openClose": True, "save": {"includeText": False}},
}
SERVER = {"name": "wolf-lsp", "version": "0.2.36"}
DIAGNOSTICS = 1  # typed.lu has one error


def session_lines(name):
    spec = importlib.util.spec_from_file_location("px99_session", os.path.join(HERE, "session.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {"open-fix": mod.open_fix, "hung": mod.hung}[name]()


def literal_ranges():
    """The string literal and the annotation `int` on typed.lu's `let n`
    line, as (line, start, end) in UTF-16 units (the file is ASCII)."""
    lines = open(os.path.join(HERE, "typed.lu"), encoding="ascii").read().split("\n")
    k = next(i for i, l in enumerate(lines) if l.lstrip().startswith("let n"))
    line = lines[k]
    q0 = line.index('"')
    q1 = line.index('"', q0 + 1) + 1
    a0 = line.index("int")
    return (k, q0, q1), (k, a0, a0 + 3)


def rng(r):
    return (r["start"]["line"], r["start"]["character"], r["end"]["character"]) if r["start"]["line"] == r["end"]["line"] else None


def check(name, text):
    bad = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    # The kinds of line the session gives, in order.
    kinds, sent, read = [], [], []
    for l in lines:
        word = l.split(" ", 1)[0]
        if word in ("c2s", "s2c"):
            parts = l.split(" ", 2)
            if len(parts) != 3 or not parts[1].isdigit():
                bad.append("R0 frames: a malformed frame line: %r" % l[:120])
                continue
            body = parts[2]
            if len(body.encode("utf-8", "surrogateescape")) != int(parts[1]):
                bad.append("R0 frames: a frame of %s bytes says %s: %r" % (len(body.encode("utf-8", "surrogateescape")), parts[1], l[:120]))
            (sent if word == "c2s" else read).append(body)
            kinds.append(word)
        else:
            kinds.append(l)
    want_sent = [l[5:] for l in session_lines(name) if l.startswith("send ")]
    if sent != want_sent:
        bad.append("R0 frames: the %d frames sent are not the session's %d bodies in order" % (len(sent), len(want_sent)))
    if name == "open-fix":
        want = (["lspc: begin open-fix", "spawn: /usr/bin/wolf lsp (cwd /home/pax/lsp)", "exec: ok",
                 "c2s", "s2c", "c2s", "c2s", "s2c", "c2s", "s2c", "c2s", "s2c", "c2s",
                 "exit: status 0", "sigchld: 1", "tty: 0 bytes", "lspc: end open-fix status 0"])
    else:
        want = (["lspc: begin hung", "spawn: /usr/bin/wolf lsp (cwd /home/pax/lsp)", "exec: ok",
                 "c2s", "s2c", "c2s", "c2s",
                 "deadline: first-diagnostics not seen within 3000 ms",
                 "kill: the server's process group, SIGKILL: 0",
                 "exit: signal 9", "c2s", "lspc: write to the server failed -32",
                 "sigchld: 1", "tty: 0 bytes", "lspc: end hung status 0"])
    if kinds != want:
        extra = [k for k in kinds if k not in want]
        missing = [k for k in want if k not in kinds]
        bad.append("R5 the end: the lines are not the session's (%d lines, %d wanted; unwanted %s; missing %s)"
                   % (len(kinds), len(want), json.dumps(extra[:3]), json.dumps(missing[:3])))
    try:
        frames = [json.loads(b) for b in read]
    except ValueError as e:
        bad.append("R1 initialize: a frame read is not JSON: %s" % e)
        return bad
    # R1: the first frame read.
    if not frames:
        bad.append("R1 initialize: no frame read")
        return bad
    f = frames[0]
    if f.get("jsonrpc") != "2.0" or f.get("id") != 1 or "result" not in f:
        bad.append("R1 initialize: the first frame is not the response to id 1: %s" % json.dumps(f)[:160])
    else:
        res = f["result"]
        if res.get("serverInfo") != SERVER:
            bad.append("R1 initialize: serverInfo is %s, not %s" % (json.dumps(res.get("serverInfo")), json.dumps(SERVER)))
        if res.get("capabilities") != CAPS:
            bad.append("R1 initialize: the capabilities are not wolf-lsp's at the pin: %s" % json.dumps(res.get("capabilities"))[:200])
    if name == "hung":
        if len(frames) != 1:
            bad.append("R2 no diagnostics: %d frames read, not the response alone" % len(frames))
        return bad
    if len(frames) != 4:
        bad.append("R5 the end: %d frames read, not 4" % len(frames))
    (lit, ann) = literal_ranges()

    def published(k, row):
        if len(frames) <= k:
            bad.append("%s: no frame %d" % (row, k + 1))
            return None
        g = frames[k]
        if g.get("method") != "textDocument/publishDiagnostics" or "id" in g:
            bad.append("%s: frame %d is not a publishDiagnostics notification: %s" % (row, k + 1, json.dumps(g)[:160]))
            return None
        p = g.get("params", {})
        if p.get("uri") != URI:
            bad.append("%s: it publishes %s, not %s" % (row, p.get("uri"), URI))
        return p.get("diagnostics")
    d = published(1, "R2 diagnostics")
    if d is not None:
        if len(d) != DIAGNOSTICS:
            bad.append("R2 diagnostics: %d diagnostics, not %d" % (len(d), DIAGNOSTICS))
        if d:
            x = d[0]
            if x.get("code") != "E0401" or x.get("severity") != 1 or x.get("source") != "wolf":
                bad.append("R2 diagnostics: code %s severity %s source %s, not E0401 1 wolf" % (x.get("code"), x.get("severity"), x.get("source")))
            if rng(x.get("range", {"start": {"line": -1}, "end": {"line": -2}})) != lit:
                bad.append("R2 diagnostics: the range %s is not the literal's %s" % (json.dumps(x.get("range")), lit))
            rel = x.get("relatedInformation") or []
            if len(rel) != 1 or rel[0].get("location", {}).get("uri") != URI or rng(rel[0]["location"].get("range", {"start": {"line": -1}, "end": {"line": -2}})) != ann:
                bad.append("R2 diagnostics: the related location is not the annotation %s: %s" % (ann, json.dumps(rel)[:160]))
    d = published(2, "R3 cleared")
    if d is not None and d != []:
        bad.append("R3 cleared: %d diagnostics after the fix" % len(d))
    if len(frames) > 3:
        g = frames[3]
        if g.get("id") != 2 or "result" not in g or g["result"] is not None:
            bad.append("R4 shutdown: frame 4 is not a null result for id 2: %s" % json.dumps(g)[:160])
    else:
        bad.append("R4 shutdown: no frame 4")
    return bad


def main(argv):
    if len(argv) != 3 or argv[1] not in ("open-fix", "hung"):
        sys.stderr.write("usage: rows.py open-fix|hung REGION\n")
        return 2
    text = open(argv[2], encoding="utf-8", errors="surrogateescape").read()
    bad = check(argv[1], text)
    for b in bad:
        print(b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
