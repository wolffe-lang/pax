#!/usr/bin/env python3
"""tests/mpx5-bore.d/rows.py SESSION GROUP WHO — px65's A2: a boreutils
session's own witness (GROUP `files`: bu30's small file tools; `text`:
bu31's text tools; WHO `root` or `pax`). Each row is a run of whole lines
that must follow one another in the session's transcript (normalised),
the rows in order (a row's first line after the last line of the row
before). A line is compared exactly, but for typed fields: `{W}`, the
session's working directory (`/tmp/w0` for root, `/tmp/w1000` for pax)
and `{w}` its last name (`w0`, `w1000`); `{msg}`, any text (a
diagnostic's words where this witness holds only who said it); `{tty}`,
the console's name (the comparison types it: PAX's console is
/dev/ttyS0, the container's a pseudo-terminal); and a line `{...}`, any
lines, as few as the next line of the row allows. A row may instead be a
function of the command's block (its lines up to the next prompt) for a
property (a topological order, a permutation). Prints the rows not held,
`no <name>;` each, and nothing when every row held. Exit 0 either way
(the caller reads the output), 2 on a usage error.

What a row holds, and from where (no row is read from boreutils' output):
  - what POSIX.1-2024 and the man pages say each utility prints: comm's
    three columns, join's fields, -a, -v, -e and -o, tsort's order,
    shuf's permutations and repeats, realpath's resolution, tty's status,
    mkfifo's, link's and unlink's effects (stat's link counts and file
    types), truncate's size arithmetic, mktemp's template and modes;
  - RFC 4648's encodings, computed here by Python's base64 module from
    the fixture's own bytes (fixture.py), never typed in;
  - GNU coreutils' diagnostics' shape, `UTIL: ` and the reason, where the
    words are boreutils' (its refusals by name) or the C library's.
"""
import base64
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fixture import FILES  # noqa: E402


def s(cmd, status, out=(), err=()):
    """A row typed through the session's `s` helper: the command, its
    status, its standard output, `[stderr]`, its standard error."""
    return ["$ s " + cmd, "status %d" % status] + list(out) + ["[stderr]"] + list(err)


def usage(util, first):
    return [first, "Try '%s --help' for more information." % util]


def wrap(text, width):
    return [text[k:k + width] for k in range(0, len(text), width)] or [""]


B64_BYTES = wrap(base64.b64encode(FILES["bytes.dat"]).decode(), 76)
B64_HELLO = base64.b64encode(FILES["hello.txt"]).decode()
B64_B64 = wrap(base64.b64encode(FILES["b64.txt"]).decode(), 16)
B32_HELLO = base64.b32encode(FILES["hello.txt"]).decode()
HELLO_WORLD = base64.b64decode(FILES["b64.txt"].replace(b"\n", b"")).decode().rstrip("\n")
assert HELLO_WORLD == base64.b32decode(FILES["b32.txt"].replace(b"\n", b"")).decode().rstrip("\n")

FILE_TOOLS = ["mkfifo", "link", "unlink", "truncate", "sync", "mktemp", "realpath", "tty"]
TEXT_TOOLS = ["base64", "base32", "comm", "join", "tsort", "shuf"]

