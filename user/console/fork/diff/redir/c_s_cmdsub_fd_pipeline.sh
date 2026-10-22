# Inside a command substitution, `exec 4>&1` makes descriptor 4 the
# substitution's own output; a pipeline stage that writes to 4 writes
# there, while its standard output goes down the pipe (XCU 2.7.5,
# 2.12: a subshell inherits open files). The gzip family's wrappers
# carry an exit status out of a pipeline this way.
exec 3>&1
status=$(
    exec 4>&1
    (false 4>&-; echo $? >&4) 3>&- | cat >&3
)
echo "status=[$status]"
status=$(exec 4>&1; { echo seven >&4; } | cat >&3)
echo "status=[$status]"
status=$(exec 4>&1; echo data | { cat; echo eight >&4; } >&3)
echo "status=[$status]"
