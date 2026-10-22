#!/usr/bin/env bash
# Re-run the PTY census from the retained final checked-only root.
set -euo pipefail
ulimit -c 0
L=/home/mfwolffe/lanes/px60
r=$(mktemp -d "$L/census-root.XXXXXX")
cp -a "$L/session4-build/mpx5-wolf/root/." "$r/"
printf '//! member: false\nfn main() {}\n' > "$r/x.lu"
"$L/pax/tests/mpx5-wolf.d/verify-bins" "$r/usr/bin"
# A fresh retained root; no automatic deletion or host-wide mount.
podman run --rm --privileged --cpuset-cpus 0-3 -v "$L:/work" \
 -e ROOT="/work/${r##*/}" localhost/px13-ubuntu bash -c '
 set -euo pipefail
 mkdir -p "$ROOT/dev" "$ROOT/proc"
 mount --rbind /dev "$ROOT/dev"
 mount -t proc proc "$ROOT/proc"
 python3 -I /work/pax/notes/px60/census.py "$ROOT" /work/census-replay /work/pax/notes/px60/chroot-exec.py
 '
