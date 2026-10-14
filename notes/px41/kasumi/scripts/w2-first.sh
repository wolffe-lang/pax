#!/bin/bash
# px41 on kasumi, tree w2: lobo-session's witness, the speaker suite, then the lobo suite, no added load.
L=~/lanes/px41
cd $L/t-w2 && PAX_REQUIRE_QEMU=1 TMPDIR=$L/tmp tests/lobo-session-selftest > $L/ev/w2/lobo-session-selftest.out 2>&1; echo "selftest rc=$?" >> $L/ev/w2/summary.txt
$L/st/suite.sh w2 speaker-idle 0 - mpx3-speaker
$L/st/suite.sh w2 lobo-idle 0 - mpx4-lobo --round 30
echo done > $L/ev/w2/first.done
