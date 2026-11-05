#!/usr/bin/env bash
# px102 measurement 2, inside px88-ubuntu:1 with CAP_SYS_PTRACE: gdb -p (an
# attach to a sleeping process) under strace (no -f); then strace -f of a
# gdb that cannot start its inferior (strace takes it), only to list the
# requests gdb's throwaway probe children make (their TRACEME is refused
# there: an invalid session, kept for the request names alone).
set -u
cd /m
out=/m/out2
mkdir -p "$out"
gcc -g -O0 -static -o sleeper sleeper.c || exit 3
gcc -g -O0 -static -o prog prog.c || exit 3
./sleeper & sp=$!
sleep 1
taskset -c "$LIGHT_CPUS" strace -o "$out/gdb-attach.named.strace" -ttt -s 64 gdb -batch -nx -x attach.gdb -p $sp ./sleeper > "$out/gdb-attach.named.out" 2>&1
echo "gdb attach exit=$?" >> "$out/versions.txt"
kill $sp; wait $sp 2>/dev/null
taskset -c "$LIGHT_CPUS" strace -f -o "$out/gdb-f.named.strace" -ttt -s 64 gdb -batch -nx -x s2.gdb ./prog > "$out/gdb-f.named.out" 2>&1
echo "gdb -f exit=$?" >> "$out/versions.txt"
echo done >> "$out/versions.txt"
exit 0
