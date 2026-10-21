#!/bin/bash
# px58 on kasumi: yew (tools/mkyew) built twice in localhost/px13-ubuntu
# (cpus 4-15), from the branch's tree; the sums and sizes printed, then
# compared.   bins.sh TAG
L=$HOME/lanes/px58
T=$1
B=$L/build/$T
rm -rf $B && mkdir -p $B
podman image inspect --format '{{.Id}}' localhost/px13-ubuntu
for n in 1 2; do
  podman run --rm --cpuset-cpus 4-15 --ulimit core=0:0 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp \
      -e PAX_YEW_REPO=$L/yew localhost/px13-ubuntu bash -c "
    cd $L/pax && git log --oneline -1 && s=\$SECONDS; tools/mkyew $B/yew$n; r=\$?; echo build: \$((SECONDS - s)) s; exit \$r" > $B/build$n.log 2>&1
  echo "build $n: rc=$?"
  cat $B/yew$n/sums.txt
  grep -h '^build: ' $B/build$n.log
done
cmp $B/yew1/yew $B/yew2/yew && echo "yew: the two builds are the same bytes"
sha256sum $B/yew*/yew
grep -h 'linked against' $B/build*.log
grep -h '^yew ' $B/build1.log | head -3
