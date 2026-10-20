#!/bin/bash
# px54 on kasumi: the suites at the branch's head, one after another
# (suite.sh), each summary line kept.   chain.sh TAG
T=$1
S=$HOME/lanes/px54/suite.sh
$S mpx5-lope $T-lope both both
for s in mpx5-jobs mpx3-shell mpx3-console mpx3-tree mpx5-accounts mpx3-screen mpx3-speaker; do
  $S $s $T-$s native bios
done
echo chain done
