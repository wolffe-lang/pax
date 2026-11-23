#!/usr/bin/env python3
"""The Linux guest's walk of an ext4 image (ext4-walk.sh's `walk:` lines) against tools/e2tree's listing.

  ext4_walk.py e2tree IMAGE            tools/e2tree's listing of IMAGE, its debugfs run directly (a pinned image)
  ext4_walk.py compare E2TREE SERIAL   PASS/FAIL: the serial log's walk against the listing, entry by entry

ext4.py (E4-linux-reads) and the rig's dry both use these functions, so the dry runs the row's own comparison.
Each entry is `PATH TYPE MODE SIZE WHAT` in e2tree's words: WHAT a file's sha256, a link's `-> TARGET`, a
directory's `-` (the live take of 2026-11-23 compared a link's bare target against e2tree's `-> TARGET`).
"""
import contextlib
import io
from importlib.machinery import SourceFileLoader
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
TYPES = {0o100000: "reg", 0o040000: "dir", 0o120000: "lnk"}
ROOT = Path(__file__).resolve().parents[2]


def expected(text):
    """e2tree's listing as entries, lost+found left out."""
    out = []
    for line in text.splitlines():
        f = line.split("\t")
        path = f[0].lstrip("/")
        if path and path != "lost+found":
            out.append(f"{path} {f[1]} {f[2]} {f[6]} {f[11]}")
    return sorted(out)


def walk_lines(serial):
    """The guest's `walk: PATH MODEHEX SIZE WHAT` lines (its serial lines end in a carriage return)."""
    return [l.split("walk: ", 1)[1].strip() for l in serial.replace("\r", "").splitlines() if "walk: " in l and "walk-errors" not in l]


def walked(lines):
    """The walk's lines in e2tree's words."""
    out = []
    for line in lines:
        path, mode, size, what = line.split(" ", 3)
        m = int(mode, 16)
        kind = TYPES.get(m & 0o170000, "?")
        out.append(f"{path} {kind} {m & 0o7777:04o} {size} {'-> ' + what if kind == 'lnk' else what}")
    return sorted(out)


def differences(want, got):
    """(only e2tree's, only Linux's) entries."""
    a, b = set(want), set(got)
    return sorted(a - b), sorted(b - a)


def e2tree(image, work):
    """tools/e2tree's listing, its debugfs run directly (inside a pinned image, as ext3.py's PAX_E2FS_NATIVE)."""
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    wrapper = work / "e2fs-local"
    wrapper.write_text('#!/bin/sh\nshift\nexec "$@"\n')
    wrapper.chmod(0o755)
    mod = SourceFileLoader("x3_e2tree", str(ROOT / "tools/e2tree")).load_module()
    mod.E2FS = str(wrapper)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = mod.main(["e2tree", str(image)])
    return code, out.getvalue()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "e2tree":
        code, text = e2tree(sys.argv[2], Path(sys.argv[2]).parent / "e2tree-work")
        sys.stdout.write(text)
        sys.exit(code)
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        want = expected(Path(sys.argv[2]).read_text())
        got = walked(walk_lines(Path(sys.argv[3]).read_text(errors="replace")))
        only_e2tree, only_linux = differences(want, got)
        ok = bool(want) and not only_e2tree and not only_linux
        kinds = sorted({e.split()[1] for e in want})
        print(("PASS" if ok else "FAIL") + f" X3L-compare {len(got)} walked against e2tree's {len(want)} ({', '.join(kinds)})"
              + ("" if ok else f"; e2tree only {only_e2tree[:3]}, Linux only {only_linux[:3]}"))
        sys.exit(0 if ok else 1)
    print(__doc__)
    sys.exit(2)
