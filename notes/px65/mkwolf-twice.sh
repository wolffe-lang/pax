#!/bin/bash
# px65, kasumi: the dev compiler (user/wolf.pin: v0.2.35, unpatched) built
# by tools/mkwolf twice, in px57-rust (the recipe's Rust image: Rust
# 1.97.1 and the musl target, FROM px13-ubuntu), on CPUs 12-15; the two
# builds' sums compared. The first is kept at ~/lanes/px65/wolf-out.
L=$HOME/lanes/px65; P=${PX65_TREE:-$L/pax}
mkdir -p "$L/tmp"
for k in 1 2; do
    rm -rf "$L/wolf-b$k"; mkdir -p "$L/wolf-b$k"
    t0=$(date +%s)
    podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e TMPDIR=$L/tmp -e PAX_BUILD=$L/build/mkwolf-$k \
        -e CARGO_INCREMENTAL=0 -e PAX_WOLF_BUILD_JOBS=4 localhost/px57-rust bash -c "cd $P && tools/mkwolf $L/wolf-b$k" > "$L/wolf-b$k.log" 2>&1
    echo "mkwolf $k rc=$? $(( $(date +%s) - t0 ))s"; tail -n 4 "$L/wolf-b$k.log"
done
cmp "$L/wolf-b1/sums.txt" "$L/wolf-b2/sums.txt" && echo "two builds, one set of bytes" || echo "TWO BUILDS DIFFER"
rm -rf "$L/wolf-out"; cp -a "$L/wolf-b1" "$L/wolf-out"; cat "$L/wolf-out/sums.txt"
