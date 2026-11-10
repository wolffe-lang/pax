#!/bin/bash
# px106: Ubuntu 24.04's login, su, sudo and passwd, black-box, inside a
# THROWAWAY container (localhost/px106-auth:1, notes/px106/Containerfile:
# the stock packages, no network) as the container's root, with the
# accounts made in that container only. Nothing of them is read but what
# they show on a pseudo-terminal (tools/linux-tty) and what they leave in
# /etc/shadow and /var/log/sudo.log.
#
#   auth-ct.sh ubuntu|pax        (run inside the container; /ct holds the inputs)
#
# /ct: pelt (PAX's shell, the shell of every account here, so the shell's
# bytes are the same on both sides), linux-tty, shadow.txt (the
# accounts' lines, made by the suite from passwords it made at run time:
# root's, pax's and bob's, lobo locked), the session keys with those
# passwords in them (*.keys), sudoers, and, for `pax`, pax/ with PAX's su,
# sudo, passwd and login, put in place of Ubuntu's (4755, root's; login
# 0755). Every session starts from the same /etc/shadow and an empty log;
# login-first starts with no /etc/shadow at all (pax only: Ubuntu's login
# has no first-boot rule). Out: /ct/out/MODE/<session>.tty (every byte the
# terminal showed), .tty.rc, .times (linux-tty --times), .shadow (the file
# after), sudo.log, and stdin.txt (sudo -S and su with no terminal).
#
# The PAM configuration is px103's "bare" one: the lines naming pam_env,
# pam_umask, pam_limits, pam_mail, pam_motd, pam_lastlog, pam_loginuid and
# pam_keyinit removed (a configuration change measured by its effect; no
# module is read) and /etc/environment emptied, since PAX has no PAM.
set -u
mode=$1
in=/ct
out=$in/out/$mode
rm -rf "$out"; mkdir -p "$out"
# The container's hostname in /etc/hosts as Ubuntu's installer writes it (127.0.1.1), so Ubuntu's sudo
# resolves it whatever the engine: podman's --hostname writes the line; docker's, with no network, does
# not, and sudo then prints `unable to resolve host` (pax#324's CI).
grep -qE "[[:space:]]$(hostname)([[:space:]]|\$)" /etc/hosts || printf '127.0.1.1\t%s\n' "$(hostname)" >> /etc/hosts
# Every output readable by the host's user, whatever user the engine maps the container's root to
# (docker: the host's root, so a copy of the 0600 /etc/shadow was unreadable to the runner; rootless
# podman: the host's user).
trap 'chmod -R a+rX "$out" 2>/dev/null' EXIT
for u in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 { print $1 }' /etc/passwd); do userdel -r "$u" >/dev/null 2>&1; done
for g in $(awk -F: '$3 == 1000 || $3 == 990 || $3 == 1001 || $3 == 2000 { print $1 }' /etc/group); do groupdel "$g" >/dev/null 2>&1; done
cp "$in/pelt" /usr/bin/pelt; chmod 755 /usr/bin/pelt
groupadd -g 1000 pax; groupadd -g 990 lobo; groupadd -g 1001 bob; groupadd -g 2000 pack
useradd -u 1000 -g 1000 -G pack -d /home/pax -m -s /bin/pelt pax
useradd -u 990 -g 990 -d /srv/lobo -s /bin/false lobo 2>/dev/null
useradd -u 1001 -g 1001 -d /home/bob -m -s /bin/pelt bob
usermod -s /bin/pelt root
mkdir -p /srv/lobo; chown 990:990 /srv/lobo
while IFS=: read -r n f _; do [ "$f" = '!' ] || usermod -p "$f" "$n"; done < "$in/shadow.txt"
for f in /etc/pam.d/*; do sed -i -E '/pam_(env|umask|limits|mail|motd|lastlog|loginuid|keyinit)\.so/d' "$f"; done
: > /etc/environment
# R-px106-6 (B3): the admin session runs on each side's own shipped policy, Ubuntu's stock
# /etc/sudoers (kept here before the sessions' policy replaces it) and PAX's user/sudo/sudoers.
cp /etc/sudoers /root/sudoers.stock
cp "$in/sudoers" /etc/sudoers; chown 0:0 /etc/sudoers; chmod 0440 /etc/sudoers
rm -rf /etc/sudoers.d; mkdir -m 0755 /etc/sudoers.d
mkdir -p /var/log
if [ "$mode" = pax ]; then
    for p in su sudo passwd; do cp "$in/pax/$p" "/usr/bin/$p"; chown 0:0 "/usr/bin/$p"; chmod 4755 "/usr/bin/$p"; done
    cp "$in/pax/login" /usr/bin/login; chown 0:0 /usr/bin/login; chmod 0755 /usr/bin/login
fi
cp /etc/shadow /root/shadow.start
{ echo "== $mode: $(sha256sum /usr/bin/su /usr/bin/sudo /usr/bin/passwd /usr/bin/login | cut -c1-16 | tr '\n' ' ')"
  stat -c '%a %U:%G %n' /etc/shadow /usr/bin/su /usr/bin/sudo /usr/bin/passwd /usr/bin/login
  grep -E '^(root|pax|lobo|bob):' /etc/passwd; } > "$out/setup.txt"
session() { # name program
    local s=$1 prog=$2
    # admin (R-px106-6, B3): pax in group sudo, the side's own shipped policy; login-trap
    # (R-px106-9): pax in sudo too, locked, so only root and sudo's members open the door.
    [ "$s" != login-trap ] || usermod -aG sudo pax
    if [ "$s" = admin ]; then
        usermod -aG sudo pax
        if [ "$mode" = pax ]; then cp "$in/sudoers.shipped" /etc/sudoers; else cp /root/sudoers.stock /etc/sudoers; fi
        chown 0:0 /etc/sudoers; chmod 0440 /etc/sudoers
        # the log a file, as on PAX's image (Ubuntu's stock policy logs to syslog): one sudoers.d line
        printf 'Defaults logfile=/var/log/sudo.log\n' > /etc/sudoers.d/log; chown 0:0 /etc/sudoers.d/log; chmod 0440 /etc/sudoers.d/log
    fi
    cp /root/shadow.start /etc/shadow; chmod 640 /etc/shadow
    [ "$mode" != pax ] || chmod 600 /etc/shadow
    [ "$s" != login-first ] && [ "$s" != login-trap ] || rm -f /etc/shadow
    rm -rf /run/sudo /var/run/sudo; rm -f /var/log/sudo.log
    (cd / && python3 "$in/linux-tty" --keys "$in/$s.keys" --prompt '$ ' --times "$out/$s.times" --end-wait 75 \
        "$out/$s.tty" -- "$prog")
    echo "linux-tty exit $?" > "$out/$s.run"
    stat -c '%a %U:%G' /etc/shadow > "$out/$s.shadow-mode" 2>/dev/null || echo none > "$out/$s.shadow-mode"
    cp /etc/shadow "$out/$s.shadow" 2>/dev/null || : > "$out/$s.shadow"
    cp /var/log/sudo.log "$out/$s.sudo.log" 2>/dev/null || : > "$out/$s.sudo.log"
    [ "$s" != login-trap ] || gpasswd -d pax sudo > /dev/null
    if [ "$s" = admin ]; then
        gpasswd -d pax sudo > /dev/null
        cp "$in/sudoers" /etc/sudoers; chown 0:0 /etc/sudoers; chmod 0440 /etc/sudoers; rm -f /etc/sudoers.d/log
    fi
}
session pw /usr/bin/pelt
session login /usr/bin/login
session login-max /usr/bin/login
[ ! -f "$in/login-time.keys" ] || session login-time /usr/bin/login
[ "$mode" != pax ] || session login-first /usr/bin/login
[ "$mode" != pax ] || session login-trap /usr/bin/login
session admin /usr/bin/pelt
# No terminal: sudo -S and su reading standard input (setsid: no controlling terminal).
cp /root/shadow.start /etc/shadow; [ "$mode" != pax ] || chmod 600 /etc/shadow
rm -rf /run/sudo /var/run/sudo; rm -f /var/log/sudo.log
bobpw=$(sed -n 's/^bob //p' "$in/passwords.txt"); rootpw=$(sed -n 's/^root //p' "$in/passwords.txt"); wrong=$(sed -n 's/^wrong //p' "$in/passwords.txt")
row() { # name, then the command line, its standard input from the file named by $IN
    local name=$1; shift
    echo "=== ROW $name"
    (cd / && env -i HOME=/home/bob TERM=linux PATH=/usr/bin:/bin setsid -w setpriv --reuid=1001 --regid=1001 --init-groups -- /bin/bash -c "$*" < "$IN" > /root/o 2> /root/e); echo "--- rc $?"
    echo "--- stdout"; cat /root/o; echo "--- stderr"; cat /root/e
}
printf '%s\n' "$bobpw" > /root/in-right; printf '%s\n%s\n%s\n' "$wrong" "$wrong" "$wrong" > /root/in-wrong
printf '%s\n' "$wrong" > /root/in-one; : > /root/in-empty; printf '%s\n' "$rootpw" > /root/in-root
{
IN=/root/in-right row sudo-S-right 'sudo -S id -u'
IN=/root/in-empty row sudo-n-after 'sudo -n id -u'
IN=/root/in-wrong row sudo-S-wrong 'sudo -S -k id -u'
IN=/root/in-one row sudo-S-one-then-eof 'sudo -S -k id -u'
IN=/root/in-empty row sudo-S-eof 'sudo -S -k id -u'
IN=/root/in-empty row sudo-no-tty 'sudo -k id -u'
IN=/root/in-empty row sudo-n 'sudo -n -k id -u'
IN=/root/in-right row sudo-S-prompt "sudo -S -k -p 'pw for %p as %U on %h: ' id -u"
# px115: a record another holder of the parent's pid left. sudoers_timestamp(5): a record made with no
# terminal names its parent by pid and by start time. Planted as root in PAX's record format
# (/var/run/sudo/ts/UID, root's with the caller's group, 0600) for the very parent that then runs
# `sudo -n` as bob: once with no start time (the kind PAX's sudo wrote before px115), once with a start
# time a tick before the parent's own. Neither is this parent's, so sudo asks. Ubuntu's sudo keeps its
# records in a file named for the user, finds none, and asks the same. The line after the sudo makes
# bash fork it (a last command is exec'd in bash's place), so the planted parent is sudo's parent.
echo "=== ROW sudo-n-pid-reused"
(cd / && setsid -w /bin/bash -c '
    p=$$; s=$(cut -d" " -f6 /proc/$$/stat); t=$(cut -d" " -f22 /proc/$$/stat); now=$(( $(date +%s%N) / 1000000 ))
    mkdir -p /var/run/sudo/ts && chmod 711 /var/run/sudo && chmod 700 /var/run/sudo/ts
    printf "ppid %s sid %s time %s\nppid %s start %s sid %s time %s\n" "$p" "$s" "$now" "$p" "$((t - 1))" "$s" "$now" > /var/run/sudo/ts/1001
    chown 0:1001 /var/run/sudo/ts/1001 && chmod 600 /var/run/sudo/ts/1001
    env -i HOME=/home/bob TERM=linux PATH=/usr/bin:/bin setpriv --reuid=1001 --regid=1001 --init-groups -- sudo -n id -u
    st=$?; exit $st' < /root/in-empty > /root/o 2> /root/e); echo "--- rc $?"
echo "--- stdout"; cat /root/o; echo "--- stderr"; cat /root/e
rm -f /var/run/sudo/ts/1001
# px115: `sudo -k -S` with a record fresh for the same parent and session still reads the password's
# line from standard input, and the command gets what follows it byte for byte (the form an ssh
# client's `printf PASSWORD | ssh HOST "sudo -k -S ..."` relies on).
printf '%s\n%s\n%s\n' "$bobpw" "$bobpw" 'px115-data-line' > /root/in-twice
IN=/root/in-twice row sudo-k-S-fresh "sudo -S id -u; sudo -k -S /bin/sh -c 'id -u; cat'"
IN=/root/in-root row su-stdin-right 'su -c "id -u"'
IN=/root/in-one row su-stdin-wrong 'su -c "id -u"'
IN=/root/in-empty row su-stdin-eof 'su -c "id -u"'
# A terminal on standard input and no controlling terminal (setsid inside script(1)'s
# pseudo-terminal): Linux's su still turns the echo off and ends the prompt's line (measured).
echo "=== ROW su-tty-no-ctty"
(sleep 2; printf '%s\r' "$wrong"; sleep 5) | (cd / && env -i HOME=/home/bob TERM=linux PATH=/usr/bin:/bin setpriv --reuid=1001 --regid=1001 --init-groups -- \
    script -qfec 'setsid -w su -c "id -u"' /dev/null) > /root/o 2>&1; echo "--- rc $?"
echo "--- the terminal"; tr -d '\r' < /root/o
} > "$out/stdin.txt" 2>&1
cp /var/log/sudo.log "$out/stdin.sudo.log" 2>/dev/null || : > "$out/stdin.sudo.log"
echo "##### done" >> "$out/stdin.txt"
