#!/bin/bash
# px41 on kasumi: the rebased head (3aef2f7, on d3f4aa9): built, then lobo-session's witness, the speaker
# suite and the lobo suite, no load added (after the K8 loops).
L=~/lanes/px41
$L/st/build.sh w7 3aef2f7 "mpx3-speaker mpx4-lobo"
while [ ! -f $L/ev/k8b.done ]; do sleep 20; done
cd $L/t-w7 && PAX_REQUIRE_QEMU=1 TMPDIR=$L/tmp tests/lobo-session-selftest > $L/ev/w7/lobo-session-selftest.out 2>&1; echo "selftest rc=$?" >> $L/ev/w7/summary.txt
PAX_REQUIRE_STRACE=1 $L/st/suite.sh w7 speaker-idle 0 - mpx3-speaker
$L/st/suite.sh w7 lobo-idle 0 - mpx4-lobo --round 30
echo done > $L/ev/w7/first.done
