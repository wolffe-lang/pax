# a subshell's own redirections, and those of braces that hold it alone,
# are its process's: the shell says that a signal ended the subshell on
# its own standard error, outside them; a fuller brace group's, a loop's
# and a function call's redirections are the shell's (dash, black box)
said() { if [ -s f ]; then echo "$1 in f"; else echo "$1 outside"; fi; rm -f f; }
( kill -TERM $(sh -c 'echo $PPID') ) 2>f; said "1 $?"
( :; kill -TERM $(sh -c 'echo $PPID') ) 2>f; said "2 $?"
( sh -c 'kill -TERM $$' ) 2>f; said "3 $?"
{ ( kill -TERM $(sh -c 'echo $PPID') ); } 2>f; said "4 $?"
{ { ( sh -c 'kill -TERM $$' ); }; } 2>f; said "5 $?"
( ( kill -TERM $(sh -c 'echo $PPID') ) 2>/dev/null ) 2>f; said "6 $?"
if ( kill -TERM $(sh -c 'echo $PPID') ) 2>f; then :; fi; said "7 $?"
x=$( ( kill -TERM $(sh -c 'echo $PPID') ) 2>f; echo after ); said "8 $x"
{ ( kill -TERM $(sh -c 'echo $PPID') ); } 2>f | cat; said "9 $?"
{ ( kill -TERM $(sh -c 'echo $PPID') ); :; } 2>f; said "10 $?"
for i in 1; do ( kill -TERM $(sh -c 'echo $PPID') ); done 2>f; said "11 $?"
g() { ( kill -TERM $(sh -c 'echo $PPID') ); }; g 2>f; said "12 $?"
