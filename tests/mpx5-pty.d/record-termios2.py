#!/usr/bin/env python3
"""Record termios2probe's Linux answers (binary supplied, not rebuilt).

Usage: python3 -I record-termios2.py BINARY OUTDIR
The console case inherits a fresh Linux PTY on stdin, with its default
38400 baud. No host terminal settings or shell startup files are used.
"""
import os
from pathlib import Path
import subprocess
import sys

binary = str(Path(sys.argv[1]).resolve())
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for mode in ("termios2", "termios2-console"):
    master, slave = os.openpty()
    try:
        args = [binary] + (["console"] if mode.endswith("console") else [])
        result = subprocess.run(args, stdin=slave, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=30,
                                env={"HOME": str(out), "SHELL": "/bin/sh",
                                     "PATH": "/usr/bin:/bin", "LC_ALL": "C"})
        if result.returncode:
            sys.stderr.buffer.write(result.stdout + result.stderr)
            raise SystemExit(result.returncode)
        (out / (mode + ".txt")).write_bytes(result.stdout)
    finally:
        os.close(slave)
        os.close(master)
