#!/bin/bash
# px54 on kasumi: pelt at the branch's pin (90d7c64) built twice by
# tools/mkpelt in localhost/px13-ubuntu (cpus 4-15).   pelt-twice.sh TAG
L=$HOME/lanes/px54
T=$1
B=$L/build/$T
rm -rf $B && mkdir -p $B
for n in 1 2; do
  podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c "
    cd $L/pax && git log --oneline -1 && grep ^PELT_REV user/pelt.pin && tools/mkpelt $B/pelt$n" > $B/build$n.log 2>&1
  echo "build $n: rc=$?"
  cat $B/pelt$n/sums.txt
done
cmp $B/pelt1/pelt $B/pelt2/pelt && echo "pelt: the two builds are the same bytes"
sha256sum $B/pelt*/pelt
