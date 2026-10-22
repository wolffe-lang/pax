trap 'echo trapped' TERM
sleep 5 & p=$!
( sleep 1; kill -TERM $$ ) &
wait $p; s=$?
[ $s -gt 128 ] && echo "wait-above-128"
kill $p
