# sh20: what a subshell's process is, per shape, asked from inside it.
# Run as `SHELL childstate.sh` (or `. ./childstate.sh` at a prompt).
# Each line: shape, the process's SigIgn (hex, the host's numbering),
# whether it is the shell's own process, and whether it leads or shares
# a process group other than the shell's. The subshell's pid is its
# child's PPID (`sh -c` as the only command of a substitution, which
# both dash and pelt run in the substitution's own process).
me=$$
mypg=$(ps -o pgid= -p $$ | tr -d ' ')
show() {
    ign=$(sed -n 's/^SigIgn:[[:space:]]*//p' /proc/$2/status)
    pg=$(ps -o pgid= -p $2 | tr -d ' ')
    if [ "$2" = "$me" ]; then who=the-shell; else who=a-child; fi
    if [ "$pg" = "$mypg" ]; then grp=shell-group; elif [ "$pg" = "$2" ]; then grp=leads-own; else grp=other-group; fi
    echo "$1: ign=$ign $who $grp"
}
show shell $$
( p=$(sh -c 'echo $PPID'); show subshell $p; : )
x=$(p=$(sh -c 'echo $PPID'); show cmdsub $p; :); echo "$x"
( p=$(sh -c 'echo $PPID'); show bg-subshell $p; : ) & wait
{ p=$(sh -c 'echo $PPID'); show bg-brace $p; : ; } & wait
{ p=$(sh -c 'echo $PPID'); show stage-first $p; : ; } | cat
: | { p=$(sh -c 'echo $PPID'); show stage-last $p; : ; }
trap 'echo t' USR1 TERM; trap '' HUP
( p=$(sh -c 'echo $PPID'); show sub-traps $p; trap; : )
trap - USR1 TERM HUP
# a program run in a substitution, and one in a background list
x=$(sed -n 's/^SigIgn:[[:space:]]*/cmdsub-program: ign=/p' /proc/self/status); echo "$x"
sed -n 's/^SigIgn:[[:space:]]*/bg-program: ign=/p' /proc/self/status & wait
# can a background subshell trap SIGINT, which it starts ignoring?
( trap 'echo bg-trap-int: caught' INT; kill -INT $(sh -c 'echo $PPID'); sleep 0.2; echo bg-trap-int: after ) & wait
