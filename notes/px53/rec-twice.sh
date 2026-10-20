#!/bin/bash
# px53: real root's recordings from the head build (head1), twice; each
# compared with the other and with the committed recordings.
L=$HOME/lanes/px53
rm -rf $L/vm/rec1 $L/vm/rec2
bash $L/pax/notes/px53/vm-rec.sh head1 $L/vm/rec1
bash $L/pax/notes/px53/vm-rec.sh head1 $L/vm/rec2
for f in $L/vm/rec1/*.tty $L/vm/rec1/*.tty.rc; do n=${f##*/}; cmp -s $f $L/vm/rec2/$n && echo "same $n" || echo "DIFFERS $n"; done
for f in $L/vm/rec1/*.tty $L/vm/rec1/*.tty.rc; do n=${f##*/}; c=$L/pax/tests/mpx5-jobs.d/linux/$n; if [ -f $c ]; then cmp -s $f $c && echo "committed-same $n" || echo "committed-DIFFERS $n"; else echo "new $n"; fi; done
