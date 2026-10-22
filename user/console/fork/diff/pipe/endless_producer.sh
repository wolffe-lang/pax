# A producer the shell runs itself never ends of its own accord: the
# reader that leaves ends it (SIGPIPE), so the pipeline ends (XCU 2.9.2:
# each stage a subshell, run together; sh19 §6.1, the endless producer
# tests/diff/PENDING.md named with no case)
while :; do echo y; done | head -n 1
echo "status=$?"
f() { while :; do printf 'line\n'; done; }
f | sed -n 2q
echo "after"
