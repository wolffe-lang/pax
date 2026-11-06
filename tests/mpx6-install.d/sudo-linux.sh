#!/bin/bash
# px103: the sudo-session.txt lines on Linux, in a throwaway container with no network
# (localhost/px103-sudo:1: Ubuntu 24.04's own sudo), as the container's root.
#   sudo-linux.sh SESSION_TXT SUDOERS OUTDIR
# Same accounts as the installed image (root, wolf 1000, lobo 990 with /bin/false), the same
# /etc/sudoers plus ONE Linux-only line (`Defaults logfile`, so that the log is a file).
# Writes OUTDIR/s-root.txt, s-wolf.txt, s-lobo.txt, s-log.txt.
set -u
sess=$1; sudoers=$2; out=$3
for u in $(awk -F: '$3 == 1000 || $3 == 990 { print $1 }' /etc/passwd); do userdel -r "$u" >/dev/null 2>&1; done
for g in $(awk -F: '$3 == 1000 || $3 == 990 { print $1 }' /etc/group); do groupdel "$g" >/dev/null 2>&1; done
groupadd -g 1000 wolf; groupadd -g 990 lobo
useradd -u 1000 -g 1000 -d /home/wolf -m -s /bin/sh wolf
useradd -u 990 -g 990 -d /srv/lobo -s /bin/false lobo
cp "$sudoers" /etc/sudoers; chown 0:0 /etc/sudoers; chmod 440 /etc/sudoers
echo 'Defaults logfile="/var/log/sudo.log"' >> /etc/sudoers
mkdir -p /var/log "$out"; : > /var/log/sudo.log; chmod 600 /var/log/sudo.log
cd /
rm -f /tmp/s-wolf.txt
section() { awk -v s="[$1]" '/^\[/ { on = ($0 == s); next } on && !/^#/ && NF' "$sess"; }
typed() { printf '%s >> %s 2>&1; echo rc=$? >> %s\n' "$1" "$2" "$2"; }
: > "$out/s-root.txt"; : > "$out/s-lobo.txt"
section root | while IFS= read -r l; do /bin/sh -c "$(typed "$l" "$out/s-root.txt")" </dev/null; done
section wolf | while IFS= read -r l; do setpriv --reuid=1000 --regid=1000 --init-groups -- /bin/sh -c "$(typed "$l" /tmp/s-wolf.txt)" </dev/null; done
cp /tmp/s-wolf.txt "$out/s-wolf.txt"
section lobo | while IFS= read -r l; do /bin/sh -c "$(typed "sudo -n -u lobo /bin/sudo -n $l" "$out/s-lobo.txt")" </dev/null; done
cp /var/log/sudo.log "$out/s-log.txt"
