# `exec` in a subshell replaces the subshell's process, not the shell's,
# and the shell goes on (XCU `exec`, 2.13): the program has the process
# id a program the subshell started saw as its parent
( p=$(sh -c 'echo $PPID'); exec sh -c "if [ \$\$ = $p ]; then echo replaced; else echo started; fi" )
echo "the shell goes on: $?"
