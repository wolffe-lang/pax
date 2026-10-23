#!/bin/bash
# px65, kasumi: suites built in the lane's container and booted (native,
# BIOS, TCG, CPUs 12-15), one after the other.
#   regress.sh RUN SUITE...      (the tree: PX65_TREE, default ~/lanes/px65/pax)
# A suite named NAME:IMAGE builds in IMAGE (localhost/px57-rust for the
# two that build Rust: mpx5-lupin, mpx5-wolf).
L=$HOME/lanes/px65; X=${PX65_TREE:-$L/pax}; P=$L/pax/notes/px65; R=$1; shift
echo "tree: $(git -C "$X" log --oneline -1) $(date -Is)"; uptime
for e in "$@"; do
    s=${e%%:*}; img=; [ "$s" != "$e" ] && img=${e#*:}
    echo "== $s $(date -Is)"; t=$R-$s
    if grep -q -- '--only build' "$X/tests/$s"; then a=(--only build --tier native); else a=(--no-boot --tier native); fi
    PX65_BUILD_IMAGE=${img:-localhost/px65-ubuntu} bash "$P/build.sh" "$s" "$t" "${a[@]}" \
      && bash "$P/boot.sh" "$s" "$t" --tier native --firmware bios
    echo "== $s: $? $(date -Is)"
done
