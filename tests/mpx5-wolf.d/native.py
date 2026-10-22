#!/usr/bin/env python3
"""Compare the M2 typed session and require real native builds and executions."""
import hashlib
import re
import sys
from pathlib import Path

def norm(text):
    text = re.sub(r"\x1b\[[0-9;?=<>]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b[()][A-Za-z0-9]", "", text)
    text = re.sub(r"\x1b[c78DEHM=>]", "", text)
    return text.replace("\r", "")

pax = norm(Path(sys.argv[1]).read_bytes().decode("utf-8"))
linux = norm(Path(sys.argv[2]).read_bytes().decode("utf-8"))
assert not re.search(r"^PANIC ", pax, re.M), "PAX kernel panic"
assert "PAX: init /bin/as ended with status 0" in pax, "native session did not end cleanly"
for line in pax.splitlines():
    if "refused:" in line:
        assert "syscall 9:" in line and ("file-backed mapping" in line or "MAP_SHARED" in line), line
unserved = {int(n) for n in re.findall(r"syscall (\d+): -ENOSYS", pax)}
assert unserved <= {25, 273, 334}, f"new unserved calls: {unserved}"
active = False
parts = []
for line in pax.splitlines():
    if line.startswith("run 1: "):
        active = True
        continue
    if not active:
        continue
    if line.startswith(("user: frames free ", "run: ", "run 2: ")):
        break
    pos = line.find("user: ")
    if pos == 0:
        continue
    if pos > 0:
        parts.append(line[:pos])
    else:
        parts.append(line + "\n")
observed = "".join(parts)
Path(sys.argv[1] + ".session").write_text(observed)
Path(sys.argv[2] + ".session").write_text(linux)
assert observed == linux, "M2 terminal bytes differ from Linux"
assert "uid=1000" in observed
for name in ("hello", "loop", "signal"):
    for phase in ("link", "native"):
        assert f"\n{phase}-{name}=0\n" in observed, f"{phase}-{name} did not succeed"
for output in ("hello, wolf\n", "the sum of the squares: 385\n", "its words: Interrupt\n"):
    assert output in observed, f"missing native output: {output!r}"
print("PASS M2: three native builds and runs as uid 1000; terminal bytes match Linux; sha256=" + hashlib.sha256(observed.encode()).hexdigest())
