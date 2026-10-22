#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text().replace("\r", "")
records = [json.loads(line) for line in text.splitlines() if line.startswith('{"commit":')]
assert any(r.get("verdict") == "exit(0)" and
           r.get("impl") == "wolfgang" and
           r.get("stdout_inline") == "written on PAX, checked by wolf\n" for r in records), "no successful typed checked run"
assert re.search(r"^pax$", text, re.M), "whoami did not identify pax"
assert "uid=1000" in text, "id did not identify uid 1000"
for status in ("fmt=0", "object=0", "build=0", "native=0", "release=2"):
    assert re.search(r"^" + status + r"$", text, re.M), f"missing {status}"
assert re.search(r"^written on PAX, checked by wolf$", text, re.M), "no native execution output"
assert "release tier requires clang >= 15" in text
assert "PAX: init /bin/env ended with status 0" in text
print("PASS dev ISO: pax identity, typed checked execution, object emission, native build/run, named release-tier wall, clean exit")
