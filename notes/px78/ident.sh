#!/bin/sh
# px78 identity oracle: what Linux shows for each disk's identity.
echo 'IDENT BEGIN'
for d in /sys/block/*; do
    n=${d##*/}
    case $n in loop*|ram*) continue ;; esac
    echo "== $n"
    echo "device-dir: $(ls "$d/device/" | tr '\n' ' ')"
    for a in model serial vendor rev wwid; do
        if [ -f "$d/device/$a" ]; then printf '%s=[' "$a"; tr -d '\n' < "$d/device/$a"; echo ']'; else echo "$a absent"; fi
    done
    for a in removable ro size; do echo "$a=$(cat "$d/$a")"; done
    [ -f "$d/serial" ] && { printf 'disk-serial=['; tr -d '\n' < "$d/serial"; echo ']'; }
    echo "link: $(readlink "$d")"
done
echo 'IDENT END'
