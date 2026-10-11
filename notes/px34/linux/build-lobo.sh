#!/usr/bin/env bash
# px34: build lobo static at its trunk pin inside px13-ubuntu.
# Runs INSIDE the container; /w is ~/lanes/px34 on kasumi.
set -euo pipefail
W=/w
WOLFDIR=$W/pax/.pax-cache/wolf-0.2.27/wolf-0.2.27-x86_64-unknown-linux-gnu
"$WOLFDIR/wolf" --version | head -n 2
mkdir -p $W/st/bin $W/st/ccbin
printf '#!/bin/sh\nexec /usr/bin/cc -static "$@"\n' > $W/st/ccbin/cc
chmod +x $W/st/ccbin/cc
cd $W/lobo
git rev-parse HEAD
export WOLF_STD=$W/st/std-pin/std
cat $WOLF_STD/STD-REV
t0=$SECONDS
PATH=$W/st/ccbin:$PATH "$WOLFDIR/wolf" build --release --no-cache ./src/main.lu -o $W/st/bin/lobo
echo "lobo built in $((SECONDS - t0)) s"
readelf -hW $W/st/bin/lobo | grep Type
readelf -lW $W/st/bin/lobo | grep -c INTERP || true
sha256sum $W/st/bin/lobo
ls -l $W/st/bin/lobo
$W/st/bin/lobo -v || true
