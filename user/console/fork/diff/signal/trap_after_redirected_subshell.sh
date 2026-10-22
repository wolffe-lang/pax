# a trap's action for a signal the shell heard while a subshell with
# redirections of its own ran: after the subshell, before the next
# command, and on the shell's descriptors, not the subshell's; a brace
# group's redirections are the shell's (dash, black box)
trap 'echo got' USR1
( kill -USR1 $$; sleep 0.2; echo in ) >f; echo "1 st=$?"; cat f
{ ( kill -USR1 $$; sleep 0.2; echo in ); } >f; echo "2 st=$?"; cat f
( sh -c 'kill -USR1 $PPID; sleep 0.2; echo in' ) >f; echo "3 st=$?"; cat f
{ kill -USR1 $$; sleep 0.2; echo in; } >f; echo "4 st=$?"; cat f
