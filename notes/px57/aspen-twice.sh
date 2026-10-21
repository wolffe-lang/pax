#!/bin/bash
# px57 on kasumi: tools/mkaspen twice in px13-ubuntu (cpus 4-15). -> ~/lanes/px57/build/aspen{1,2}/
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}
cd $X && echo "tree: $(git log --oneline -1) $(git status --short | tr '\n' ' ')"
for n in 1 2; do
  rm -rf $L/build/aspen$n && mkdir -p $L/build/aspen$n
  podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp localhost/px13-ubuntu bash -c \
    "cd $X && tools/mkaspen $L/build/aspen$n" > $L/build/aspen$n.log 2>&1
  echo "build $n: rc $?"; tail -n 3 $L/build/aspen$n.log
done
sha256sum $L/build/aspen1/aspen $L/build/aspen2/aspen
cmp $L/build/aspen1/aspen $L/build/aspen2/aspen && echo "the same bytes"