FILES_ROWS = [
    ("the eight tools are found by PATH",
     ["$ for c in mkfifo link unlink truncate; do command -v $c; done"] + ["/bin/" + c for c in FILE_TOOLS[:4]]
     + ["$ for c in sync mktemp realpath tty; do command -v $c; done"] + ["/bin/" + c for c in FILE_TOOLS[4:]]),
    ("mkfifo", s("mkfifo f1", 0)),
    ("mkfifo -m", s("mkfifo -m 600 f2", 0)),
    ("two FIFOs, their modes under umask 022 and -m 600",
     s("stat -c '%A %F %n' f1 f2", 0, ["prw-r--r-- fifo f1", "prw------- fifo f2"])),
    ("mkfifo of a taken name", s("mkfifo f1", 1, err=["mkfifo: cannot create fifo 'f1': File exists"])),
    ("mkfifo under a missing directory",
     s("mkfifo nodir/f3", 1, err=["mkfifo: cannot create fifo 'nodir/f3': No such file or directory"])),
    ("mkfifo -Z: refused by name", ["$ s mkfifo -Z f4", "{msg}", "[stderr]", "mkfifo: {msg}"]),
    ("link", s("link a b", 0)),
    ("link: two names, one file of 6 bytes", s("stat -c '%h %s %n' a b", 0, ["2 6 a", "2 6 b"])),
    ("link to a taken name", s("link a b", 1, err=["link: cannot create link 'b' to 'a': File exists"])),
    ("link of a missing file",
     s("link nosuch c", 1, err=["link: cannot create link 'c' to 'nosuch': No such file or directory"])),
    ("link with one operand", s("link a", 1, err=usage("link", "link: missing operand after 'a'"))),
    ("unlink", s("unlink b", 0)),
    ("unlink: one name left", s("stat -c '%h %n' a", 0, ["1 a"])),
    ("unlink of a missing name", s("unlink b", 1, err=["unlink: cannot unlink 'b': No such file or directory"])),
    ("unlink of a directory: Linux's EISDIR", s("unlink d", 1, err=["unlink: cannot unlink 'd': Is a directory"])),
    ("unlink with two operands", s("unlink a b", 1, err=usage("unlink", "unlink: extra operand 'b'"))),
    ("truncate -s 10", s("truncate -s 10 a", 0)),
    ("the size", s("stat -c '%s %n' a", 0, ["10 a"])),
    ("truncate -s +5", s("truncate -s +5 a", 0) + s("stat -c %s a", 0, ["15"])),
    ("truncate -s -3", s("truncate -s -3 a", 0) + s("stat -c %s a", 0, ["12"])),
    ("truncate -s %8: up to a multiple", s("truncate -s %8 a", 0) + s("stat -c %s a", 0, ["16"])),
    ("truncate -s /5: down to a multiple", s("truncate -s /5 a", 0) + s("stat -c %s a", 0, ["15"])),
    ("truncate -s 1K makes a file of 1024 bytes", s("truncate -s 1K k1", 0) + s("stat -c '%s %n' k1", 0, ["1024 k1"])),
    ("truncate -c makes nothing", s("truncate -c -s 4 nonew", 0) + ["$ s stat -c %s nonew", "status 1", "[stderr]", "stat: {msg}"]),
    ("truncate -r, and -r with a relative -s",
     s("truncate -r k1 r1", 0) + s("truncate -r k1 -s +1 r2", 0)
     + s("stat -c '%s %n' r1 r2", 0, ["1024 r1", "1025 r2"])),
    ("truncate -s 0", s("truncate -s 0 a", 0) + s("stat -c %s a", 0, ["0"])),
    ("truncate of a FIFO: refused by name", ["$ s truncate -s 4 f1", "{msg}", "[stderr]", "truncate: {msg}"]),
    ("truncate -o: refused by name", ["$ s truncate -o -s 1 a", "{msg}", "[stderr]", "truncate: {msg}"]),
    # px65: Q is a suffix since GNU 9.1 (quetta: 1Q is 2^100), so the row
    # is the overflow's, the reason the C library's strerror(EOVERFLOW).
    ("a size past 2^63 (1Q, 2^100)",
     s("truncate -s 1Q a", 1, err=["truncate: Invalid number: '1Q': Value too large for defined data type"])),
    ("no size and no reference",
     s("truncate a", 1, err=usage("truncate", "truncate: you must specify either '--size' or '--reference'"))),
    ("truncate of a directory", s("truncate -s 4 d", 1, err=["truncate: cannot open 'd' for writing: Is a directory"])),
    ("sync of a file", s("sync s1", 0)),
    ("sync -d of a file", s("sync -d s1", 0)),
    ("sync --data of a file and a directory", s("sync --data s1 d", 0)),
    ("sync of a missing file", s("sync nosuch", 1, err=["sync: error opening 'nosuch': No such file or directory"])),
    ("bare sync: refused by name (no sync(2) in wolf: wolf-lang#906)",
     ["$ s sync", "status 1", "[stderr]", "sync: {msg}"]),
    ("sync -f: refused by name (no syncfs(2) in wolf: wolf-lang#906)",
     ["$ s sync -f s1", "status 1", "[stderr]", "sync: {msg}"]),
    ("mktemp: a file /tmp/tmp.XXXXXXXXXX, mode 0600, empty",
     ["{...}", "status 0", "shape /tmp/tmp.XXXXXXXXXX"] + s("stat -c '%A %s %F' $t", 0, ["-rw------- 0 regular empty file"])),
    ("mktemp -d: a directory, mode 0700",
     ["{...}", "status 0", "shape /tmp/tmp.XXXXXXXXXX"] + s("stat -c '%A %F' $t", 0, ["drwx------ directory"])),
    ("mktemp -p DIR TEMPLATE", ["{...}", "status 0", "shape W/x.XXXXXX"]),
    ("mktemp --suffix", ["{...}", "status 0", "shape W/tmp.XXXXXXXXXX.txt"]),
    ("mktemp -u: a name, nothing made",
     ["{...}", "status 0", "shape W/tmp.XXXXXXXXXX", "$ stat -c %n $t >/dev/null 2>&1; echo \"stat status $?\"", "stat status 1"]),
    ("two names, distinct", ["{...}", "distinct"]),
    ("too few X's", s("mktemp abc", 1, err=["mktemp: too few X's in template 'abc'"])),
    ("mktemp under a missing directory",
     s("mktemp -p nodir", 1, err=["mktemp: failed to create file via template 'nodir/tmp.XXXXXXXXXX': No such file or directory"])),
    ("mktemp -q: the same failure, quiet", s("mktemp -q -p nodir", 1)),
    ("realpath .", s("realpath .", 0, ["{W}"])),
    ("realpath through ..", s("realpath ./d/../a", 0, ["{W}/a"])),
    ("realpath follows links, a chain too", s("realpath la lla", 0, ["{W}/a", "{W}/a"])),
    ("realpath -s keeps the link", s("realpath -s la", 0, ["{W}/la"])),
    ("realpath of a dangling link: its target, the last part missing", s("realpath dangle", 0, ["{W}/nowhere"])),
    ("realpath -e of a dangling link", s("realpath -e dangle", 1, err=["realpath: dangle: No such file or directory"])),
    ("realpath -m", s("realpath -m nowhere/x/../y", 0, ["{W}/nowhere/y"])),
    ("realpath --relative-to", s("realpath --relative-to=/tmp a", 0, ["{w}/a"])),
    ("realpath --relative-base", s("realpath --relative-base=/tmp a /etc", 0, ["{w}/a", "/etc"])),
    ("realpath -L: .. before the link", s("realpath -L le/..", 0, ["{W}"])),
    ("realpath -P: .. after the link", s("realpath -P le/..", 0, ["/"])),
    ("realpath -q", s("realpath -q -e nosuch", 1)),
    ("tty: the console's name", s("tty", 0, ["{tty}"])),
    ("tty -s", s("tty -s", 0)),
    ("tty --silent", s("tty --silent", 0)),
    ("tty of a file", ["$ tty < a; echo \"status $?\"", "not a tty", "status 1"]),
    ("tty -s of a file", ["$ tty -s < a; echo \"status $?\"", "status 1"]),
    ("tty with an operand: status 2", s("tty extra", 2, err=usage("tty", "tty: extra operand 'extra'"))),
    ("the tree removed, FIFOs and links in it", ["$ cd /; rm -r $W; echo \"status $?\"", "status 0"]),
]


