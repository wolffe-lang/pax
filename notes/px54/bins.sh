#!/bin/bash
# px54 on kasumi: lope (tools/mklope) and pelt (tools/mkpelt) built twice
# each in localhost/px13-ubuntu (cpus 4-15), from the branch's tree; the
# sums and sizes printed, then compared.   bins.sh TAG
L=$HOME/lanes/px54
T=$1
B=$L/build/$T
rm -rf $B && mkdir -p $B
podman image inspect --format '{{.Id}}' localhost/px13-ubuntu
for n in 1 2; do
  podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
      -e PAX_LOPE_REPO=$L/lope localhost/px13-ubuntu bash -c "
    cd $L/pax && git log --oneline -1 && tools/mklope $B/lope$n && tools/mkpelt $B/pelt$n" > $B/build$n.log 2>&1
  echo "build $n: rc=$?"
  cat $B/lope$n/sums.txt $B/pelt$n/sums.txt
done
cmp $B/lope1/lope $B/lope2/lope && echo "lope: the two builds are the same bytes"
cmp $B/pelt1/pelt $B/pelt2/pelt && echo "pelt: the two builds are the same bytes"
sha256sum $B/lope*/lope $B/pelt*/pelt
grep -h 'linked against' $B/build*.log
