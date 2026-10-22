# `( … ) 2>/dev/null` that a signal ends: the shell's word on it is on the
# shell's standard error, not in the subshell's /dev/null (dash, black box)
( kill -TERM $(sh -c 'echo $PPID') ) 2>/dev/null; echo "st=$?"
