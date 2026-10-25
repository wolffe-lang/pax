#!/usr/bin/env python3
"""tests/mpx5-scent.d/rows.py SESSION — px64's A2: the scent session's own
witness. Each row is a run of whole lines that must follow one another in
the session's transcript (normalised), the rows in order (a row's first
line after the last line of the row before). A line is compared exactly,
but for three typed fields: `{pid}`, one or more ASCII digits (the
runtime's thread id in a panic line, R-ct02-6's one typed field); `{n}`,
a number that is the build's or the session's (a binary's size, which
the libc.a it links moves; pelt's line count); `{_}`, one or more spaces
(ls -l's padding to the widest size). Prints the rows not held, `no
<name>;` each, and nothing when every row held. Exit 0 either way (the
caller reads the output), 2 on a usage error.

What a row holds, and from where (no row is read from scent's output):
  - GNU grep 3.12's answer (`--disable-perl-regexp`, the C locale) for
    every option the contract names: what the pinned build prints, run as
    a black box on the same fixture (notes/px64/gnu-rows.sh records it),
    and what its manual says it prints;
  - rulings #115-#117's published answers (scent's README, the table):
    scent's, which differ from GNU's by decision;
  - the eight upstream-blocked rows' shapes (scent's README): the argv0
    seam (`grep:` whatever the invocation's name), and the runtime's abort
    on an argument that is not UTF-8, here passed by the kernel from a
    `#!` line (pelt refuses the byte in ANSI-C quoting before invoking scent);
  - scent's own prose where GNU's is not asked for (--help's first line,
    --version, the M2 refusal of -r), and what PAX and the image are:
    the link, the wrappers' warnings, /bin/sh, no locale, pelt's words.
"""
import re
import sys

W = "egrep: warning: egrep is obsolescent; using grep -E"
F = "fgrep: warning: fgrep is obsolescent; using grep -F"
PANIC = ["", "thread '<unnamed>' ({pid}) panicked at /rustc/8bab26f4f68e0e26f0bb7960be334d5b520ea452/library/std/src/env.rs:876:51:",
         'called `Result::unwrap()` on an `Err` value: "-F\\xFF"',
         "note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace",
         "fatal runtime error: failed to initiate panic, error 5, aborting"]


def s(cmd, status, out=(), err=()):
    """A row typed through the session's `s` helper: the command, its
    status, its standard output (NUL shown as @), `[stderr]`, its
    standard error."""
    return ["$ s " + cmd, "status %d" % status] + list(out) + ["[stderr]"] + list(err)


