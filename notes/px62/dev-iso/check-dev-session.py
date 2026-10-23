#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path
# The bytes, not read_text(): its newline translation makes "\r\r\n" two
# lines, and a session line would be followed by an empty one.
text = Path(sys.argv[1]).read_bytes().decode("utf-8", "replace").replace("\r", "")
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
# px62: pelt 57ffef9's autocd (sh23): a directory typed as a command is
# entered, so `../home/pax` from /bin lands in /home/pax.
lines = text.splitlines()
at = [k for k, l in enumerate(lines) if l.rstrip().endswith("$ pwd")]
assert at and lines[at[-1] + 1] == "/home/pax", "the jump from /bin to ../home/pax did not land in /home/pax"
assert "cannot be run" not in text, "a directory typed as a command was refused"
# px62: the native link runs without the old mapping refusals (ld.lld's
# file-backed and MAP_SHARED mappings are served now).
assert "refused: a file-backed mapping" not in text and "refused: MAP_SHARED" not in text, "a mapping refused"
print("PASS dev ISO: pax identity, typed checked execution, object emission, native build/run, named release-tier wall, the jump to /home/pax, no mapping refused, clean exit")
