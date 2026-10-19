#!/bin/bash
# px52 on kasumi: mpx5-jobs built (native) in px13-ubuntu, then its fds archive on real root's guest twice
# (vm/rec1, vm/rec2), the two compared byte for byte.   fds-chain.sh TAG
L=$HOME/lanes/px52; P=$L/pax/notes/px52; T=$1
bash $P/build.sh mpx5-jobs $T --only build --tier native || exit 1
for r in rec1 rec2; do
  rm -rf $L/vm/$r
  bash $P/vm-fds.sh $L/vm/$r $L/build/$T/mpx5-jobs/fds.cpio > $L/vm/$r.out 2>&1
  echo "$r: $(grep -c . $L/vm/$r.out) lines; $(grep '^root\|^user' $L/vm/$r.out | tr '\n' ' ')"
done
for f in fds.tty fds.tty.rc fds-user.tty fds-user.tty.rc; do
  cmp -s $L/vm/rec1/$f $L/vm/rec2/$f && echo "same: $f $(sha256sum < $L/vm/rec1/$f | cut -c1-16)" || echo "DIFFER: $f"
done
