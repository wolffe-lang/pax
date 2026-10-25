#!/usr/bin/env python3
"""tests/mpx5-scent.d/fixture.py DIR — px64: the text fixture the scent
session greps, generated (the same bytes every run): written into DIR,
which the image carries as /usr/share/scent and the container's root as
the same path. Each file is small enough to read on a console; big.txt
is generated rows. Prints one line per file: name, bytes, sha256."""
import hashlib
import os
import sys

FILES = {
    # BRE with a backreference, ERE classes and alternation, -F's
    # punctuation, -i/-v/-c, -n/-b/-o, -w/-x, -e with -f.
    "words.txt": b"".join(l + b"\n" for l in [
        b"abab", b"abcabc", b"cat", b"Cat", b"CAT", b"concatenate", b"dog 42",
        b"a.b*[c]", b"x.b*[c]", b"the cat sat", b"category", b"1999 was a year"]),
    # merged context and -m with context.
    "ctx.txt": b"".join(b"line %02d\n" % k for k in range(1, 21)),
    # -f's patterns, beside an -e.
    "pats.txt": b"dog\n^1999\n",
    # -z: three NUL-ended records, two with a newline inside.
    "z.dat": b"a\nb\0c\0b\nd\0",
    # the binary-file policy: a NUL before the match.
    "nul.dat": b"text line\0binary\nmatch here\n",
    # the C locale: two bytes a line (U+00E9, U+00C9 in UTF-8).
    "utf8.txt": b"\xc3\xa9\n\xc3\x89\n",
    # ruling #115: four spaces then ab.
    "w115.txt": b"    ab\n",
    # ruling #116: the double star, on `a`.
    "a116.txt": b"a\n",
    # ruling #117: a pattern file x NUL y newline; input x NUL y NUL.
    "p117.pat": b"x\0y\n",
    "i117.dat": b"x\0y\0",
    # the runtime's abort on an argument that is not UTF-8 (scent's
    # not-yet-argv-bytes rows, wolf-lang#406/#904): pelt, a wolf program,
    # refuses byte FF in ANSI-C quoting (pelt#65), so the kernel passes it from
    # this script's `#!` line (px56): scent is run with `-F<FF>`.
    "ff-arg": b"#!/bin/scent -F\xff\n",
    # a generated file: 5,000 rows, every third alpha.
    "big.txt": b"".join(b"row %04d %s\n" % (k, b"alpha" if k % 3 == 0 else b"beta") for k in range(1, 5001)),
}


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: fixture.py DIR")
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    for name, data in sorted(FILES.items()):
        with open(os.path.join(d, name), "wb") as f:
            f.write(data)
        os.chmod(os.path.join(d, name), 0o755 if data.startswith(b"#!") else 0o644)
        print("%s %d %s" % (name, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