def tsort_order(block):
    """tsort ts.txt: every name once, every pair's first before its second."""
    pairs = [l.split() for l in FILES["ts.txt"].decode().splitlines()]
    names = {n for p in pairs for n in p}
    if len(block) < 2 or block[0] != "status 0" or block[-1] != "[stderr]":
        return False
    out = block[1:-1]
    if sorted(out) != sorted(names) or len(out) != len(names):
        return False
    pos = {n: k for k, n in enumerate(out)}
    return all(pos[a] < pos[b] for a, b in pairs)


def tsort_loop(block):
    """tsort tcyc.txt: status 1, the loop named on standard error."""
    if not block or block[0] != "status 1" or "[stderr]" not in block:
        return False
    k = block.index("[stderr]")
    err = block[k + 1:]
    return bool(err) and err[0] == "tsort: tcyc.txt: input contains a loop:" \
        and sorted(err[1:3]) == ["tsort: a", "tsort: b"] and sorted(block[1:k]) == ["a", "b"]


TEXT_ROWS = [
    ("the six tools are found by PATH",
     ["$ for c in base64 base32 comm join tsort shuf; do command -v $c; done"] + ["/bin/" + c for c in TEXT_TOOLS]),
    ("base64 of a line (RFC 4648)", s("base64 hello.txt", 0, [B64_HELLO])),
    ("base64 of every byte, wrapped at 76", s("base64 bytes.dat", 0, B64_BYTES)),
    ("base64 -w 16", s("base64 -w 16 b64.txt", 0, B64_B64)),
    ("base64 with two operands", s("base64 hello.txt b64.txt", 1, err=usage("base64", "base64: extra operand 'b64.txt'"))),
    ("base64 -w 0: no newline", ["$ s base64 -w 0 hello.txt", "status 0", B64_HELLO + "[stderr]"]),
    ("base64 round trip of every byte", ["$ base64 bytes.dat | base64 -d | wc -c", "256"]),
    ("base64 -d of a wrapped text", s("base64 -d b64.txt", 0, [HELLO_WORLD])),
    ("base64 -d of a bad text", ["$ s base64 -d bad.txt", "status 1", "{...}", "[stderr]", "base64: invalid input"]),
    ("base64 -d -i: the garbage ignored", s("base64 -d -i bad.txt", 0, ["hello"])),
    ("base64 -d of a pipe", ["$ echo aGVsbG8K | s base64 -d", "status 0", "hello", "[stderr]"]),
    ("base64 of a missing file", s("base64 nosuch", 1, err=["base64: nosuch: No such file or directory"])),
    ("base64 -w of a word", s("base64 -w x hello.txt", 1, err=["base64: invalid wrap size: 'x'"])),
    ("base32 of a line (RFC 4648)", s("base32 hello.txt", 0, [B32_HELLO])),
    ("base32 -d of a wrapped text", s("base32 -d b32.txt", 0, [HELLO_WORLD])),
    ("base32 round trip of every byte", ["$ base32 bytes.dat | base32 -d | wc -c", "256"]),
    ("base32 -d of a bad text", ["$ s base32 -d bad.txt", "status 1", "{...}", "[stderr]", "base32: invalid input"]),
    ("comm: three columns", s("comm c1.txt c2.txt", 0, ["apple", "\t\tbanana", "\t\tcherry", "date", "\tegg", "\tfig"])),
    ("comm -12", s("comm -12 c1.txt c2.txt", 0, ["banana", "cherry"])),
    ("comm -3", s("comm -3 c1.txt c2.txt", 0, ["apple", "date", "\tegg", "\tfig"])),
    ("comm --total", s("comm --total c1.txt c2.txt", 0,
                       ["apple", "\t\tbanana", "\t\tcherry", "date", "\tegg", "\tfig", "2\t2\t2\ttotal"])),
    ("comm --output-delimiter", s("comm --output-delimiter=: c1.txt c2.txt", 0,
                                  ["apple", "::banana", "::cherry", "date", ":egg", ":fig"])),
    ("comm of an unsorted file", ["$ s comm cu.txt c2.txt", "status 1", "{...}", "[stderr]",
                                  "comm: file 1 is not in sorted order", "{...}"]),
    ("comm --nocheck-order", s("comm --nocheck-order cu.txt c2.txt", 0, ["\tbanana", "\t\tcherry", "apple", "\tegg", "\tfig"])),
    ("join", s("join j1.txt j2.txt", 0, ["1 alice paris", "3 carol rome"])),
    ("join -a 1", s("join -a 1 j1.txt j2.txt", 0, ["1 alice paris", "2 bob", "3 carol rome"])),
    ("join -v 2", s("join -v 2 j1.txt j2.txt", 0, ["4 oslo"])),
    ("join -a -a -e -o", s("join -a 1 -a 2 -e NONE -o 0,1.2,2.2 j1.txt j2.txt", 0,
                           ["1 alice paris", "2 bob NONE", "3 carol rome", "4 NONE oslo"])),
    ("join -t -1 -2", s("join -t : -1 2 -2 1 p1.txt p2.txt", 0, ["1:alice:red", "3:carol:blue"])),
    ("join -i", s("join -i u1.txt u2.txt", 0, ["A one uno", "b two dos"])),
    ("join --header", s("join --header h1.txt h2.txt", 0, ["id name city", "1 alice paris", "2 bob rome"])),
    ("join of a missing file", s("join j1.txt nosuch", 1, err=["join: nosuch: No such file or directory"])),
    ("tsort: a topological order", ("tsort ts.txt", tsort_order)),
    ("tsort: a loop", ("tsort tcyc.txt", tsort_loop)),
    ("tsort: an odd number of tokens",
     s("tsort todd.txt", 1, err=["tsort: todd.txt: input contains an odd number of tokens"])),
    ("shuf of one number", s("shuf -i 1-1", 0, ["1"])),
    ("shuf -i: a permutation of the range", ["$ shuf -i 1-10 | sort -n"] + [str(k) for k in range(1, 11)]),
    ("shuf -e: a permutation of the words", ["$ shuf -e a b c d | sort", "a", "b", "c", "d"]),
    ("shuf of a file: a permutation of its lines", ["$ shuf lines.txt | sort -n"] + [str(k) for k in range(1, 11)]),
    ("shuf -n 3", ["$ shuf -n 3 -i 1-100 | wc -l", "3"]),
    ("shuf -r: repeats", s("shuf -r -n 4 -e x", 0, ["x", "x", "x", "x"])),
    ("shuf -n 0", s("shuf -n 0 -i 1-3", 0)),
    ("shuf of a reversed range", s("shuf -i 5-1", 1, err=["shuf: invalid input range: '5-1'"])),
    ("shuf --random-source: refused by name",
     ["$ s shuf --random-source=lines.txt -i 1-3", "{msg}", "[stderr]", "shuf: {msg}"]),
    ("shuf -i with -e", s("shuf -i 1-3 -e a", 1, err=usage("shuf", "shuf: cannot combine -e and -i options"))),
    ("the scratch removed", ["$ cd /; rm -r $O; echo \"status $?\"", "status 0"]),
]


