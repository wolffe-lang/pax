#!/bin/bash
# px65 (px63's), kasumi: the playground booted with a copy of a test disk and the
# maintainer's session typed (session.py), then the transcript and the
# disk checked: both boots mount /home from the disk, the note is in
# `ls -l` and read back after the reset, e2fsck -fn finds the copy
# clean and debugfs reads the note; the shipped files hashed again.
set -u
L=$HOME/lanes/px65/play
P=${PX65_TREE:-$HOME/lanes/px65/pax}
printf '%s\n' $$ > "$L/boot.pid"
S=$L/session; rm -rf "$S"; mkdir -p "$S"
cp "$L/out/pax-home.test.img" "$S/home.img"
uptime
python3 "$P/notes/px65/play/session.py" "$L/out/pax-playground.iso" "$S/home.img" "$S/serial.log"; rc=$?
echo "session.py rc=$rc"
. "$P/tools/lib.sh"
serial_norm "$S/serial.log" > "$S/serial.txt"
python3 - "$S/serial.txt" <<'PY'
import sys
s = open(sys.argv[1], "rb").read().decode("utf-8", "replace")
lines = s.split("\n")
NOTE = "written on PAX, before the reboot"
ok = True
def need(c, what):
    global ok
    print(("PASS " if c else "FAIL ") + what)
    ok = ok and c
need(lines.count("fstab: /dev/vda on /home: ext2, read-write, write-back") == 2, "both boots mount /home from the disk, write-back")
need(any(l.startswith("ext2: vda: ") and "clean, mount 1;" in l for l in lines), "the first mount is mount 1 (a new disk)")
need(any(l.startswith("ext2: vda: ") and "clean, mount 2;" in l for l in lines), "the second boot's mount is mount 2, clean")
first, second = s.split("PAX: the console")[1:3]
need(any(l.endswith(" notes.txt") and " 34 " in l for l in first.split("\n")), "ls -l lists notes.txt, 34 bytes")
need("reboot(2): the volumes written and marked clean; restarting" in first, "reboot(2) wrote the volumes and restarted")
after = second.split("cat notes.txt", 1)[1] if "cat notes.txt" in second else ""
need(NOTE in after.split("\n")[1:3], "the second boot's cat prints the note")
need("\nhalt\n" in second, "exit halts")
for l in first.split("\n"):
    if "notes.txt" in l and l.startswith("-"):
        print("  " + l)
print("playground session: " + ("PASS" if ok else "FAIL"))
PY
"$P/tools/e2fs" "$S" e2fsck -fn home.img > "$S/fsck.txt" 2>&1; echo "e2fsck -fn rc=$? $(tail -n 1 "$S/fsck.txt")"
echo "debugfs: $("$P/tools/e2fs" "$S" debugfs -R "cat /pax/notes.txt" home.img 2>/dev/null)"
"$P/tools/e2fs" "$S" debugfs -R "stat /pax/notes.txt" home.img 2>/dev/null | head -12
sha256sum "$L/out/pax-playground.iso" "$L/out/pax-home.test.img"
uptime
echo "boot.sh done $(date -Is)"
