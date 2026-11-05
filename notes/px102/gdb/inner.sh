#!/usr/bin/env bash
# px102 measurement, inside px88-ubuntu:1: gdb (the distro's) driven over a
# small static program under strace (no -f: strace -f would take the
# inferior as its own tracee, and the inferior's PTRACE_TRACEME would fail;
# every ptrace request gdb makes comes from its main thread).
set -u
cd /m
out=/m/out
mkdir -p "$out"
{ gdb --version | head -1; strace -V | head -1; gcc --version | head -1; uname -r; cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null; } > "$out/versions.txt" 2>&1
gcc -g -O0 -static -o prog prog.c || exit 3
gcc -g -O0 -static -o sleeper sleeper.c || exit 3
for s in s2 watch; do
  taskset -c "$LIGHT_CPUS" strace -o "$out/gdb-$s.strace" -ttt -s 64 -X raw gdb -batch -nx -x $s.gdb ./prog > "$out/gdb-$s.out" 2>&1
  echo "gdb $s exit=$?" >> "$out/versions.txt"
  taskset -c "$LIGHT_CPUS" strace -o "$out/gdb-$s.named.strace" -ttt -s 64 gdb -batch -nx -x $s.gdb ./prog > "$out/gdb-$s.named.out" 2>&1
done
# attach: gdb -p to a sleeping descendant (Yama's scope 1 allows a descendant)
./sleeper & sp=$!
sleep 1
taskset -c "$LIGHT_CPUS" strace -o "$out/gdb-attach.named.strace" -ttt -s 64 gdb -batch -nx -x attach.gdb -p $sp ./sleeper > "$out/gdb-attach.named.out" 2>&1
echo "gdb attach exit=$?" >> "$out/versions.txt"
kill $sp; wait $sp 2>/dev/null
echo done >> "$out/versions.txt"
exit 0