def line_re(pat, w):
    parts = re.split(r"(\{msg\}|\{W\}|\{w\})", pat)
    out = []
    for p in parts:
        if p == "{msg}":
            out.append(".*")
        elif p == "{W}":
            out.append(re.escape("/tmp/" + w))
        elif p == "{w}":
            out.append(re.escape(w))
        else:
            out.append(re.escape(p))
    return re.compile("".join(out) + r"\Z")


def match_at(lines, i, row, w):
    """Match row's lines from lines[i]; return the index after, or None."""
    if not row:
        return i
    head = row[0]
    if head == "{...}":
        rest = row[1:]
        if not rest:
            j = i
            while j < len(lines) and not lines[j].startswith("$ "):
                j += 1
            return j
        for j in range(i, len(lines) + 1):
            r = match_at(lines, j, rest, w)
            if r is not None:
                return r
        return None
    if i < len(lines) and line_re(head, w).match(lines[i]):
        return match_at(lines, i + 1, row[1:], w)
    return None


def main():
    if len(sys.argv) != 4 or sys.argv[2] not in ("files", "text") or sys.argv[3] not in ("root", "pax"):
        print("usage: rows.py SESSION files|text root|pax", file=sys.stderr)
        return 2
    lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().split("\n")
    w = "w0" if sys.argv[3] == "root" else "w1000"
    rows = FILES_ROWS if sys.argv[2] == "files" else TEXT_ROWS
    pos = 0
    missing = []
    for name, row in rows:
        if isinstance(row, tuple):
            cmd, pred = row
            k = next((j for j in range(pos, len(lines)) if lines[j] == "$ s " + cmd), None)
            if k is None:
                missing.append(name)
                continue
            e = k + 1
            while e < len(lines) and not lines[e].startswith("$ "):
                e += 1
            if pred(lines[k + 1:e]):
                pos = e
            else:
                missing.append(name)
            continue
        found = None
        for j in range(pos, len(lines)):
            r = match_at(lines, j, row, w)
            if r is not None:
                found = r
                break
        if found is None:
            missing.append(name)
        else:
            pos = found
    for m in missing:
        print("no %s;" % m)
    return 0


def count(group):
    return len(FILES_ROWS if group == "files" else TEXT_ROWS)


if __name__ == "__main__":
    sys.exit(main())
