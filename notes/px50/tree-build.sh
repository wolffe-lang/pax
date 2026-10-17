#!/bin/bash
# px50 on kasumi: mpx3-tree's images (px13-ubuntu), reusing pelt, boreutils and su from an earlier build.
#   tree-build.sh TAG [FROMTAG]
L=$HOME/lanes/px50
T=$1 F=${2:-t1}
B=$L/build/$T
rm -rf $B && mkdir -p $B
FW=$L/build/$F/mpx3-tree
podman run --rm -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu bash -c "cd $L/pax && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/mpx3-tree --only build --tier native --pelt $FW/shell/root/bin --bore $FW/bore --su $FW/subin" > $B.build.log 2>&1
echo "build: $?"; tail -1 $B.build.log
