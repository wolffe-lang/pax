#!/usr/bin/env python3
"""image-bound.py — pax#467: rows.py's image build holds MKINITRAMFS_BOUND and says its time.

    image-bound.py SECONDS

Packs a small archive through rows.py's own initramfs(), with a shim in place of
tools/mkinitramfs that sleeps SECONDS first and then runs the real tool, as a slow host's build
would. Red (`FAIL image-bound …`, exit 1) when the build is cut at the bound, when its `image:`
line is missing, or when the archive is not the real tool's; green (`PASS image-bound …`, exit 0)
otherwise. With SECONDS past the old bound of 300 and under MKINITRAMFS_BOUND it is the row's
red-first witness: red at the old bound, green at the new. A small SECONDS checks the time line
alone, in seconds.
"""
import contextlib
import hashlib
import importlib.util
import io
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        sys.stderr.write('usage: image-bound.py SECONDS\n')
        return 2
    secs = int(sys.argv[1])
    spec = importlib.util.spec_from_file_location('rows', HERE / 'rows.py')
    rows = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rows)
    with tempfile.TemporaryDirectory(prefix='image-bound.') as d:
        d = pathlib.Path(d)
        (d / 'hello').write_bytes(b'hello\n')
        files = ['/etc/hello=%s:644' % (d / 'hello'), '/tmp/:1777']
        shim = d / 'mkinitramfs'
        shim.write_text('#!/bin/sh\nsleep %d\nexec %s "$@"\n' % (secs, ROOT / 'tools/mkinitramfs'))
        os.chmod(shim, 0o755)
        said = io.StringIO()
        with contextlib.redirect_stdout(said):
            built = rows.initramfs(d / 'shim.cpio', files, 'image-bound', mk=shim)
        out = said.getvalue()
        sys.stdout.write(''.join('  ' + l + '\n' for l in out.splitlines()))
        if not built:
            print('FAIL image-bound a build of %d s was cut at the bound of %d s' % (secs, rows.MKINITRAMFS_BOUND))
            return 1
        line = [l for l in out.splitlines() if l.startswith('image: shim.cpio, 2 arguments, ')]
        if not line:
            print('FAIL image-bound no `image:` line with its time: %r' % out[-300:])
            return 1
        subprocess.run([str(ROOT / 'tools/mkinitramfs'), str(d / 'real.cpio')] + files, check=True,
                       capture_output=True)
        if hashlib.sha256((d / 'shim.cpio').read_bytes()).digest() != hashlib.sha256((d / 'real.cpio').read_bytes()).digest():
            print('FAIL image-bound the shim built another archive than tools/mkinitramfs does')
            return 1
        print('PASS image-bound a build of %d s held under the bound of %d s: %s' % (secs, rows.MKINITRAMFS_BOUND, line[0]))
        return 0


if __name__ == '__main__':
    sys.exit(main())
