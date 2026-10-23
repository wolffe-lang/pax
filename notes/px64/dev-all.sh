#!/bin/bash
# px64, kasumi: the dev ISO end to end at one tree commit: verify, build,
# assemble, boot (notes/px64/dev-iso/).
set -u
L=$HOME/lanes/px64/dev
C=$1
printf '%s\n' $$ > "$HOME/lanes/px64/dev-all.pid"
mkdir -p "$L"
git -C $HOME/lanes/px64/pax update-ref -d refs/original/refs/heads/px64 2>/dev/null || true
rm -rf "$L/pax"; git clone -q $HOME/lanes/px64/pax "$L/pax" && git -C "$L/pax" checkout -q --detach "$C" || exit 2
echo "tree $(git -C "$L/pax" rev-parse HEAD) $(git -C "$L/pax" log -1 --format=%ct)"
for s in verify build assemble boot; do
    t0=$(date +%s)
    bash "$L/pax/notes/px64/dev-iso/$s.sh" > "$L/$s.log" 2>&1
    rc=$?
    echo "$s rc=$rc $(( $(date +%s) - t0 ))s $(date -Is)"
    tail -n 12 "$L/$s.log"
    [ "$rc" = 0 ] || { echo "dev-all stopped at $s"; exit 1; }
done
echo "dev-all done $(date -Is)"
