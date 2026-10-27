#!/bin/pelt
# Passwordless root entry for the live medium only. Not installed login.
printf 'PAX live medium: log in as root (no password).\n'
while :; do
    printf 'login: '
    IFS= read -r account || exit 0
    if [ "$account" = root ]; then
        export HOME=/root USER=root LOGNAME=root PATH=/bin TERM=linux
        [ ! -f /etc/shrc ] || export ENV=/etc/shrc
        cd /root || exit 1
        exec /bin/pelt -i -m
    fi
    printf 'Only root is available on the live medium.\n'
done
