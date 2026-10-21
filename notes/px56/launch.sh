#!/bin/bash
# px56 on kasumi: start a long job detached (setsid -f), its pids recorded.
#   launch.sh TAG COMMAND...   -> ~/lanes/px56/out/TAG.out, TAG.pid (the
#   wrapper), TAG.jobpid (the job), TAG.rc (its status, at its end)
L=$HOME/lanes/px56
t=$1; shift
cd $L || exit 2
rm -f $L/out/$t.rc
setsid -f bash -c 'o=$1; shift; echo $$ > $o.pid; "$@" > $o.out 2>&1 < /dev/null & echo $! > $o.jobpid; wait $!; echo $? > $o.rc' _ $L/out/$t "$@" < /dev/null > /dev/null 2>&1
sleep 1
echo "$t: wrapper $(cat $L/out/$t.pid 2>/dev/null), job $(cat $L/out/$t.jobpid 2>/dev/null)"
