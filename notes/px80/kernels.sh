#!/usr/bin/env bash
# px80 item 2: every kernel the tree builds (kernel/kmain*.lu, both tiers),
# built by tools/build-kernel in px65's container (localhost/px80-ubuntu) on
# CPUs 0-3 with notes/px80/lld-wrap first on PATH: each link's output is the
# bundle's lld 18.1.8's, linked again by the container's Ubuntu lld 18.1.3 and
# compared byte for byte (one line per link in $O/lld.log). mkw's and mpx1's
# own variants are linked the same way when those suites run
# (notes/px80/run-suite.sh). Run under the block's lock. Output: $O.
set -euo pipefail
ulimit -c 0
L=$HOME/lanes/px80
O=$L/kernels
rm -rf "$O"; mkdir -p "$O" "$L/cache" "$L/tmp"
taskset -c 0-3 podman run --rm --cpuset-cpus 0-3 --ulimit core=0:0 -v "$L:$L:Z" -v "$L/lld-out:/opt/px80:ro" \
    -e L="$L" -e O="$O" localhost/px80-ubuntu bash -c '
set -uo pipefail
cd "$L/pax"; git config --global --add safe.directory "*"
echo "tree $(git rev-parse HEAD)"
export PAX_CACHE=$L/cache TMPDIR=$L/tmp
export PAX_WOLF=$(tools/fetch-wolf | tail -n 1)
export PATH=$L/pax/notes/px80/lld-wrap:$PATH PX80_LLD=/opt/px80/ld.lld PX80_LLD_REF=/usr/bin/ld.lld PX80_LLD_LOG=$O/lld.log
echo "ld.lld on PATH: $(command -v ld.lld) -> $($PX80_LLD --version); reference: $($PX80_LLD_REF --version)"
n=0 bad=0
for src in kernel/kmain*.lu; do
    k=$(basename "$src" .lu)
    for tier in native release; do
        flag=(); [ "$tier" = release ] && flag=(--release)
        D=$O/$tier/$k; mkdir -p "$D"
        t0=$(date +%s)
        if elf=$(tools/build-kernel "${flag[@]}" --src "$src" "$D" 2>"$D/build-kernel.log"); then
            n=$((n + 1)); echo "$k $tier ok $(( $(date +%s) - t0 ))s $(sha256sum "$elf" | cut -c1-16)"
        else
            bad=$((bad + 1)); echo "$k $tier BUILD FAILED $(( $(date +%s) - t0 ))s"; tail -n 5 "$D/build-kernel.log"
        fi
    done
done
echo "kernels built: $n, failed: $bad"
echo "links: $(wc -l < $O/lld.log); $(cut -d" " -f1 $O/lld.log | sort | uniq -c | tr "\n" " ")"
'
echo "kernels.sh done $(date -Is)"
