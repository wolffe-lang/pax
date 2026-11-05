#!/usr/bin/env python3
"""tests/mpx5-lsp.d/session.py — write px99's sessions for user/elf/lspc.c.

    session.py OUTDIR

Writes OUTDIR/open-fix.lsp and OUTDIR/hung.lsp, lspc's session files
(the format is lspc.c's header), from this directory's typed.lu (the
file as the workspace holds it: one known type error) and fixed.lu (the
buffer after the edit that fixes it). Each JSON body is compact (no
blank between tokens), its keys in the order written here, ASCII only,
so the bytes on the wire are the same wherever the file is made.

  open-fix  `initialize` and `initialized`; `didOpen` of typed.lu; the
            diagnostics; a full-text `didChange` to fixed.lu, never
            saved; the diagnostics again (none); `shutdown`, `exit`, the
            server's input closed and its end awaited.
  hung      the same server made slow by the compiler's own test hook
            (WOLF_QUERY_TEST_SLOW_MS, wolf_query's TEST_SLOW_ENV: every
            query sleeps first, in 5 ms slices): after `didOpen` no
            diagnostics come within 3 s, so the client kills the server's
            process group and reaps it, as an editor gives up on a server
            that hangs.

The server is /usr/bin/wolf with argv `wolf lsp` (sagitta's row for the
language, src/mod/lsp/client.c), in the workspace's directory, with the
dev image's shell environment for it (PATH, and WOLF_STD naming the
compiler's std where the dev image keeps it).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = "/home/pax/lsp"
FILE = "typed.lu"
URI = "file://" + WS + "/" + FILE
STD = "/usr/share/wolf/compiler-std"


def body(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)


def text(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return f.read()


def head(name, slow=None):
    lines = [
        "name " + name,
        "cwd " + WS,
        "env PATH=/usr/bin:/bin",
        "env WOLF_STD=" + STD,
    ]
    if slow is not None:
        lines.append("env WOLF_QUERY_TEST_SLOW_MS=%d" % slow)
    lines += [
        "argv /usr/bin/wolf lsp",
        "deadline 600000",
        "send " + body({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "processId": None, "clientInfo": {"name": "lspc", "version": "px99"},
            "rootUri": "file://" + WS, "capabilities": {},
            "workspaceFolders": [{"uri": "file://" + WS, "name": "lsp"}]}}),
        'wait initialize "id":1,',
        "send " + body({"jsonrpc": "2.0", "method": "initialized", "params": {}}),
        "send " + body({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": URI, "languageId": "wolf", "version": 1, "text": text("typed.lu")}}}),
    ]
    return lines


def open_fix():
    return head("open-fix") + [
        'wait first-diagnostics "method":"textDocument/publishDiagnostics"',
        "send " + body({"jsonrpc": "2.0", "method": "textDocument/didChange", "params": {
            "textDocument": {"uri": URI, "version": 2}, "contentChanges": [{"text": text("fixed.lu")}]}}),
        'wait cleared-diagnostics "method":"textDocument/publishDiagnostics"',
        "send " + body({"jsonrpc": "2.0", "id": 2, "method": "shutdown"}),
        'wait shutdown "id":2,',
        "send " + body({"jsonrpc": "2.0", "method": "exit"}),
        "close",
        "end",
    ]


def hung():
    return head("hung", slow=600000) + [
        'quiet first-diagnostics 3000 "method":"textDocument/publishDiagnostics"',
        "kill",
        "end",
    ]


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: session.py OUTDIR\n")
        return 2
    os.makedirs(argv[1], exist_ok=True)
    for name, lines in (("open-fix", open_fix()), ("hung", hung())):
        with open(os.path.join(argv[1], name + ".lsp"), "w", encoding="ascii", newline="\n") as f:
            f.write("# px99: written by tests/mpx5-lsp.d/session.py\n")
            f.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
