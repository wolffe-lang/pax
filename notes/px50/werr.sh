#!/bin/bash
# px50 on kasumi (in px13-ubuntu): the kernel's compile errors, all of them, warnings left out.
#   werr.sh KMAIN
L=${PX50:-$HOME/lanes/px50}
cd $L/pax/kernel
W=$(cd $L/pax && PAX_CACHE=$L/cache tools/fetch-wolf | tail -n 1)
"$W" build "$1.lu" --target x86_64-unknown-none --emit=obj -o $L/tmp/werr.o --error-limit=0 2>&1 | awk '/^error/{p=1} /^warning/{p=0} p' | head -${2:-120}
