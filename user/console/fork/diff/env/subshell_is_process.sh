# A subshell is a process of its own (XCU 2.13): a program it starts,
# not as its last command, has the subshell as its parent and not the
# shell; so has one a command substitution starts, and one after a
# stage the shell runs itself; a background subshell's or brace
# group's $! is a live process; and what any of them assigns stays in it
( sh -c 'echo $PPID' > p1; : ); read a < p1
[ "$a" = "$$" ] && echo "subshell: the shell" || echo "subshell: another process"
b=$(sh -c 'echo $PPID'; :)
[ "$b" = "$$" ] && echo "substitution: the shell" || echo "substitution: another process"
c=$(: | sh -c 'echo $PPID'; :)
[ "$c" = "$$" ] && echo "stage: the shell" || echo "stage: another process"
( sleep 1 ) & p=$!
kill -0 $p 2>/dev/null && echo "background subshell: a process" || echo "background subshell: none"
{ sleep 1; } & q=$!
kill -0 $q 2>/dev/null && echo "background group: a process" || echo "background group: none"
wait
x=0; ( x=1 ); { x=2; } & wait; y=0; y=3 | :; echo "kept: $x $y"
