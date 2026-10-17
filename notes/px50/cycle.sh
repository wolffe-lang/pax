#!/bin/bash
# px50 on kasumi: build mpx5-jobs' images (px13-ubuntu), record fds on real root's guest from the suite's own
# archive, boot the fds image on PAX, and diff the two, root's and the user's.   cycle.sh TAG [norec]
L=$HOME/lanes/px50
T=$1
B=$L/build/$T
rm -rf $B && mkdir -p $B
podman run --rm --network none -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/mpx5-jobs --only build --tier native" > $B.build.log 2>&1
grep -a 'built native fds' $B.build.log || { tail -20 $B.build.log; exit 1; }
if [ "${2:-}" != norec ]; then
  timeout 1500 $L/pax/notes/px50/vm-fds.sh $L/out/$T-rec $B/mpx5-jobs/fds.cpio > $L/out/$T-rec.log 2>&1 &
  rp=$!
fi
timeout 1000 $L/pax/notes/px50/pax-boot.sh $B/mpx5-jobs native fds kmain_session $L/out/$T-pax
R=$L/out/$T-rec
[ "${2:-}" = norec ] && R=$L/out/${3:-rec1}
[ -n "${rp:-}" ] && wait $rp
cd $L/pax && . tools/lib.sh
for n in 1 2; do r=fds; [ $n = 2 ] && r=fds-user
  serial_norm $R/$r.tty > $L/out/$T-pax/$r.rec.cmp
  diff $L/out/$T-pax/$r.rec.cmp $L/out/$T-pax/run$n.session > $L/out/$T-pax/diff-$r.txt
  echo "== $r: $(grep -c . $L/out/$T-pax/$r.rec.cmp) lines on Linux, $(grep -c . $L/out/$T-pax/run$n.session) on PAX, $(grep -c '^<' $L/out/$T-pax/diff-$r.txt) differ"
  head -60 $L/out/$T-pax/diff-$r.txt
done
