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
    cp /root/shadow.start /etc/shadow; chmod 640 /etc/shadow
    [ "$mode" != pax ] || chmod 600 /etc/shadow
    [ "$s" != login-first ] || rm -f /etc/shadow
    rm -rf /run/sudo /var/run/sudo; rm -f /var/log/sudo.log
    (cd / && python3 "$in/linux-tty" --keys "$in/$s.keys" --prompt '$ ' --times "$out/$s.times" --end-wait 75 \
        "$out/$s.tty" -- "$prog")
    echo "linux-tty exit $?" > "$out/$s.run"
    cp /etc/shadow "$out/$s.shadow" 2>/dev/null || : > "$out/$s.shadow"
    cp /var/log/sudo.log "$out/$s.sudo.log" 2>/dev/null || : > "$out/$s.sudo.log"
}
session pw /usr/bin/pelt
session login /usr/bin/login
session login-max /usr/bin/login
[ ! -f "$in/login-time.keys" ] || session login-time /usr/bin/login
[ "$mode" != pax ] || session login-first /usr/bin/login
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
IN=/root/in-root row su-stdin-right 'su -c "id -u"'
IN=/root/in-one row su-stdin-wrong 'su -c "id -u"'
IN=/root/in-empty row su-stdin-eof 'su -c "id -u"'
} > "$out/stdin.txt" 2>&1
cp /var/log/sudo.log "$out/stdin.sudo.log" 2>/dev/null || : > "$out/stdin.sudo.log"
echo "##### done" >> "$out/stdin.txt"
