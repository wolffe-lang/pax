#!/bin/bash
# px66, kasumi: the playground disk booted from a copy, the maintainer's
# session typed (session.py, his own QEMU line) under SeaBIOS and under
# the edk2 UEFI code file, then the transcript and the disk checked: both
# boots of each mount /home from /dev/vda2, the note is in `ls -l` and
# read back after the reset, `exit` halts, and the host's dumpe2fs -h of
# partition 2 says clean, e2fsck -fn finds it clean and debugfs reads
# the note; the shipped file hashed again.
#   boot.sh [bios|uefi]...
set -u
L=$HOME/lanes/px66/play
P=$HOME/lanes/px66/pax
printf '%s\n' $$ > "$L/boot.pid"
EDK2=${EDK2:-/usr/share/qemu/edk2-x86_64-code.fd}
for fw in ${*:-bios uefi}; do
S=$L/session-$fw; rm -rf "$S"; mkdir -p "$S"
cp "$L/out/pax-disk.img" "$S/disk.img"
uptime
if [ "$fw" = uefi ]; then python3 "$P/notes/px66/play/session.py" "$S/disk.img" "$S/serial.log" "$EDK2"; rc=$?
else python3 "$P/notes/px66/play/session.py" "$S/disk.img" "$S/serial.log"; rc=$?; fi
echo "session.py $fw rc=$rc"
. "$P/tools/lib.sh"
serial_norm "$S/serial.log" | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' > "$S/serial.txt"
python3 - "$S/serial.txt" "$fw" <<'PY'
import sys
s = open(sys.argv[1], "rb").read().decode("utf-8", "replace")
lines = s.split("\n")
NOTE = "written on PAX, before the reboot"
ok = True
def need(c, what):
    global ok
    print(("PASS " if c else "FAIL ") + sys.argv[2] + ": " + what)
    ok = ok and c
need(lines.count("fstab: /dev/vda2 on /home: ext2, read-write, write-back") == 2, "both boots mount /home from /dev/vda2, write-back")
need(sum(1 for l in lines if l.startswith("boot: /boot/initramfs.cpio from a disk: partition 1, GPT disk ")) == 2, "both boots say the initramfs came from partition 1 of the GPT disk")
need(any(l.startswith("ext2: vda2: ") and "clean, mount 1;" in l for l in lines), "the first mount is mount 1 (a new disk)")
need(any(l.startswith("ext2: vda2: ") and "clean, mount 2;" in l for l in lines), "the second boot's mount is mount 2, clean")
first, second = s.split("PAX: the console")[1:3]
need(any(l.endswith(" notes.txt") and " 34 " in l for l in first.split("\n")), "ls -l lists notes.txt, 34 bytes")
need("reboot(2): the volumes written and marked clean; restarting" in first, "reboot(2) wrote the volumes and restarted")
after = second.split("cat notes.txt", 1)[1] if "cat notes.txt" in second else ""
need(NOTE in after.split("\n")[1:3], "the second boot's cat prints the note")
need("\nhalt\n" in second, "exit halts")
for l in first.split("\n"):
    if "notes.txt" in l and l.startswith("-"):
        print("  " + l)
print("playground session %s: %s" % (sys.argv[2], "PASS" if ok else "FAIL"))
PY
dd if="$S/disk.img" of="$S/home.img" bs=1M skip=$(( (4096 * 512 + 192 * 1048576) / 1048576 )) status=none
"$P/tools/e2fs" "$S" dumpe2fs -h home.img 2>/dev/null | grep -E '^(Filesystem state|Mount count):' | tr -s ' '
"$P/tools/e2fs" "$S" e2fsck -fn home.img > "$S/fsck.txt" 2>&1; echo "e2fsck -fn rc=$? $(tail -n 1 "$S/fsck.txt")"
echo "debugfs: $("$P/tools/e2fs" "$S" debugfs -R "cat /pax/notes.txt" home.img 2>/dev/null)"
rm -f "$S/home.img"
done
sha256sum "$L/out/pax-disk.img"
uptime
echo "boot.sh done $(date -Is)"
