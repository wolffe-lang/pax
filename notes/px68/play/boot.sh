#!/bin/bash
# px68 (px67's recipe, this lane's paths), kasumi: the playground disk booted from a copy, the maintainer's
# session typed (session.py, his own QEMU line) under SeaBIOS and under
# the edk2 UEFI code file, then the transcript and the disk checked: both
# boots mount `/` from partition 2 read-write with no initramfs; the
# first is mount 1, the second mount 2, clean; the second boot reads the
# edited /etc/motd, lope's added directory, /home/pax/notes.txt and
# /root/note; `exit` ends every process and halts; and the host's
# dumpe2fs -h of partition 2 says clean, e2fsck -fn finds it clean and
# debugfs reads the four edits; the shipped file hashed again.
#   P=<tree> boot.sh [bios|uefi]...
set -u
L=$HOME/lanes/px68/play
P=${P:-$HOME/lanes/px68/pax}
printf '%s\n' $$ > "$L/boot.pid"
EDK2=${EDK2:-/usr/share/qemu/edk2-x86_64-code.fd}
for fw in ${*:-bios uefi}; do
S=$L/session-$fw; rm -rf "$S"; mkdir -p "$S"
cp --sparse=always "$L/out/pax-disk.img.px68" "$S/disk.img"
uptime
if [ "$fw" = uefi ]; then python3 "$P/notes/px68/play/session.py" "$S/disk.img" "$S/serial.log" "$EDK2"; rc=$?
else python3 "$P/notes/px68/play/session.py" "$S/disk.img" "$S/serial.log"; rc=$?; fi
echo "session.py $fw rc=$rc"
. "$P/tools/lib.sh"
serial_norm "$S/serial.log" | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' > "$S/serial.txt"
python3 - "$S/serial.txt" "$fw" <<'PY'
import re, sys
s = open(sys.argv[1], "rb").read().decode("utf-8", "replace")
lines = s.split("\n")
NOTE = "written on PAX, before the reboot"
ROOTNOTE = "root wrote this in /root"
ok = True
def need(c, what):
    global ok
    print(("PASS " if c else "FAIL ") + sys.argv[2] + ": " + what)
    ok = ok and c
roots = [l for l in lines if re.match(r"^root: PARTUUID=[0-9a-f-]{36} \(vda2\) on /: ext3, read-write, data=ordered$", l)]
need(len(roots) == 2, "both boots mount / from partition 2 by its PARTUUID, ext3, read-write, data=ordered (%d)" % len(roots))
need(lines.count("fstab: /dev/vda2 is /: ext3, read-write, data=ordered") == 2, "both boots' /etc/fstab names / first")
need(not any("recovering the journal" in l for l in lines), "no recovery: reboot(2) and exit leave the journal empty")
need(not any(l.startswith("boot: /boot/initramfs.cpio") for l in lines), "no initramfs loaded (R-px67-2)")
need(any(l.startswith("ext2: vda2: ") and "clean, mount 1;" in l for l in lines), "the first mount is mount 1 (a new disk)")
need(any(l.startswith("ext2: vda2: ") and "clean, mount 2;" in l for l in lines), "the second boot's mount is mount 2, clean")
first, second = s.split("PAX: the console")[1:3]
need("reboot(2): the volumes written and marked clean; restarting" in first, "reboot(2) wrote / and restarted")
def after(cmd, text):
    return text.split(cmd, 1)[1].split("\n")[1:4] if cmd in text else []
need("hello" in after("cat /etc/motd", second), "the second boot's /etc/motd is hello")
need(any(l.strip() == "/usr/share/tunes" or l.strip().endswith(" /usr/share/tunes") for l in after("lope list", second)), "lope's added directory is in the second boot's lope list")
need(NOTE in after("cat notes.txt", second), "the second boot's cat prints /home/pax/notes.txt")
need(ROOTNOTE in after("cat /root/note", second), "the second boot's cat prints /root/note")
m = second.split("cat /proc/self/mounts", 1)[1].split("$ ", 1)[0] if "cat /proc/self/mounts" in second else ""
need("/dev/root / ext3 rw,relatime 0 0" in m and "tmpfs /tmp tmpfs" in m, "/proc/self/mounts: /dev/root at / (ext3), a tmpfs at /tmp")
need("\nhalt\n" in second, "exit halts")
for l in m.strip().split("\n"):
    print("  " + l)
print("playground session %s: %s" % (sys.argv[2], "PASS" if ok else "FAIL"))
PY
p2=$(python3 "$P/tools/mkgpt" --print "$S/disk.img" | awk '$1 == 2 {print $4}')
lo=${p2%-*}; hi=${p2#*-}
dd if="$S/disk.img" of="$S/root.img" bs=512 skip="$lo" count=$(( hi - lo + 1 )) status=none
"$P/tools/e2fs" "$S" dumpe2fs -h root.img 2>/dev/null | grep -E '^(Filesystem state|Mount count|Filesystem features|Journal sequence|Journal start):' | tr -s ' '
"$P/tools/e2fs" "$S" e2fsck -fn root.img > "$S/fsck.txt" 2>&1; echo "e2fsck -fn rc=$? $(tail -n 1 "$S/fsck.txt")"
for f in /etc/motd /home/pax/notes.txt /root/note /home/pax/.local/share/lope/store; do
    echo "debugfs $f: $("$P/tools/e2fs" "$S" debugfs -R "cat $f" root.img 2>/dev/null | tr '\n' '|' | cut -c1-200)"
done
rm -f "$S/root.img"
done
sha256sum "$L/out/pax-disk.img.px68"
uptime
echo "boot.sh done $(date -Is)"
