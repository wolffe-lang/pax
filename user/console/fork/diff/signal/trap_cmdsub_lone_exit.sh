# A command substitution that is one `trap` command lists the shell's
# traps, EXIT's too, and does not run the EXIT action as it ends (XCU
# `trap`); a substitution with anything more starts with them reset
trap 'echo parent-exit' EXIT
x=$(trap); echo "[$x]"
y=$(trap; :); echo "[$y]"
trap - EXIT
