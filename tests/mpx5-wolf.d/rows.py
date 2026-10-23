#!/usr/bin/env python3
"""Independent witnesses: differential equality alone may agree on failure."""
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text()
who = sys.argv[2]
# px65: the compiler's identity is the pin's (user/wolf.pin's version
# line), so a pin move moves the witness with it, never a stale literal.
pin = (Path(__file__).resolve().parent / "../../user/wolf.pin").read_text()
VERSION_LINE = next(l.split("=", 1)[1].strip().strip('"') for l in pin.splitlines()
                    if l.startswith("WOLF_SRC_VERSION_LINE="))
IMPL_VERSION = VERSION_LINE.split()[1]
programs = ("hello", "loop", "signal", "spawn", "exec", "fork", "host", "std")
errors = []
for marker in ("typed=0", "object=0", "build=2", "release=2"):
    if f"\n{marker}\n" not in text:
        errors.append(f"missing status: {marker}")
for wall in ("cannot run `cc`", "release tier requires clang >="):
    if wall not in text:
        errors.append(f"M2 wall missing: {wall}")
for program in programs:
    for command, status in (("check", 2), ("typecheck", 0), ("fmt", 0), ("run", 0)):
        if f"\n{command}-{program}={status}\n" not in text:
            errors.append(f"{command}-{program} did not return {status}")
if "wolf: `check` is not a wolf command." not in text:
    errors.append("missing check-command refusal")
if VERSION_LINE not in text:
    errors.append("version missing")
records = {}
for line in text.splitlines():
    if not line.startswith("{"):
        continue
    r = json.loads(line)
    if r.get("protocol") != 1:
        errors.append("wrong protocol")
    records[(Path(r["file"]).stem, r["phase_reached"])] = r
    if r.get("impl") != "wolfgang" or r.get("impl_version") != IMPL_VERSION:
        errors.append("wrong checked-machine identity")
for program in programs:
    if records.get((program, "typecheck"), {}).get("verdict") != "pass":
        errors.append(f"missing passing typecheck: {program}")
for program in (*programs, "x"):
    if (program, "run") not in records:
        errors.append(f"missing run observation: {program}")
for program, output in (("hello", "hello, wolf\n"), ("loop", "the sum of the squares: 385\n"),
                        ("signal", "INTERRUPT is signal 2 here\nits words: Interrupt\n"),
                        ("spawn", "spawn: joined, answer 42\n"), ("exec", "exec: child status 7\n"),
                        ("std", "std: wolf\n"), ("x", "typed at PAX console, checked by wolf\n")):
    r = records.get((program, "run"), {})
    if r.get("verdict") != "exit(0)" or output not in (r.get("stdout_inline") or ""):
        errors.append(f"wrong output/verdict: {program}")
# os_fork returns an error row, not a protocol-level refusal. Catch it in
# the fixture so the machine's answer is explicitly named in the output.
r = records.get(("fork", "run"), {})
if r.get("verdict") != "exit(0)" or r.get("stdout_inline") != "fork: unsupported\n":
    errors.append("fork not refused by name")
r = records.get(("host", "run"), {})
home = "/" if who == "root" else "/home/pax"
for want in ("clock: a 20 ms sleep, at least 20 ms passed: true\n",
             f"env: HOME before the program sets it: {home}\n",
             "env: HOME after env_set: /home/wolf\n", "tree: x.lu in the working directory:"):
    if want not in (r.get("stdout_inline") or ""):
        errors.append(f"host witness missing: {want.rstrip()}")
for e in errors:
    print(f"FAIL W2 {who}: {e}")
if not errors:
    print(f"PASS W2 {who}: command statuses, observation identities and independent witnesses")
sys.exit(bool(errors))
