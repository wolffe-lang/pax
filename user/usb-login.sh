#!/bin/pelt
# Passwordless root entry for the live medium only. Not installed login.
# The terminal is root's again first, as login(1) gives a terminal to the
# account it logs in (px98; a kernel that keeps no owner refuses it, and
# the login goes on; a medium with no chown skips it).
printf 'PAX live medium: log in as root (no password).\n'
while :; do
    printf 'login: '
    IFS= read -r account || exit 0
    if [ "$account" = root ]; then
        export HOME=/root USER=root LOGNAME=root PATH=/bin TERM=linux
        [ ! -f /etc/shrc ] || export ENV=/etc/shrc
        cd /root || exit 1
        [ ! -x /bin/chown ] || { /bin/chown 0:0 /dev/stdin 2>/dev/null && /bin/chmod 600 /dev/stdin 2>/dev/null; }
        exec /bin/pelt -i -m
    fi
    printf 'Only root is available on the live medium.\n'
done
