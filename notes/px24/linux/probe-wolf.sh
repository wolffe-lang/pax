#!/usr/bin/env bash
# px24: how many connections the wolf witness holds before wolf-lang#713 stalls it. Inside px13-ubuntu.
set -uo pipefail
B=/w/st/bin/waitwolf
for cpus in 0 0-3; do
  for n in 1 2 4 6 7 8 9 12 15 16 17; do
    r=$(timeout 5 taskset -c $cpus $B loop 7080 $n | tail -n 1 | cut -c1-60); printf "cpus %s loop %s: rc=%s %s\n" $cpus $n $? "$r"
  done
  for n in 4 8 12 14 15 16 17 24 31 32 33; do
    timeout 8 taskset -c $cpus $B serve 7081 $n > /w/st/serve.tmp 2>&1 &
    sp=$!; sleep 0.3
    timeout 5 taskset -c $cpus $B call 127.0.0.1 7081 $n > /w/st/call.tmp 2>&1; c=$?
    wait $sp; printf "cpus %s serve+call %s: call rc=%s serve rc=%s\n" $cpus $n $c $?
  done
done
