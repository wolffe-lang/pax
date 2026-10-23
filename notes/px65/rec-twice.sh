#!/bin/bash
# px65, kasumi: real root's recordings from a head build, twice; each
# compared with the other and (vm-rec.sh) with the committed ones.
#   rec-twice.sh BUILDTAG
L=$HOME/lanes/px65
rm -rf "$L/vm/rec1" "$L/vm/rec2"
bash "$L/pax/notes/px65/vm-rec.sh" "$1" "$L/vm/rec1"
bash "$L/pax/notes/px65/vm-rec.sh" "$1" "$L/vm/rec2"
for f in "$L"/vm/rec1/*.tty "$L"/vm/rec1/*.tty.rc; do n=${f##*/}; cmp -s "$f" "$L/vm/rec2/$n" && echo "twice-same $n" || echo "twice-DIFFERS $n"; done
