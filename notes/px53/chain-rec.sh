#!/bin/bash
# px53 on kasumi: build mpx5-jobs (TAG), then real root's recordings twice (vm/rec1, vm/rec2) from its archive.
#   chain-rec.sh TAG
L=$HOME/lanes/px53
bash $L/pax/notes/px53/build-only.sh mpx5-jobs $1 native
rm -rf $L/vm/rec1 $L/vm/rec2
bash $L/pax/notes/px53/vm-rec.sh $1 $L/vm/rec1
bash $L/pax/notes/px53/vm-rec.sh $1 $L/vm/rec2
for f in $L/vm/rec1/*.tty; do n=${f##*/}; cmp -s $f $L/vm/rec2/$n && echo "same $n" || echo "DIFFERS $n"; done
