#!/usr/bin/env bash
set -euo pipefail
L=$HOME/lanes/px70
ulimit -c 0
exec 9>"$HOME/lanes/kasumi-cores-12-15.lock"
flock 9
export PAX_VT_KERNEL=/usr/lib/modules/7.3.0-4-cachyos/vmlinuz
tag=${PAX_MEASURE_TAG:-measure}
echo $$ > "$L/out/$tag.pid"
trap 'rc=$?; echo "$rc" > "$L/out/$tag.exit"' EXIT
python3 "$L/pax/notes/px70/vt-measure.py" "$L" header
podman run --rm --name px70-measure-build --cpuset-cpus 12-15 --ulimit core=0:0 \
    -v "$L:$L:Z" -e L="$L" -e PAX_MEASURE_ONLY localhost/px13-ubuntu bash -c '
    set -euo pipefail
    flags=(); [ -z "${PAX_MEASURE_ONLY:-}" ] || flags=(-DPX70_NO_RGB)
    cc "${flags[@]}" -static -O1 -Wall -Wextra -Wno-unused-result -Wno-unused-function \
       -I "$L/measure" -o "$L/measure/px70probe" "$L/pax/notes/px70/vtprobe.c"'
"$L/pax/tools/mkinitramfs" "$L/measure/px70.cpio" "/vtprobe=$L/measure/px70probe:755"
sha256sum "$PAX_VT_KERNEL" "$PAX_VT_KERNEL" "$L/measure/px70probe"
python3 "$L/pax/notes/px70/vt-measure.py" "$L"
