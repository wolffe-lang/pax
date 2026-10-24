#!/usr/bin/env python3
# px68: how long a boot's replay took, from QEMU's own trace of the disk
# with the host's timestamps (`-msg timestamp=on`: each line
# `PID@SEC.USEC:virtio_blk_…`): from the journal superblock's first read
# (the mount's) to the completion of the first FLUSH after its first
# write (the replay's emptied log), with what lay between.
#   replay-time.py TRACE IMAGE OFFSET   (IMAGE the disk after the boot, its volume at OFFSET bytes)
import importlib.machinery
import os
import re
import sys
import types

sys.dont_write_bytecode = True
here = os.path.dirname(os.path.abspath(__file__))
loader = importlib.machinery.SourceFileLoader("mkjournal", os.path.join(here, "..", "..", "tools", "mkjournal"))
mj = types.ModuleType("mkjournal")
loader.exec_module(mj)

trace, image, off = sys.argv[1], sys.argv[2], int(sys.argv[3])
v = mj.Vol(image, off)
per = v.bs // 512
base = off // 512
jsb = set(base + v.map[0] * per + k for k in range(per))
jall = set(base + p * per + k for p in v.map for k in range(per))
pat = re.compile(r"^\d+@(\d+)\.(\d+):virtio_blk_(handle_write|handle_read|req_complete) vdev \S+ req (\S+)(?: sector (\d+))?")
pend = {}
ev = []  # (handle time, done time, kind, sector)
for line in open(trace, errors="replace"):
    m = pat.match(line)
    if not m:
        continue
    t = int(m.group(1)) + int(m.group(2)) / 1e6
    kind, req = m.group(3), m.group(4)
    if kind != "req_complete":
        pend[req] = (t, "W" if kind == "handle_write" else "R", int(m.group(5)))
    else:
        r = pend.pop(req, None)
        ev.append((r[0], t, r[1], r[2]) if r else (t, t, "F", None))
if not ev:
    head = open(trace, errors="replace").readline().rstrip("\n")
    sys.exit("replay-time: no timestamped virtio_blk events in %s; its first line: %r" % (trace, head[:200]))
i0 = next((i for i, e in enumerate(ev) if e[2] == "R" and e[3] in jsb), None)
iw = next((i for i, e in enumerate(ev) if i0 is not None and i > i0 and e[2] == "W" and e[3] in jsb), None)
i1 = next((i for i, e in enumerate(ev) if iw is not None and i > iw and e[2] == "F"), None)
if i1 is None:
    sys.exit("replay-time: no journal superblock read, rewrite and FLUSH after it in %s" % trace)
mid = ev[i0:i1 + 1]
jr = sum(1 for e in mid if e[2] == "R" and e[3] in jall)
hw = sum(1 for e in mid if e[2] == "W" and e[3] not in jall)
fl = sum(1 for e in mid if e[2] == "F")
boot = ev[i1][1] - ev[0][0]
print("replay-time: %.1f ms from the journal superblock's read to the FLUSH after its rewrite: %d journal reads, %d home writes, %d FLUSHes; %.1f ms from the boot's first disk request to it" % (
    (ev[i1][1] - ev[i0][0]) * 1e3, jr, hw, fl, boot * 1e3))
