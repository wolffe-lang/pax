#!/usr/bin/env bash
# px80: restage after a README change: the staged tree's README.md replaced
# by notes/px80/bundle-README.md, then stage.sh's last steps again (the
# contents' sums, the reproducible tar.xz at the tree commit's time, its
# sha256 read twice). Every other staged file stays as stage.sh made it.
set -euo pipefail
L=$HOME/lanes/px80
P=$L/pax
N=pax-wolf-link-18.1.8
S=$L/stage; B=$S/$N
cp "$P/notes/px80/bundle-README.md" "$B/README.md"; chmod 644 "$B/README.md"
for k in 1 2; do (cd "$B" && awk '{print $2"  "$1}' wolf-link.sums | sha256sum -c --quiet - && echo "staged bundle read $k: the record's seven files"); done
(cd "$B" && find . -type f | LC_ALL=C sort | xargs sha256sum > "$S/$N.contents.sha256")
t=$(git -C "$P" log -1 --format=%ct)
tar --sort=name --mtime="@$t" --owner=0 --group=0 --numeric-owner --format=gnu -C "$S" -cf - "$N" | xz -9 -T1 > "$S/$N.tar.xz"
(cd "$S" && sha256sum "$N.tar.xz" > "$N.tar.xz.sha256")
sha256sum "$S/$N.tar.xz"; sha256sum "$S/$N.tar.xz"; wc -c < "$S/$N.tar.xz"
echo "restage.sh done at $(git -C "$P" rev-parse HEAD) $(date -Is)"
