sleep 1 & p=$!
(wait $p; echo "sub=$?") 2>/dev/null
wait $p; echo "parent=$?"
