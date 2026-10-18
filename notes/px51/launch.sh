#!/bin/bash
# px51 on kasumi: start a long job detached (setsid), its pid recorded.
#   launch.sh TAG COMMAND...   -> ~/lanes/px51/out/TAG.out, TAG.pid
L=$HOME/lanes/px51
t=$1; shift
cd $L || exit 2
setsid "$@" > $L/out/$t.out 2>&1 < /dev/null &
echo $! > $L/out/$t.pid
echo "$t: pid $(cat $L/out/$t.pid)"
