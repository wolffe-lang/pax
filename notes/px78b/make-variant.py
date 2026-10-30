#!/usr/bin/env python3
"""px78b: the kasumi leg for the test stick, lane-local (px77c's make-variants way).

    make-variant.py METAL.py OUT.py ATA-MODEL MODEL SERIAL

From the branch's tests/mpx6-install.d/metal.py: the target is kasumi's
own disk as the maintainer's allow-list line names it, an ide-hd with
ATA-MODEL (e.g. "Samsung SSD 860 EVO 500GB") that PAX and Linux show as
MODEL (its first 16 bytes, trimmed: "Samsung SSD 860"), and SERIAL, at
500107862016 bytes; the leg never appends the line: the staged stick
already carries it. Every edit is asserted to apply exactly once. (The
serial is an argument: the public tree does not carry the maintainer's.)
"""
import sys
src, out, ata, model, serial = sys.argv[1:6]
assert ata[:16].rstrip() == model, (ata, model)
s = open(src).read()
edits = [
    ("TARGET = {'model': 'Samsung SSD 870 EVO 500GB', 'serial': 'PX78-TARGET-0001', 'bytes': 500107862016, 'size': '500.1 GB'}",
     f"TARGET = {{'model': {ata!r}, 'serial': {serial!r}, 'bytes': 500107862016, 'size': '500.1 GB'}}"),
    ("LINUX_MODEL = 'Samsung SSD 870'  # what CachyOS's /sys/block/sdX/device/model shows (16 bytes, trimmed)\n",
     "LINUX_MODEL = 'Samsung SSD 870'  # what CachyOS's /sys/block/sdX/device/model shows (16 bytes, trimmed)\n"
     f"TARGET_MODEL = {model!r}  # px78b: kasumi's target as the maintainer's line names it\n"),
    ("SUMMARY = f'Erase {LINUX_MODEL}, serial {TARGET[\"serial\"]}", "SUMMARY = f'Erase {TARGET_MODEL}, serial {TARGET[\"serial\"]}"),
    ("    line.write_text(f'model={LINUX_MODEL} serial={TARGET[\"serial\"]}\\n')\n"
     "    run([paxfat, '--offset', esp, 'append', stick, line, '/pax/install-targets'])\n",
     "    line.write_text(f'model={TARGET_MODEL} serial={TARGET[\"serial\"]}\\n')\n"
     "    # px78b: the staged stick already carries the line; no append here.\n"),
    ("    need(listed, f'model={LINUX_MODEL} serial={TARGET[\"serial\"]}', 'M0-stick')",
     "    need(listed, f'model={TARGET_MODEL} serial={TARGET[\"serial\"]}', 'M0-stick')"),
    ("f'/dev/sdc bytes={TARGET[\"bytes\"]} sector=512 model={LINUX_MODEL} serial={TARGET[\"serial\"]}'",
     "f'/dev/sdc bytes={TARGET[\"bytes\"]} sector=512 model={TARGET_MODEL} serial={TARGET[\"serial\"]}'"),
    ("m.command(f\"echo 'model={LINUX_MODEL} serial={TARGET['serial']}' > /tmp/allow\"",
     "m.command(f\"echo 'model={TARGET_MODEL} serial={TARGET['serial']}' > /tmp/allow\""),
]
for old, new in edits:
    assert s.count(old) == 1, old
    s = s.replace(old, new)
open(out, 'w').write(s)
print(f'{len(edits)} edits applied once each: {out}')
