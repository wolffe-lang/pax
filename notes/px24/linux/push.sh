#!/usr/bin/env bash
set -uo pipefail
W=/w/st; out=$W/wolf-strace; B=$W/bin/waitwolf
bash /w/st/wolfc.sh /w/st/waitwolf.lu 2>&1 | tail -15 || exit 1
sha256sum $B
timeout 60 strace -f -s 64 -o $out/push-4.strace $B push 7090 4 4000000 > $out/push-4.out 2>&1 &
sp=$!; sleep 0.5
timeout 60 strace -f -s 64 -o $out/pull-4.strace $B pull 127.0.0.1 7090 4 4000000 400 > $out/pull-4.out 2>&1; echo rc=$? >> $out/pull-4.out
wait $sp; echo rc=$? >> $out/push-4.out
cat $out/push-4.out $out/pull-4.out; wc -l $out/push-4.strace $out/pull-4.strace
