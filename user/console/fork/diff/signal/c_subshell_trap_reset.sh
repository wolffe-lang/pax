trap 'echo parent-exit' EXIT
trap 'echo caught' TERM
( trap ) | wc -l | tr -d ' '
( echo in-sub )
( kill -TERM $(sh -c 'echo $PPID'); echo not-reached ); echo "st=$?"
trap - EXIT
