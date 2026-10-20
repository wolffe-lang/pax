#!/bin/bash
# px53 on kasumi: tests/mkw (M-KW: the kernel at the pin, step 6's checked machine and lupin rows) built in
# px13-ubuntu (wolf and lupin at kernel/wolf.pin), then its ISOs booted here (TCG); and tests/tour the same way.
L=$HOME/lanes/px53
B=$L/build/mkw1
rm -rf $B && mkdir -p $B
cd $L/pax
podman run --rm --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "
  cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) PAX_LUPIN=\$(tools/fetch-lupin | tail -n 1) && \$PAX_LUPIN --version && tests/mkw --no-boot && tests/tour --no-boot" > $B.build.log 2>&1
echo "build: $?"; grep -a 'PASS\|FAIL' $B.build.log | cut -c1-240
export PAX_CACHE=$L/cache PAX_BUILD=$B
taskset -c 4-15 tests/mkw --images $B/mkw --firmware bios > $B.mkw.log 2>&1; echo "mkw boot: $?"; tail -n 2 $B.mkw.log
taskset -c 4-15 tests/tour --images $B/tour --firmware bios > $B.tour.log 2>&1; echo "tour boot: $?"; grep -a FAIL $B.tour.log | head; tail -n 1 $B.tour.log
