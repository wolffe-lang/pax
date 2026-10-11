#!/usr/bin/env bash
# px24 scratch: build one wolf file static in px13-ubuntu. /w is ~/lanes/px24.
set -uo pipefail
W=/w
WOLFDIR=$W/pax/.pax-cache/wolf-0.2.27/wolf-0.2.27-x86_64-unknown-linux-gnu
mkdir -p $W/st/bin $W/st/ccbin $W/st/wb
printf '#!/bin/sh\nexec /usr/bin/cc -static "$@"\n' > $W/st/ccbin/cc
chmod +x $W/st/ccbin/cc
src=$1; name=$(basename "$src" .lu)
rm -rf $W/st/wb/$name; mkdir -p $W/st/wb/$name
cp "$src" $W/st/wb/$name/$name.lu
cd $W/st/wb/$name
PATH=$W/st/ccbin:$PATH "$WOLFDIR/wolf" build --release --no-cache "$name.lu" -o $W/st/bin/$name
rc=$?
echo "wolf build rc=$rc"
exit $rc
