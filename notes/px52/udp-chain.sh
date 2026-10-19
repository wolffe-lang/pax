#!/bin/bash
# px52 on kasumi (pax#86): trunk d6fbcdc's mpx4-udp images built in px13-ubuntu (cpus 4-15) from a detached
# worktree, then udp-loop.sh four times, one after the other: trunk's picker plain, under load and under churn,
# and this branch's picker under churn.   udp-chain.sh N
L=$HOME/lanes/px52; P=$L/pax; N=${1:-100}
B=$L/build/udp-trunk
mkdir -p $L/ev/udp-loop
if [ ! -f $B/mpx4-udp/native/kmain_sockets-user.iso ]; then
    rm -rf $B $L/trunk && mkdir -p $B
    git -C $P worktree add -q --detach $L/trunk d6fbcdc || exit 2
    echo "trunk tree: $(git -C $L/trunk log --oneline -1)"
    podman run --rm --privileged --cpuset-cpus 4-15 -v $L:$L:Z -e PAX_CACHE=$L/cache -e TMPDIR=$L/tmp -e PAX_BUILD=$B localhost/px13-ubuntu \
        bash -c "cd $L/trunk && export PAX_WOLF=\$(tools/fetch-wolf | tail -n 1) && tests/mpx4-udp --no-boot --tier native" > $B.build.log 2>&1
    echo "build: $? ($(tail -n 1 $B.build.log | cut -c1-200))"
    cp $L/trunk/tests/mpx4-udp $L/ev/udp-loop/trunk-d6fbcdc-mpx4-udp
    git -C $P worktree remove --force $L/trunk
fi
W=$B/mpx4-udp
bash $P/notes/px52/udp-loop.sh trunk-plain $N $L/ev/udp-loop/trunk-d6fbcdc-mpx4-udp $W plain
bash $P/notes/px52/udp-loop.sh trunk-load $N $L/ev/udp-loop/trunk-d6fbcdc-mpx4-udp $W load
bash $P/notes/px52/udp-loop.sh trunk-churn $N $L/ev/udp-loop/trunk-d6fbcdc-mpx4-udp $W churn
cp $P/tests/mpx4-udp $L/ev/udp-loop/px52-mpx4-udp
bash $P/notes/px52/udp-loop.sh fixed-churn $N $L/ev/udp-loop/px52-mpx4-udp $W churn
cat $L/ev/udp-loop/*/summary.txt
