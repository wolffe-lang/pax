# sh19 #34: what each shape pelt runs in-process does, asked from inside.
# Run as `SHELL shapes.sh` with TMPDIR set; every line is "row: answer".
t=${TMPDIR:-/tmp}/shapes.$$
mkdir -p "$t"

# 1. ( … ): whose child is a program started inside it? (not the last
# command, so no shell can run it in the subshell's own process)
( env sh -c 'echo $PPID'; : ) > "$t/p1"; read p < "$t/p1"
if [ "$p" = "$$" ]; then echo "sub-child-parent: the shell"; else echo "sub-child-parent: another process"; fi
# $$ inside is the shell's, as POSIX says
( echo "$$" ) > "$t/p2"; read q < "$t/p2"
[ "$q" = "$$" ] && echo "sub-dollar-dollar: the shell's" || echo "sub-dollar-dollar: other"
# a variable set inside does not come out
x=0; ( x=1 ); echo "sub-assign-kept: $x"

# 2. ( … ) & and { …; } &: does the shell go on before the list ends?
{ ( sleep 0.3; echo a ) & echo b; wait; } > "$t/o2"
echo "bg-sub-order: $(tr '\n' ' ' < "$t/o2")"
{ { sleep 0.3; echo a; } & echo b; wait; } > "$t/o3"
echo "bg-brace-order: $(tr '\n' ' ' < "$t/o3")"
# is $! a process?
( sleep 0.2 ) & p=$!
if kill -0 "$p" 2>/dev/null; then echo "bg-sub-pid: a process"; else echo "bg-sub-pid: no process"; fi
wait
# a variable set in a background brace group does not come out
y=0; { y=1; } & wait; echo "bg-brace-assign-kept: $y"

# 3. $( … ): whose child is a program started inside it?
r=$(env sh -c 'echo $PPID'; :)
if [ "$r" = "$$" ]; then echo "cmdsub-child-parent: the shell"; else echo "cmdsub-child-parent: another process"; fi

# 4. a stage the shell runs itself: does the next stage start before it ends?
{ echo one; sleep 0.3; echo producer-done >&2; } 2>>"$t/o4" | { read v; echo "reader-got-$v" >&2; cat >/dev/null; } 2>>"$t/o4"
echo "stage-order: $(tr '\n' ' ' < "$t/o4")"
# a program stage after a shell stage: whose child is the program?
s=$( : | env sh -c 'echo $PPID'; : )
if [ "$s" = "$$" ]; then echo "stage-program-parent: the shell"; else echo "stage-program-parent: another process"; fi

# 5. a function in a pipeline
f() { echo one; sleep 0.3; echo f-done >&2; }
f 2>>"$t/o5" | { read v; echo "reader-got-$v" >&2; cat >/dev/null; } 2>>"$t/o5"
echo "func-stage-order: $(tr '\n' ' ' < "$t/o5")"
# a variable a stage sets: kept by neither (every stage a subshell)
z=0; z=1 | :; echo "stage-assign-kept: $z"

# 6. exec inside a subshell replaces the subshell, not the shell
( exec env true ); echo "sub-exec: the shell went on"

rm -rf "$t"
echo "end"
