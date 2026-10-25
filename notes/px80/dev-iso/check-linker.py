#!/usr/bin/env python3
"""px80: the dev session names the ISO's own linker on PAX: `ld.lld --version`
answers LLD 18.1.8 (no distro prefix: the bundle's static build). That the
link front end drives it is check-dev-session.py's `build=0` and `native=0`."""
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_bytes().decode("utf-8", "replace").replace("\r", "")
lines = text.splitlines()
v = [l for l in lines if re.match(r"^LLD \d+\.\d+\.\d+", l)]
assert v, "ld.lld --version printed no LLD line"
assert v[0].startswith("LLD 18.1.8 "), f"the ISO's linker is {v[0]!r}, not LLD 18.1.8"
assert not any("Ubuntu" in l for l in v), "a distro lld answered"
print(f"PASS linker on PAX: {v[0]}")
