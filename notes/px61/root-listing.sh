#!/usr/bin/env bash
# R-px61-1 covers FIFO only. The full / listing is independently
# measured with /proc present, never suppressed (pax#113).
set -euo pipefail
L=$HOME/lanes/px61
printf '%s\n' $$ > "$L/root-listing.pid"
ulimit -c 0
uptime
O=$L/root-listing
mkdir -p "$O"
python3 -I "$L/pax/notes/px61/unpack-play.py" "$L/w/play.cpio" "$O/root" "$O/owners"
printf 'aspen /\naspen -pugsD /etc\nexit 0\n' > "$O/root.keys"
export PAX_CACHE=$L/cache PAX_BUILD=$O PAX_ENGINE=podman PAX_TREE_IMAGE=localhost/px13-ubuntu
for role in root pax; do
    argv=(/bin/env ENV=/etc/shrc /bin/sh -i -m)
    [ "$role" = root ] || argv=(/bin/as 1000 1000 /bin/env HOME=/home/pax ENV=/etc/shrc /bin/sh -i -m)
    taskset -c 8-11 "$L/pax/tools/linux-tree" --root "$O/root" --keys "$O/root.keys" --prompt '$ ' \
        --argv0 "${argv[0]}" --size 256m --rdev --nsproc --owners "$O/owners" "$O/linux-$role.tty" -- "${argv[@]}"
    echo "root listing $role status $(cat "$O/linux-$role.tty.rc")"
done
uptime
