#!/bin/bash
# px54 on kasumi: the three pelt suites that take --no-boot, not --only
# build (suite.sh chooses), at the branch's head.   chain2.sh TAG
T=$1
S=$HOME/lanes/px54/suite.sh
for s in mpx3-console mpx3-screen mpx3-speaker; do
  $S $s $T-$s native bios
done
echo chain done
