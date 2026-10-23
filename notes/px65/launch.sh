#!/bin/bash
# px65, kasumi: start a long job detached (setsid -f), under the CPU
# lock, its pids recorded; killed by those pids only.
#   launch.sh TAG COMMAND...   -> ~/lanes/px65/out/TAG.out, TAG.pid (the
#   wrapper), TAG.jobpid (the job), TAG.rc (its status, at its end)
L=$HOME/lanes/px65
t=$1; shift
mkdir -p "$L/out"
cd "$L" || exit 2
rm -f "$L/out/$t.rc"
setsid -f bash -c 'o=$1; shift; echo $$ > $o.pid; ulimit -c 0; flock "$HOME/lanes/kasumi-cores-12-15.lock" "$@" > $o.out 2>&1 < /dev/null & echo $! > $o.jobpid; wait $!; echo $? > $o.rc' _ "$L/out/$t" "$@" < /dev/null > /dev/null 2>&1
sleep 1
echo "$t: wrapper $(cat "$L/out/$t.pid" 2>/dev/null), job $(cat "$L/out/$t.jobpid" 2>/dev/null)"
