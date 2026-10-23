#!/usr/bin/env python3
"""notes/px64/gnu-rows.py PAX_ROOT GNU_GREP — px64: the A2 rows that are
GNU grep 3.12's answers, held to the pinned GNU build itself, run as a
black box (scent's tools/fetch-oracle builds it from the signed tarball;
never read). Each such row's command is run by bash with the session's
`s` helper, `grep` on PATH the GNU binary, in a fresh copy of the
fixture; its output lines must be the row's lines after the typed one.
Run inside scent's oracle container (its glibc is the build's). Prints
one line a row, PASS or FAIL, then the count; exit 1 on a FAIL."""
import os
import runpy
import shutil
import subprocess
import sys
import tempfile

root, gnu = sys.argv[1], sys.argv[2]
rows = runpy.run_path(os.path.join(root, "tests/mpx5-scent.d/rows.py"))["ROWS"]
fixture = os.path.join(root, "tests/mpx5-scent.d/fixture.py")
# The rows whose lines are GNU's (the rest are scent's by ruling, the
# upstream rows, scent's own prose, or PAX's and pelt's).
GNU = {"BRE with a backreference", "-E: a class and an alternation", "-F: punctuation is literal", "-i -c", "-v -c",
       "-n -b -o", "-w", "-x", "merged context, a separator between groups", "-m with trailing context",
       "-e mixed with -f", "standard input (a pipe) and a file", "a generated file of 5,000 rows",
       "-z: NUL-ended records", "the binary-file policy", "-a", "-I", "no match: status 1",
       "a missing file: status 2", "-s: the message suppressed, status 2", "-P: the configured build's refusal",
       "-E with -F: conflicting matchers", "the C locale: a line of two bytes is two characters",
       "the C locale: -i folds ASCII only", "an unknown option: the usage, status 2"}
HELPER = ("s() { \"$@\" >$O/o 2>$O/e; echo \"status $?\"; s2; }\n"
          "s2() { tr '\\0' @ <$O/o; echo '[stderr]'; cat $O/e; }\n")
fails = n = 0
with tempfile.TemporaryDirectory() as t:
    b = os.path.join(t, "bin")
    os.mkdir(b)
    shutil.copy2(gnu, os.path.join(b, "grep"))
    for name, lines in rows:
        if name not in GNU:
            continue
        n += 1
        fx = os.path.join(t, "fx")
        shutil.rmtree(fx, ignore_errors=True)
        subprocess.run([sys.executable, "-I", fixture, fx], check=True, capture_output=True)
        o = os.path.join(t, "o")
        os.makedirs(o, exist_ok=True)
        cmd = lines[0][2:]
        env = {"PATH": b + ":/usr/bin:/bin", "HOME": "/", "O": o}
        r = subprocess.run(["bash", "-c", HELPER + "cd " + fx + "\n" + cmd], env=env, capture_output=True)
        got = r.stdout.decode("latin-1").split("\n")
        if got and got[-1] == "":
            got.pop()
        want = lines[1:]
        ok = got == want
        fails += not ok
        print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else ": GNU %r, the row %r" % (got, want)))
print("gnu-rows: %d of %d rows are GNU 3.12's answers" % (n - fails, n))
sys.exit(1 if fails else 0)
