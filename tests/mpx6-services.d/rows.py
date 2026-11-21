#!/usr/bin/env python3
"""tests/mpx6-services.d/rows.py SESSION VERSION — A0: alpha at the console,
with nothing to start. Each row is a run of whole lines that must follow
one another in the session's transcript (normalised), the rows in order (a
row's first line after the last line of the row before), as
tests/mpx5-trash.d/rows.py holds trash's. VERSION is the line
tools/mkalpha read from `alpha --version` on the build host. Prints the
rows not held, ` no <name>;` each, and nothing when every row held. Exit 0
either way (the caller reads the output), 2 on a usage error.

What a row holds, and from where (no row is read from the command's output
on PAX): alpha's own goldens at the pinned commit (tests/unit/cli/:
check-empty-root's count line, client-no-manager's line and status 3), the
control socket a client asks when it names none (src/cli/cli.lu's
CONTROL, /run/alpha/control), the version line from the same binary run
on Linux, and what the session typed.
"""
import re
import sys


def s(cmd, status, out=(), err=()):
    """A row typed through the session's `s` helper: the command, its
    status, its standard output, `[stderr]`, its standard error."""
    return ["$ s " + cmd, "status %d" % status] + list(out) + ["[stderr]"] + list(err)


def rows(version):
    return [
        ("alpha is found by PATH", ["$ command -v alpha", "/bin/alpha"]),
        ("alpha --version prints the version line, status 0", s("alpha --version", 0, out=[version])),
        ("alpha check --root / counts no unit, status 0",
         s("alpha check --root /", 0, out=["alpha check: 0 units, 0 errors, 0 warnings"])),
        ("alpha status finds no manager, status 3",
         s("alpha status", 3, err=["alpha: no manager answers at /run/alpha/control (not_found)"])),
    ]


def held(lines, version):
    missing = []
    at = 0
    for name, want in rows(version):
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
        sys.stderr.write("usage: rows.py SESSION VERSION\n")
        sys.exit(2)
    lines = open(sys.argv[1], "rb").read().decode("utf-8", "replace").split("\n")
    for name in held([re.sub(r"\r$", "", line) for line in lines], sys.argv[2]):
        print(" no %r;" % name, end="")


if __name__ == "__main__":
    main()
