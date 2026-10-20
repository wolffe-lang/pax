#!/bin/bash
# px54 on kasumi: start a long job detached (setsid -f), its pid recorded
# by the job itself.   launch.sh TAG COMMAND...  -> ~/lanes/px54/out/TAG.out, TAG.pid, TAG.rc
L=$HOME/lanes/px54
t=$1; shift
cd $L || exit 2
setsid -f bash -c 'echo $$ > "$0/out/$1.pid"; shift 2; "$@"; echo $? > "'"$L/out/$t.rc"'"' "$L" "$t" x "$@" > $L/out/$t.out 2>&1 < /dev/null
sleep 1
echo "$t: pid $(cat $L/out/$t.pid)"
