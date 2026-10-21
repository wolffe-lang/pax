#!/bin/bash
# px57 on kasumi: tools/mklupin twice, each in a fresh container of the throwaway Rust image
# (localhost/px57-rust, notes/px57/rust/Containerfile), cpus 4-15; the build directory the
# container's own /tmp/pax-mklupin both times. -> ~/lanes/px57/build/lupin{1,2}/
L=$HOME/lanes/px57; X=${PX57_TREE:-$L/pax}
cd $X && echo "tree: $(git log --oneline -1) $(git status --short | tr '\n' ' ')"
podman image inspect --format '{{.Id}}' localhost/px57-rust
for n in 1 2; do
  rm -rf $L/build/lupin$n && mkdir -p $L/build/lupin$n
  /usr/bin/time -f "build $n: %e s wall" podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache localhost/px57-rust bash -c \
    "cd $X && tools/mklupin $L/build/lupin$n" > $L/build/lupin$n.log 2>&1
  echo "build $n: rc $?"; tail -n 4 $L/build/lupin$n.log
done
sha256sum $L/build/lupin1/lupin $L/build/lupin2/lupin
cmp $L/build/lupin1/lupin $L/build/lupin2/lupin && echo "the same bytes"
readelf -hW $L/build/lupin1/lupin | grep -E 'Type|Entry'; readelf -lW $L/build/lupin1/lupin | grep -E 'LOAD|INTERP|TLS|GNU_STACK'; readelf -dW $L/build/lupin1/lupin | head -2
