#!/bin/bash
# sh20: when a trap the shell's signal set off runs, against the command
# it came during (a forked subshell, a substitution, a stage, a program).
# usage: trapwait.sh SH
SH=$1
n=0
row() {
  n=$((n + 1))
  printf '%02d %s\n   %s\n' "$n" "$1" "$("$SH" -c "$1" 2>&1 | tr '\n' ' ')"
}
row 'trap "echo got" USR1; ( kill -USR1 $$; sleep 0.2; echo in ); echo st=$?; echo two'
row 'trap "echo got" USR1; ( kill -USR1 $$; sleep 0.2; echo in ) >/dev/null; echo st=$?; echo two'
row 'trap "echo got" USR1; { ( kill -USR1 $$; sleep 0.2; echo in ); } >/dev/null; echo st=$?; echo two'
row 'trap "echo got" USR1; sh -c "kill -USR1 \$PPID; sleep 0.2" >/dev/null; echo st=$?; echo two'
row 'trap "echo got" USR1; x=$(kill -USR1 $$; sleep 0.2; echo in); echo st=$?; echo two'
row 'trap "echo got" USR1; ( kill -USR1 $$; sleep 0.2 ) | cat; echo st=$?; echo two'
row 'trap "echo got" USR1; ( kill -USR1 $$; sleep 0.2 ) & wait; echo st=$?; echo two'
row 'trap "echo got" USR1; ( sh -c "kill -USR1 \$PPID; sleep 0.2" ) >/dev/null; echo st=$?; echo two'
row 'trap "echo got" USR1; ( kill -USR1 $$; sleep 0.2; echo in ) >/dev/null
echo st=$?; echo two'
