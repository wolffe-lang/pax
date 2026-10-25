#!/usr/bin/env bash
# Run inside the existing Ubuntu build container. Unpack pinned oracle
# binaries into this lane only; no package scripts or package installation.
set -euo pipefail
L=$HOME/lanes/px71
# The container's HOME is /root; the lane root is supplied explicitly.
L=$1
. "$L/pax/user/disktools.pin"
store=$L/oracles
mkdir -p "$store/debs" "$store/root" "$store/bin"
for p in $DISKTOOLS_DEBS; do
    fv=${p}_FILE; pv=${p}_POOL; sv=${p}_SHA256
    file=${!fv}; pool=${!pv}; sum=${!sv}
    if [ ! -f "$store/debs/$file" ]; then
        curl -fsSL --retry 2 "https://archive.ubuntu.com/ubuntu/pool/$pool/${file//+/%2b}" -o "$store/debs/$file"
    fi
    echo "$sum  $store/debs/$file" | sha256sum -c -
    dpkg-deb -x "$store/debs/$file" "$store/root"
done
for p in sgdisk sfdisk mkfs.fat fsck.fat mcopy mmd mdir mtype; do
    executable=
    for bin in usr/sbin usr/bin sbin; do
        if [ -x "$store/root/$bin/$p" ]; then executable=$store/root/$bin/$p; break; fi
    done
    [ -n "$executable" ]
    printf '#!/bin/sh\nexec env LD_LIBRARY_PATH="%s/usr/lib/x86_64-linux-gnu:%s/lib/x86_64-linux-gnu" %s "$@"\n' "$store/root" "$store/root" "$executable" > "$store/bin/$p"
    chmod 755 "$store/bin/$p"
done
"$store/bin/sgdisk" --version
"$store/bin/sfdisk" --version
"$store/bin/fsck.fat" --help >/dev/null 2>&1 || [ "$?" = 2 ]
