#!/usr/bin/env python3
"""tests/mpx5-trash.d/rows.py SESSION HOME — tb03's A2: the trash session's
own witness. Each row is a run of whole lines that must follow one another
in the session's transcript (normalised), the rows in order (a row's first
line after the last line of the row before), as tests/mpx5-scent.d/rows.py
holds scent's. HOME is the session's (`/` for root's, `/home/pax` for the
user's); its trash is HOME/Trash, and its work directory `/tmp/w` and the
user id. Prints the rows not held, ` no <name>;` each, and nothing when
every row held. Exit 0 either way (the caller reads the output), 2 on a
usage error.

What a row holds, and from where (no row is read from the commands' output
on either side): trash's README and its oracle rows at trash `c027df8` (the
status 74 and the message for a missing operand, `-f`'s silence, the
listing's `DATE TIME PATH`, the restore's `   N DATE TIME PATH` and its
prompt, trash-empty's question and its `y`), and what the session typed.
"""
import re
import sys


def s(cmd, status, out=(), err=()):
    """A row typed through the session's `s` helper: the command, its
    status, its standard output, `[stderr]`, its standard error."""
    return ["$ s " + cmd, "status %d" % status] + list(out) + ["[stderr]"] + list(err)


def rows(home):
    uid = "0" if home == "/" else "1000"
    w = "/tmp/w" + uid
    trash = "/Trash" if home == "/" else home + "/Trash"
    return [
        ("the five commands are found by PATH",
         ["$ for c in trash trash-list trash-restore trash-rm trash-empty; do command -v $c; done",
          "/bin/trash", "/bin/trash-list", "/bin/trash-restore", "/bin/trash-rm", "/bin/trash-empty"]),
        ("trash --version", ["$ trash --version", "trash (wolffe-lang trash) 0.1.0-dev"]),
        ("a file trashed", s("trash a.txt", 0)),
        ("the listing names it", ["$ l", "status 0", w + "/a.txt", "[stderr]"]),
        ("a tree and two files trashed", s("trash d b.log c.log", 0)),
        ("nothing is left where they were", ["$ f *", "*"]),
        ("the trash holds the four, under their own names", ["$ f $HOME/Trash/files/*", "a.txt", "b.log", "c.log", "d"]),
        ("a missing operand refused by name, status 74",
         s("trash nosuch", 74, err=["trash: cannot trash non existent 'nosuch'"])),
        ("-f says nothing of it", s("trash -f nosuch", 0)),
        ("the tree restored by its path: offered as 0, then put back",
         ["status 0", "0 " + w + "/d", "[stderr]"]),
        ("the tree is back", ["$ f *", "d"]),
        ("with its file's bytes", ["$ while read -r x; do echo \"$x\"; done <d/e/f", "two"]),
        ("a pattern removed for good", s("trash-rm '*.log'", 0)),
        ("only the file is left in the trash", ["$ l", "status 0", w + "/a.txt", "[stderr]"]),
        ("trash-empty -i asks, and takes y",
         ["status 0", "Would empty the following trash directories:", "- " + trash, "[stderr]"]),
        ("the listing is empty", ["$ l", "status 0", "[stderr]"]),
        ("files/ and info/ are empty", ["$ f $HOME/Trash/files/* $HOME/Trash/info/*", "*", "*"]),
    ]


def held(lines, home):
    missing = []
    at = 0
    for name, want in rows(home):
        found = -1
        for i in range(at, len(lines) - len(want) + 1):
            if lines[i:i + len(want)] == want:
                found = i
                break
        if found < 0:
            missing.append(name)
        else:
            at = found + len(want)
    return missing


def main():
    if len(sys.argv) != 3:
        sys.stderr.write("usage: rows.py SESSION HOME\n")
        sys.exit(2)
    lines = open(sys.argv[1], "rb").read().decode("utf-8", "replace").split("\n")
    for name in held([re.sub(r"\r$", "", line) for line in lines], sys.argv[2]):
        print(" no %r;" % name, end="")


if __name__ == "__main__":
    main()