ROWS = [
    ("the link and the wrappers are found by PATH",
     ["$ for c in grep egrep fgrep scent sh; do command -v $c; done",
      "/bin/grep", "/bin/egrep", "/bin/fgrep", "/bin/scent", "/bin/sh"]),
    ("the image: the wrappers 0755, grep a link to scent, scent and sh programs",
     ["$ ls -l /bin/grep /bin/egrep /bin/fgrep /bin/scent /bin/sh",
      "-rwxr-xr-x 1 0 0{_}240 Jan  1  1970 /bin/egrep", "-rwxr-xr-x 1 0 0{_}240 Jan  1  1970 /bin/fgrep",
      "lrwxrwxrwx 1 0 0{_}5 Jan  1  1970 /bin/grep -> scent", "-rwxr-xr-x 1 0 0{_}{n} Jan  1  1970 /bin/scent",
      "-rwxr-xr-x 1 0 0{_}{n} Jan  1  1970 /bin/sh"]),
    ("readlink: /bin/grep is a link to scent", ["$ readlink /bin/grep", "scent"]),
    ("no LANG, no LC_ in the environment", ["$ env | grep -c -e '^LANG=' -e '^LC_'; echo \"status $?\"", "0", "status 1"]),
    ("no locale data", s("ls /usr/lib/locale", 2, err=["ls: cannot access '/usr/lib/locale': No such file or directory"])),
    ("BRE with a backreference", s("grep '\\(ab\\)\\1' words.txt", 0, ["abab"])),
    ("-E: a class and an alternation", s("grep -E '^[[:digit:]]+|dog' words.txt", 0, ["dog 42", "1999 was a year"])),
    ("-F: punctuation is literal", s("grep -F 'a.b*[c]' words.txt", 0, ["a.b*[c]"])),
    ("-i -c", s("grep -i -c cat words.txt", 0, ["6"])),
    ("-v -c", s("grep -v -c cat words.txt", 0, ["8"])),
    ("-n -b -o", s("grep -n -b -o ab words.txt", 0, ["1:0:ab", "1:2:ab", "2:5:ab", "2:8:ab"])),
    ("-w", s("grep -w cat words.txt", 0, ["cat", "the cat sat"])),
    ("-x", s("grep -x cat words.txt", 0, ["cat"])),
    ("merged context, a separator between groups",
     s("grep -n -C1 -e 'line 05' -e 'line 07' -e 'line 12' ctx.txt", 0,
       ["4-line 04", "5:line 05", "6-line 06", "7:line 07", "8-line 08", "--", "11-line 11", "12:line 12", "13-line 13"])),
    ("-m with trailing context", s("grep -n -m1 -A2 'line 0' ctx.txt", 0, ["1:line 01", "2-line 02", "3-line 03"])),
    ("-e mixed with -f", s("grep -e cat -f pats.txt words.txt", 0,
                          ["cat", "concatenate", "dog 42", "the cat sat", "category", "1999 was a year"])),
    ("standard input (a pipe) and a file", ["$ cat words.txt | s grep -c cat - ctx.txt", "status 0",
                                            "(standard input):4", "ctx.txt:0", "[stderr]"]),
    ("a generated file of 5,000 rows", s("grep -c 'alpha$' big.txt", 0, ["1666"])),
    ("-z: NUL-ended records", s("grep -z b z.dat", 0, ["a", "b@b", "d@[stderr]"])[:-1]),
    ("the binary-file policy", s("grep match nul.dat", 0, err=["grep: nul.dat: binary file matches"])),
    ("-a", s("grep -a match nul.dat", 0, ["match here"])),
    ("-I", s("grep -I match nul.dat", 1)),
    ("no match: status 1", s("grep zzz words.txt", 1)),
    ("a missing file: status 2", s("grep cat nosuch", 2, err=["grep: nosuch: No such file or directory"])),
    ("-s: the message suppressed, status 2", s("grep -s cat nosuch", 2)),
    ("-P: the configured build's refusal", s("grep -P x words.txt", 2,
                                            err=["grep: Perl matching not supported in a --disable-perl-regexp build"])),
    ("-E with -F: conflicting matchers", s("grep -E -F x words.txt", 2, err=["grep: conflicting matchers specified"])),
    ("egrep's warning even for --help", ["$ egrep --help >/dev/null", W]),
    ("fgrep's warning even for --help, then scent's own usage line",
     ["$ fgrep --help | head -n 1", F, "Usage: scent [OPTION]... PATTERNS [FILE]..."]),
    ("egrep -F: the warning, then the conflict, status 2", s("egrep -F x words.txt", 2, err=[W, "grep: conflicting matchers specified"])),
    ("fgrep -E: the warning, then the conflict, status 2", s("fgrep -E x words.txt", 2, err=[F, "grep: conflicting matchers specified"])),
    ("egrep is grep -E", s("egrep -c 'cat|dog' words.txt", 0, ["5"], [W])),
    ("fgrep is grep -F", s("fgrep -c 'a.b*' words.txt", 0, ["1"], [F])),
    ("/bin/egrep with PATH emptied of /bin: the wrapper puts its own directory first",
     ["$ PATH=/nowhere /bin/egrep -c 'cat|dog' words.txt", W, "5"]),
    ("/bin/fgrep with PATH emptied of /bin", ["$ PATH=/nowhere /bin/fgrep -c 'a.b*' words.txt", F, "1"]),
    ("/bin/grep by its path with PATH emptied of /bin", ["$ PATH=/nowhere /bin/grep -c cat words.txt", "4"]),
    ("grep by name with PATH emptied of /bin: not found, 127",
     ["$ PATH=/nowhere grep -c cat words.txt; echo \"status $?\"", "pelt: line {n}: grep: not found", "status 127"]),
    ("/bin/scent by its own name", s("/bin/scent -c cat words.txt", 0, ["4"])),
    ("the C locale: a line of two bytes is two characters", s("grep -c '^..$' utf8.txt", 0, ["2"])),
    ("the C locale: -i folds ASCII only", s("grep -i -c $'\\303\\251' utf8.txt", 0, ["1"])),
    ("ruling #115: whole-word, leftmost-longest (scent's answer; GNU's omits `2: `)",
     s("grep -E -a -o -b -w '.{1,2}' w115.txt", 0, ["0:  ", "2: ", "4:ab"])),
    ("ruling #116: ** is * (scent's answer; GNU's is status 1)", s("grep -E '(A**|.)(a)\\1**' a116.txt", 0, ["a"])),
    ("ruling #117: never cross a record (scent's answer; GNU's is x NUL y NUL, status 0)", s("grep -F -z -f p117.pat i117.dat", 1)),
    ("an unknown option: the usage, status 2", s("grep --bad", 2, err=["grep: unrecognized option '--bad'",
                                                               "Usage: grep [OPTION]... PATTERNS [FILE]...",
                                                               "Try 'grep --help' for more information."])),
    ("the argv0 seam (wolf-lang#899, #904): /bin/grep's diagnostic says grep: (GNU's says /bin/grep:)",
     s("/bin/grep --bad", 2, err=["grep: unrecognized option '--bad'", "Usage: grep [OPTION]... PATTERNS [FILE]...",
                                  "Try 'grep --help' for more information."])),
    # px65: pelt 70eec14 (sh24) says a simple command's end by a signal
    # through the command's own redirected standard error, so the line is
    # the error file's last, after the runtime's panic text.
    ("an argument that is not UTF-8, from a #! line (wolf-lang#406, #904): the runtime aborts",
     ["$ s ./ff-arg", "status 134", "[stderr]"] + PANIC + ["pelt: ended by signal 6 (ABRT)"]),
    ("pelt refuses byte FF before invoking scent (pelt#65)",
     ["$ s grep -F x $'\\377'",
      "pelt: line 50: $'\\377': a byte that is not UTF-8 cannot be carried yet (pelt#65)"]),
    ("-r is M2: refused by name", s("grep -r cat .", 2, err=["scent: not yet implemented: r (M2)"])),
    ("--version is scent's own", ["$ grep --version | head -n 1", "scent 0.1.0"]),
]


def held(lines):
    missing = []
    at = 0
    for name, want in ROWS:
        pats = [re.compile("^" + re.escape(w).replace(re.escape("{pid}"), "[0-9]+").replace(re.escape("{n}"), "[0-9]+")
                           .replace(re.escape("{_}"), " +") + "$") for w in want]
        found = -1
        for i in range(at, len(lines) - len(want) + 1):
            if all(p.match(l) for p, l in zip(pats, lines[i:i + len(want)])):
                found = i
                break
        if found < 0:
            missing.append(name)
        else:
            at = found + len(want)
    return missing


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: rows.py SESSION\n")
        sys.exit(2)
    lines = open(sys.argv[1], "rb").read().decode("utf-8", "replace").split("\n")
    for name in held(lines):
        print(" no %r;" % name, end="")
    print("", end="")


if __name__ == "__main__":
    main()
