#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px70
ulimit -c 0
exec 9>"$HOME/lanes/kasumi-cores-12-15.lock"; flock 9
python3 "$L/pax/notes/px70/key-measure.py" "$L" header
podman run --rm --name px70-keyprobe --cpuset-cpus 12-15 --ulimit core=0:0 \
    -v "$L:$L:Z" -e L="$L" -e PAX_KEYS_MODE localhost/px13-ubuntu bash -c '
    set -euo pipefail
    flags=(); [ "${PAX_KEYS_MODE:-}" != yew ] || flags=(-DPX70_YEW_MODE)
    cc "${flags[@]}" -static -O1 -I "$L/measure" -o "$L/measure/keyprobe" "$L/pax/notes/px70/keyprobe.c"'
"$L/pax/tools/mkinitramfs" "$L/measure/keys.cpio" "/keyprobe=$L/measure/keyprobe:755"
sha256sum "$L/measure/keyprobe" /usr/lib/modules/7.3.0-4-cachyos/vmlinuz
python3 "$L/pax/notes/px70/key-measure.py" "$L"
