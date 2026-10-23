#!/bin/bash
# px65, kasumi: tests/mkw (M-KW: the kernel at the pin, step 6's checked
# machine and lupin rows) and tests/tour, built and booted in the lane's
# container (wolf and lupin at kernel/wolf.pin), native and release, BIOS.
#   mkw.sh TAG    (the tree: PX65_TREE)
L=$HOME/lanes/px65; X=${PX65_TREE:-$L/pax}
B=$L/build/${1:-mkw1}
rm -rf "$B" && mkdir -p "$B" "$L/cache" "$L/tmp"
echo "tree: $(git -C "$X" log --oneline -1)"
podman run --rm --cpuset-cpus 12-15 --ulimit core=0:0 -v "$L:$L:Z" -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px65-ubuntu bash -c "
  cd $X && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) PAX_LUPIN=\$(tools/fetch-lupin | tail -n 1) && \$PAX_WOLF --version | head -n 1 && \$PAX_LUPIN --version &&
  tests/mkw --no-boot && tests/tour --no-boot &&
  taskset -c 12-15 tests/mkw --images $B/mkw --firmware bios > $B.mkw.log 2>&1; echo \"mkw boot: \$?\"; tail -n 2 $B.mkw.log
  taskset -c 12-15 tests/tour --images $B/tour --firmware bios > $B.tour.log 2>&1; echo \"tour boot: \$?\"; grep -a FAIL $B.tour.log | head; tail -n 1 $B.tour.log
" > "$B.build.log" 2>&1
echo "mkw.sh rc=$?"; grep -a -E 'PASS|FAIL|boot:|^wolf|^lupin' "$B.build.log" | cut -c1-240
